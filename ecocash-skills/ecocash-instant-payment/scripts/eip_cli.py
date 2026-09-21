#!/usr/bin/env python3
"""EcoCash Instant Payment (EIP) sandbox CLI - standard library only.

Commands
  header                     print the Authorization header for EIP_USERNAME/EIP_PASSWORD
  lint FILE|-                check a charge or refund JSON body for the mistakes that break
                             EIP integrations (field casing, amount, tranType, MSISDN ...)
  charge  --msisdn --amount  start a charge (a new clientCorrelator is generated and printed)
  lookup  --msisdn --correlator
  wait    --msisdn --correlator [--timeout 90]   poll every 3 s until SUCCESS/FAILED
  refund  --msisdn --original-ref --amount       refund a SUCCESS charge (new correlator)
  self-test                  run the linter against built-in good and bad payloads

Configuration comes from the same EIP_* variables as the templates (config/eip.env.example),
from the environment or from --env-file. Nothing is sent with --dry-run: the request is
printed with the password and merchant PIN masked.

Safety
  * Only the sandbox base URL is allowed unless --allow-live is given, because a live
    base URL moves real money.
  * `charge` never retries. After a timeout, run `lookup` with the SAME correlator -
    re-running `charge` could charge the customer twice.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SANDBOX = "https://developers.ecocash.co.zw/sandbox/payment/v1"

CHARGE_KEYS = ["clientCorrelator", "notifyUrl", "referenceCode", "tranType", "endUserId",
               "remarks", "transactionOperationStatus", "paymentAmount", "merchantCode",
               "merchantPin", "merchantNumber", "countryCode", "terminalID", "location",
               "superMerchantName", "merchantName"]
# A charge carries all 16 documented keys (notifyUrl may be ""). A refund carries the same
# shape plus originalEcocashReference; the portal's own Playground leaves out notifyUrl,
# remarks and transactionOperationStatus on refunds, so those are optional there.
CHARGE_REQUIRED = [k for k in CHARGE_KEYS if k != "notifyUrl"]
REFUND_REQUIRED = [k for k in CHARGE_KEYS
                   if k not in ("notifyUrl", "remarks", "transactionOperationStatus")] \
    + ["originalEcocashReference"]

# misspellings seen in real integrations -> the exact key EIP expects
CASING = {
    "chargingInformation": "charginginformation", "chargingInfo": "charginginformation",
    "charginginfo": "charginginformation", "ChargingInformation": "charginginformation",
    "chargeMetadata": "chargeMetaData", "chargemetadata": "chargeMetaData",
    "terminalId": "terminalID", "terminalid": "terminalID", "TerminalID": "terminalID",
    "endUserID": "endUserId", "enduserId": "endUserId", "msisdn": "endUserId",
    "correlator": "clientCorrelator", "clientCorrelatorId": "clientCorrelator",
    "reference": "referenceCode", "refCode": "referenceCode",
    "merchantPIN": "merchantPin", "notifyURL": "notifyUrl", "callbackUrl": "notifyUrl",
    "superMerchant": "superMerchantName", "originalReference": "originalEcocashReference",
    "transactionOperationsStatus": "transactionOperationStatus",
}


# --------------------------------------------------------------------------- config

def load_env_file(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cfg(name, default=None, required=True):
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit("error: %s is not set (see config/eip.env.example)" % name)
    return v


def base_url(allow_live):
    url = cfg("EIP_BASE_URL", SANDBOX).rstrip("/")
    if url != SANDBOX and not allow_live:
        sys.exit("error: EIP_BASE_URL is %s, not the sandbox.\n"
                 "Charges against a live base URL move real money. Re-run with --allow-live "
                 "if that is really what you want." % url)
    return url


def auth_header():
    token = base64.b64encode(("%s:%s" % (cfg("EIP_USERNAME"), cfg("EIP_PASSWORD"))).encode()).decode()
    return "Basic " + token


def merchant():
    return {
        "merchantCode": cfg("EIP_MERCHANT_CODE"),
        "merchantPin": cfg("EIP_MERCHANT_PIN"),
        "merchantNumber": cfg("EIP_MERCHANT_NUMBER"),
        "countryCode": "ZW",
        "terminalID": cfg("EIP_TERMINAL_ID"),
        "location": cfg("EIP_LOCATION", "Harare"),
        "superMerchantName": cfg("EIP_SUPER_MERCHANT_NAME"),
        "merchantName": cfg("EIP_MERCHANT_NAME"),
    }


def payment_amount(amount, currency, description):
    return {
        "charginginformation": {"amount": "%.2f" % float(amount), "currency": currency,
                                "description": description},
        "chargeMetaData": {"channel": cfg("EIP_CHANNEL", "WEB")},
    }


# --------------------------------------------------------------------------- lint

def lint(body):
    """Return (errors, warnings) for a charge or refund body."""
    errors, warnings = [], []
    if not isinstance(body, dict):
        return ["the body must be a JSON object"], []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in CASING:
                    errors.append("%s%s: wrong name - EIP expects %r" % (path, k, CASING[k]))
                walk(v, "%s%s." % (path, k))
    walk(body, "")

    # Fields the portal never documents are guesses (often from other EcoCash APIs) and
    # may be rejected; flag them rather than silently sending them.
    known = {"": set(CHARGE_KEYS) | {"originalEcocashReference", "currencyCode"},
             "paymentAmount.": {"charginginformation", "chargeMetaData"},
             "paymentAmount.charginginformation.": {"amount", "currency", "description"},
             "paymentAmount.chargeMetaData.": {"channel"}}

    def undocumented(node, path):
        if isinstance(node, dict) and path in known:
            for k, v in node.items():
                if k not in known[path] and k not in CASING:
                    warnings.append("%s%s is not a documented EIP field - remove it unless "
                                    "EcoCash confirmed it" % (path, k))
                undocumented(v, "%s%s." % (path, k))
    undocumented(body, "")

    is_refund = "originalEcocashReference" in body or body.get("tranType") in ("REF", "REV")
    required = REFUND_REQUIRED if is_refund else CHARGE_REQUIRED
    for k in required:
        if k not in body:
            errors.append("missing %r%s" % (k, " (a refund needs the ORIGINAL charge's EcoCash "
                                                "reference, i.e. its transactionId)"
                                             if k == "originalEcocashReference" else ""))

    pa = body.get("paymentAmount")
    if isinstance(pa, dict):
        ci = pa.get("charginginformation")
        if not isinstance(ci, dict):
            errors.append("paymentAmount.charginginformation is missing (all lowercase)")
        else:
            for k in ("amount", "currency", "description"):
                if k not in ci:
                    errors.append("missing paymentAmount.charginginformation.%s" % k)
            amt = ci.get("amount")
            try:
                val = float(amt)
                if val <= 0:
                    errors.append("amount must be positive (E004)")
                if isinstance(amt, str) and not re.fullmatch(r"\d+(\.\d{1,2})?", amt):
                    errors.append("amount %r has more than 2 decimals or a bad format (E004)" % amt)
                if isinstance(amt, float) and round(amt, 2) != amt:
                    errors.append("amount %r has more than 2 decimals (E004)" % amt)
            except (TypeError, ValueError):
                if amt is not None:
                    errors.append("amount %r is not a number (E004)" % amt)
            if ci.get("currency") not in (None, "USD", "ZWG"):
                errors.append("currency %r must be USD or ZWG (E003)" % ci.get("currency"))
        cm = pa.get("chargeMetaData")
        if not isinstance(cm, dict) or "channel" not in cm:
            errors.append("paymentAmount.chargeMetaData.channel is missing")
        if "amount" in pa or "currency" in pa:
            errors.append("amount/currency belong inside paymentAmount.charginginformation, "
                          "not directly in paymentAmount")
    for k in ("amount", "currency"):
        if k in body:
            errors.append("%r is not a top-level field - it goes in "
                          "paymentAmount.charginginformation" % k)

    tt = body.get("tranType")
    if tt is not None and tt not in ("MER", "REF", "REV"):
        errors.append("tranType %r must be MER, REF or REV" % tt)
    if "originalEcocashReference" in body and tt == "MER":
        warnings.append("refund sent with tranType MER: the Documentation tab says REF/REV, the "
                        "Playground and SDK samples send MER - confirm which the sandbox accepts")
    if not is_refund and tt not in (None, "MER"):
        errors.append("a charge uses tranType MER")

    msisdn = str(body.get("endUserId", ""))
    if msisdn and not re.fullmatch(r"263\d{9}", msisdn):
        if re.fullmatch(r"0\d{9}|\d{9}", msisdn):
            warnings.append("endUserId %r: prefer the 263XXXXXXXXX form (E002 risk)" % msisdn)
        else:
            errors.append("endUserId %r is not a Zimbabwe MSISDN like 263771234567 (E002)" % msisdn)

    corr = str(body.get("clientCorrelator", ""))
    if corr and re.fullmatch(r"(REF|REFUND)-00\d", corr):
        warnings.append("clientCorrelator %r looks hard-coded - it must be unique per attempt (E005)"
                        % corr)
    if "originalEcocashReference" in body and corr and corr == body.get("originalEcocashReference"):
        errors.append("the refund reuses the charge reference as clientCorrelator - use a NEW one")
    if "transactionOperationStatus" in body and body["transactionOperationStatus"] != "Charged":
        warnings.append("transactionOperationStatus is always \"Charged\" in the documented bodies")
    if body.get("countryCode") not in (None, "ZW"):
        errors.append("countryCode must be ZW")
    return errors, warnings


# --------------------------------------------------------------------------- http

def request(method, url, body, dry_run):
    headers = {"Authorization": auth_header(), "Content-Type": "application/json",
               "Accept": "application/json"}
    if dry_run:
        shown = json.loads(json.dumps(body)) if body else None
        if shown and "merchantPin" in shown:
            shown["merchantPin"] = "****"
        print("%s %s\nAuthorization: Basic ****\nContent-Type: application/json" % (method, url))
        if shown is not None:
            print(json.dumps(shown, indent=2))
        return {}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            text = res.read().decode() or "{}"
            return json.loads(text)
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = {"raw": text}
        print("HTTP %d %s" % (e.code, json.dumps(parsed)), file=sys.stderr)
        if e.code in (500, 503):
            print("(%d is retryable with backoff; 4xx errors are not)" % e.code, file=sys.stderr)
        sys.exit(2)
    except (urllib.error.URLError, TimeoutError) as e:
        print("network error: %s" % e, file=sys.stderr)
        if method == "POST" and url.endswith("/transactions/amount/"):
            print("The charge MAY have reached the customer. Do NOT re-run charge - run "
                  "`lookup` with the same --correlator first.", file=sys.stderr)
        sys.exit(3)


def status_of(b):
    return b.get("status") or b.get("transactionStatus") or b.get("transactionOperationStatus")


def lookup_url(base, msisdn, corr):
    q = lambda s: urllib.parse.quote(s, safe="")
    return "%s/%s/transactions/amount/%s" % (base, q(msisdn), q(corr))


# --------------------------------------------------------------------------- commands

GOOD = {
    "clientCorrelator": "3f2b6c1e-9a47-4d0b-8b8e-7c1d2a5e6f90", "notifyUrl": "",
    "referenceCode": "ORDER-1001", "tranType": "MER", "endUserId": "263771234567",
    "remarks": "Order 1001", "transactionOperationStatus": "Charged",
    "paymentAmount": {"charginginformation": {"amount": "10.00", "currency": "USD",
                                              "description": "Order 1001"},
                      "chargeMetaData": {"channel": "WEB"}},
    "merchantCode": "287164", "merchantPin": "1234", "merchantNumber": "778503033",
    "countryCode": "ZW", "terminalID": "TERM001", "location": "Harare",
    "superMerchantName": "EcoCash Sandbox", "merchantName": "Test Merchant",
}


def self_test():
    cases = [("good charge", GOOD, 0)]
    bad = json.loads(json.dumps(GOOD))
    bad["paymentAmount"]["chargingInformation"] = bad["paymentAmount"].pop("charginginformation")
    bad["terminalId"] = bad.pop("terminalID")
    cases.append(("camelCased fields", bad, 4))  # 2 wrong names + the 2 correct ones missing
    refund = json.loads(json.dumps(GOOD))
    refund.update({"tranType": "REF", "clientCorrelator": "9c0e1d2f-0000-4a4a-9b9b-111122223333"})
    cases.append(("refund without originalEcocashReference", refund, 1))
    flat = json.loads(json.dumps(GOOD))
    flat["amount"] = 10
    flat["paymentAmount"]["charginginformation"]["amount"] = "10.001"
    cases.append(("top-level amount, 3 decimals", flat, 2))
    extra = json.loads(json.dumps(GOOD))
    extra["paymentAmount"]["chargeMetaData"]["purchaseCategoryCode"] = "Online Payment"
    extra["sourceReference"] = "abc"
    cases.append(("undocumented fields (warnings, not errors)", extra, 0))
    ok = True
    errs, warns = lint(extra)
    if len(warns) != 2:
        print("  undocumented-field warnings: FAIL (%d, expected 2)" % len(warns))
        ok = False
    for name, body, want in cases:
        errs, _ = lint(body)
        passed = len(errs) == want
        ok &= passed
        print("  %-42s %s (%d error(s), expected %d)" % (name, "PASS" if passed else "FAIL",
                                                        len(errs), want))
    print("\nlinter self-test %s" % ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", help="load EIP_* variables from this file first")
    ap.add_argument("--dry-run", action="store_true", help="print the request, send nothing")
    ap.add_argument("--allow-live", action="store_true", help="allow a non-sandbox EIP_BASE_URL")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("header")
    p = sub.add_parser("lint"); p.add_argument("file")
    p = sub.add_parser("charge")
    p.add_argument("--msisdn", required=True); p.add_argument("--amount", required=True)
    p.add_argument("--currency", default="USD"); p.add_argument("--reference")
    p.add_argument("--correlator"); p.add_argument("--notify-url", default="")
    for name in ("lookup", "wait"):
        p = sub.add_parser(name)
        p.add_argument("--msisdn", required=True); p.add_argument("--correlator", required=True)
        if name == "wait":
            p.add_argument("--timeout", type=int, default=90)
            p.add_argument("--every", type=int, default=3)
    p = sub.add_parser("refund")
    p.add_argument("--msisdn", required=True); p.add_argument("--original-ref", required=True)
    p.add_argument("--amount", required=True); p.add_argument("--currency", default="USD")
    p.add_argument("--reference"); p.add_argument("--tran-type")
    sub.add_parser("self-test")
    a = ap.parse_args()

    if a.env_file:
        load_env_file(a.env_file)

    if a.cmd == "self-test":
        return self_test()
    if a.cmd == "lint":
        body = json.load(sys.stdin if a.file == "-" else open(a.file, encoding="utf-8"))
        errs, warns = lint(body)
        for e in errs:
            print("ERROR   " + e)
        for w in warns:
            print("WARNING " + w)
        print("\n%d error(s), %d warning(s)" % (len(errs), len(warns)))
        return 1 if errs else 0
    if a.cmd == "header":
        print("Authorization: " + auth_header())
        return 0

    base = base_url(a.allow_live)
    if a.cmd == "charge":
        corr = a.correlator or str(uuid.uuid4())
        ref = a.reference or "ORDER-" + corr[:8]
        body = {"clientCorrelator": corr, "notifyUrl": a.notify_url, "referenceCode": ref,
                "tranType": "MER", "endUserId": a.msisdn, "remarks": ref,
                "transactionOperationStatus": "Charged",
                "paymentAmount": payment_amount(a.amount, a.currency, ref)}
        body.update(merchant())
        print("clientCorrelator: %s  (save it - lookups and support need it)" % corr, file=sys.stderr)
        res = request("POST", base + "/transactions/amount/", body, a.dry_run)
    elif a.cmd == "lookup":
        res = request("GET", lookup_url(base, a.msisdn, a.correlator), None, a.dry_run)
    elif a.cmd == "wait":
        deadline = time.monotonic() + a.timeout
        res, st = {}, None
        while time.monotonic() < deadline:
            res = request("GET", lookup_url(base, a.msisdn, a.correlator), None, a.dry_run)
            st = status_of(res)
            print("status: %s" % st, file=sys.stderr)
            if st in ("SUCCESS", "FAILED") or a.dry_run:
                break
            time.sleep(a.every)
        else:
            print("not final after %ds - treat as UNKNOWN (review later), never as failed"
                  % a.timeout, file=sys.stderr)
    else:  # refund
        corr = str(uuid.uuid4())
        ref = a.reference or "REFUND-" + corr[:8]
        body = {"clientCorrelator": corr, "referenceCode": ref,
                "tranType": a.tran_type or cfg("EIP_REFUND_TRAN_TYPE", "REF"),
                "endUserId": a.msisdn, "originalEcocashReference": a.original_ref,
                "remarks": ref, "paymentAmount": payment_amount(a.amount, a.currency, "Refund")}
        body.update(merchant())
        res = request("POST", base + "/transactions/refund/", body, a.dry_run)

    if res:
        print(json.dumps(res, indent=2))
        st = status_of(res)
        if st:
            print("status: %s" % st, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
