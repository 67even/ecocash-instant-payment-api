import os
import time
import uuid

import requests

BASE_URL = os.environ.get(
    "EIP_BASE_URL", "https://developers.ecocash.co.zw/sandbox/payment/v1"
).rstrip("/")
REFUND_TRAN_TYPE = os.environ.get("EIP_REFUND_TRAN_TYPE", "REF")

session = requests.Session()
session.auth = (os.environ["EIP_USERNAME"], os.environ["EIP_PASSWORD"])
session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})


class EcoCashError(Exception):
    def __init__(self, status, body):
        super().__init__(f"EIP {status}: {body.get('statusMessage', 'request failed')}")
        self.status, self.body = status, body


def _merchant():
    return {
        "merchantCode": os.environ["EIP_MERCHANT_CODE"],
        "merchantPin": os.environ["EIP_MERCHANT_PIN"],
        "merchantNumber": os.environ["EIP_MERCHANT_NUMBER"],
        "countryCode": "ZW",
        "terminalID": os.environ["EIP_TERMINAL_ID"],
        "location": os.environ.get("EIP_LOCATION", "Harare"),
        "superMerchantName": os.environ["EIP_SUPER_MERCHANT_NAME"],
        "merchantName": os.environ["EIP_MERCHANT_NAME"],
    }


def _amount(amount, currency, description):
    return {
        "charginginformation": {
            "amount": f"{float(amount):.2f}",  # "2.00" - see section 4.5
            "currency": currency,
            "description": description,
        },
        "chargeMetaData": {"channel": os.environ.get("EIP_CHANNEL", "WEB")},
    }


def _call(method, path, payload=None):
    resp = session.request(method, BASE_URL + path, json=payload, timeout=30)
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if not resp.ok:
        raise EcoCashError(resp.status_code, body)
    return body


def charge(msisdn, amount, reference, correlator, currency="USD", notify_url=""):
    """Start a charge. Persist `correlator` BEFORE calling this."""
    return _call("POST", "/transactions/amount/", {
        "clientCorrelator": correlator,
        "notifyUrl": notify_url,
        "referenceCode": reference,
        "tranType": "MER",
        "endUserId": msisdn,
        "remarks": reference,
        "transactionOperationStatus": "Charged",
        "paymentAmount": _amount(amount, currency, reference),
        **_merchant(),
    })


def lookup(msisdn, correlator):
    q = requests.utils.quote
    return _call("GET", f"/{q(msisdn, safe='')}/transactions/amount/{q(correlator, safe='')}")


def refund(msisdn, original_reference, amount, reference, currency="USD"):
    return _call("POST", "/transactions/refund/", {
        "clientCorrelator": str(uuid.uuid4()),  # a NEW correlator
        "referenceCode": reference,
        "tranType": REFUND_TRAN_TYPE,
        "endUserId": msisdn,
        "originalEcocashReference": original_reference,
        "remarks": reference,
        "paymentAmount": _amount(amount, currency, "Refund"),
        **_merchant(),
    })


def status_of(body):
    """`status` is documented; the portal's SDK samples read two other names."""
    return body.get("status") or body.get("transactionStatus") or body.get("transactionOperationStatus")


def reference_of(body):
    return body.get("ecocashReference") or body.get("transactionId")


def wait_for_result(msisdn, correlator, timeout=90, every=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = status_of(lookup(msisdn, correlator))
        if status in ("SUCCESS", "FAILED"):
            return status
        time.sleep(every)
    return "UNKNOWN"  # not final: flag for review, never assume failure
