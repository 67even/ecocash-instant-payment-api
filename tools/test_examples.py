#!/usr/bin/env python3
"""Run the README's clients and the Claude skill's CLI against a mock EIP server.

The mock (tools/mock/eip_mock_server.py) answers only the three documented routes
UNDER the base path /sandbox/payment/v1, and only with the right Basic auth. So
a client that drops the base path, sends the wrong auth, or misspells a field
(charginginformation, chargeMetaData, terminalID) fails here rather than in
someone's integration.

The skill's scripts/eip_cli.py is held to the same checks: its linter self-test must
pass, and its charge -> lookup -> refund must hit the same routes with the same keys.

The PHP, Java and C# examples are syntax-checked where a toolchain exists
(php -l); they were run against the same mock when the guide was written.

    python3 tools/test_examples.py
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8765
ENV = {
    "EIP_BASE_URL": "http://127.0.0.1:%d/sandbox/payment/v1" % PORT,
    "EIP_USERNAME": "sbx_test", "EIP_PASSWORD": "secret",
    "EIP_MERCHANT_CODE": "287164", "EIP_MERCHANT_PIN": "1234",
    "EIP_MERCHANT_NUMBER": "778503033", "EIP_TERMINAL_ID": "TERM001",
    "EIP_MERCHANT_NAME": "Test Merchant", "EIP_SUPER_MERCHANT_NAME": "EcoCash Sandbox",
    "EIP_CHANNEL": "WEB", "EIP_LOCATION": "Harare", "EIP_REFUND_TRAN_TYPE": "REF",
}
CHARGE_KEYS = {"clientCorrelator", "notifyUrl", "referenceCode", "tranType", "endUserId",
               "remarks", "transactionOperationStatus", "paymentAmount", "merchantCode",
               "merchantPin", "merchantNumber", "countryCode", "terminalID", "location",
               "superMerchantName", "merchantName"}
REFUND_KEYS = (CHARGE_KEYS - {"notifyUrl", "transactionOperationStatus"}) | {"originalEcocashReference"}
PATHS = [("POST", "/sandbox/payment/v1/transactions/amount/"),
         ("GET", "/sandbox/payment/v1/263771234567/transactions/amount/CORR-1"),
         ("POST", "/sandbox/payment/v1/transactions/refund/")]


def blocks(lang):
    text = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    return re.findall(r"```%s\n(.*?)```" % lang, text, re.S)


def verify(log, name):
    recs = [json.loads(l) for l in io.open(log, encoding="utf-8")]
    bad = []
    if [(r["method"], r["path"]) for r in recs] != PATHS:
        bad.append("requests were %s" % [(r["method"], r["path"]) for r in recs])
    for r in recs:
        if not r["auth_ok"]:
            bad.append("%s %s: wrong Authorization header" % (r["method"], r["path"]))
        b = r["body"]
        if r["method"] != "POST":
            continue
        want = CHARGE_KEYS if r["path"].endswith("/amount/") else REFUND_KEYS
        if set(b) != want:
            bad.append("%s: keys differ by %s" % (r["path"], sorted(set(b) ^ want)))
        pa = b.get("paymentAmount", {})
        if set(pa) != {"charginginformation", "chargeMetaData"}:
            bad.append("%s: paymentAmount keys %s" % (r["path"], sorted(pa)))
        elif pa["charginginformation"].get("amount") != "10.00":
            bad.append("%s: amount %r, expected '10.00'" % (r["path"], pa["charginginformation"].get("amount")))
    for b in bad:
        print("::error::%s example: %s" % (name, b))
    print("  %-8s %s" % (name, "PASS" if not bad else "FAIL"))
    return not bad


def run(name, cmd, cwd, log):
    if os.path.exists(log):
        os.unlink(log)
    env = dict(os.environ, **ENV)
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        print("::error::%s example crashed:\n%s%s" % (name, res.stdout, res.stderr))
        return False
    return verify(log, name)


def main():
    work = tempfile.mkdtemp()
    log = os.path.join(work, "log.jsonl")
    server = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "mock", "eip_mock_server.py"),
                               str(PORT), log])
    time.sleep(1)
    ok = True
    try:
        if shutil.which("node"):
            io.open(os.path.join(work, "ecocash.js"), "w").write(blocks("javascript")[0])
            io.open(os.path.join(work, "t.mjs"), "w").write(
                "import { charge, lookup, refund, referenceOf } from './ecocash.js';\n"
                "const c = await charge({ msisdn: '263771234567', amount: '10', reference: 'ORDER-1', correlator: 'CORR-1' });\n"
                "await lookup('263771234567', 'CORR-1');\n"
                "await refund({ msisdn: '263771234567', originalReference: referenceOf(c), amount: 10, reference: 'RF-1' });\n")
            ok &= run("node", ["node", "t.mjs"], work, log)
        io.open(os.path.join(work, "ecocash.py"), "w").write(blocks("python")[0])
        ok &= run("python", [sys.executable, "-c",
                             "import ecocash as e\n"
                             "c=e.charge('263771234567','10','ORDER-1','CORR-1')\n"
                             "e.lookup('263771234567','CORR-1')\n"
                             "e.refund('263771234567', e.reference_of(c), 10, 'RF-1')\n"], work, log)
        cli = [sys.executable, os.path.join(ROOT, "ecocash-skills", "ecocash-instant-payment",
                                            "scripts", "eip_cli.py")]
        res = subprocess.run(cli + ["self-test"], capture_output=True, text=True, timeout=60)
        print("  %-8s %s" % ("lint", "PASS" if res.returncode == 0 else "FAIL"))
        if res.returncode:
            print("::error::eip_cli.py self-test failed:\n%s%s" % (res.stdout, res.stderr))
            ok = False
        # the mock is not the sandbox host, so --allow-live is needed to reach it
        script = ("set -e\n"
                  "%(c)s charge --msisdn 263771234567 --amount 10 --reference ORDER-1 "
                  "--correlator CORR-1 --notify-url https://example.com/eip/notify\n"
                  "%(c)s lookup --msisdn 263771234567 --correlator CORR-1\n"
                  "%(c)s refund --msisdn 263771234567 --original-ref MOCK-REF --amount 10 "
                  "--reference RF-1\n") % {"c": " ".join('"%s"' % a for a in cli + ["--allow-live"])}
        ok &= run("cli", ["bash", "-c", script], work, log)
        if shutil.which("php"):
            for i, code in enumerate(blocks("php")):
                src = code if code.lstrip().startswith("<?php") else "<?php\n" + (
                    "return [" + code + "];" if code.lstrip().startswith("'") else code)
                f = os.path.join(work, "ex%d.php" % i)
                io.open(f, "w").write(src)
                res = subprocess.run(["php", "-l", f], capture_output=True, text=True)
                print("  %-8s %s" % ("php #%d" % (i + 1), "PASS" if res.returncode == 0 else "FAIL"))
                if res.returncode:
                    print("::error::PHP example %d: %s" % (i + 1, res.stdout.strip()))
                    ok = False
    finally:
        server.terminate()
        shutil.rmtree(work, ignore_errors=True)
    print("\nall examples behave" if ok else "\nexample failures above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
