---
name: ecocash-instant-payment
description: "EcoCash Instant Payment (EIP) API integration expert for Zimbabwe's EcoCash online payment gateway (developers.ecocash.co.zw): charging a customer's EcoCash wallet via a USSD PIN prompt, looking up a transaction, refunding or reversing it, the sandbox, and going live. EIP's request format is unusual and its developer portal contradicts itself, so consult this skill for any EcoCash EIP code, code review, error, sandbox or go-live question, even a quick one, in any language (PHP/Laravel, Node.js, Python, Java, C#, cURL). Recognise it by: EcoCash or EIP; POST /transactions/amount/ or /transactions/refund/; GET /{endUserId}/transactions/amount/{clientCorrelator}; charginginformation, chargeMetaData, terminalID, clientCorrelator, endUserId, merchantPin, originalEcocashReference; tranType MER/REF/REV; sandbox PINs 0000/1111/2222/9999; errors E001-E015; sbx_ credentials; whitelisting test numbers. Not for Paynow checkout (where EcoCash is one payment option) or other mobile-money APIs."
---

# EcoCash Instant Payment (EIP)

EIP lets a merchant's **server** charge a customer's EcoCash wallet. EcoCash sends the customer a
**USSD PIN prompt**, the customer approves on their phone, and the merchant learns the outcome by
callback or by looking the transaction up. Money moves, so correctness beats speed: most rules
below exist because breaking them loses a payment, charges someone twice, or leaks the merchant PIN.

This skill knows exactly what the EcoCash EIP guide at
https://67even.github.io/ecocash-instant-payment-api/ knows (portal checked 21 Sep 2026). The
`references/` files are generated from that guide; `references/portal-documentation-tab.md` and
`references/portal-sdk-samples.md` are the portal's own pages, verbatim.

## 1. Setup and authentication

1. **Sandbox access comes from the EcoCash Developer Portal** (https://developers.ecocash.co.zw/portal):
   register → EcoCash Instant Payment → **Authentication** → *Request Sandbox Access* → username
   and password arrive in the portal **Inbox** (username starts `sbx_`) → *Save & Activate* →
   **Test Numbers** → add and OTP-verify an EcoCash-registered MSISDN. Walk a newcomer through
   `references/portal-onboarding.md`.
2. **Auth is HTTP Basic on every request**: `Authorization: Basic base64(username:password)`, plus
   `Content-Type: application/json`. No tokens, no expiry, no refresh. `401` (`E006`) = bad or
   malformed header; `403` (`E007`) = sandbox not activated (`references/authentication.md`).
3. **Sandbox base URL:** `https://developers.ecocash.co.zw/sandbox/payment/v1`. The cURL sample on
   the portal's Authentication tab points at `http://localhost:8080/...`: never copy it.
4. **Everything lives in config**, never in code: credentials, the merchant values and the three
   "first-run" settings in §4. Start from `config/eip.env.example`. Merchant values: use the set on
   the developer's own Authentication tab → *Credential Reference* (sandbox: `287164` / `1234` /
   `778503033` / `TERM001` / `WEB`); the Documentation tab's Test Data shows a different set
   (`001535` / `788732685` / `UAT00003` / `POS`) - see `references/sandbox-testing.md`.
5. **Server-side only.** The Basic credentials and `merchantPin` must never reach a browser or app.

Run `python3 scripts/eip_cli.py --env-file .env charge --msisdn 2637XXXXXXXX --amount 1` once
credentials exist: it is the fastest proof that auth, merchant values and the test number work.

## 2. Endpoints

Base URL + path, Basic auth on all of them. **Keep the trailing slashes exactly as shown.**

| Purpose | Method + path | Success |
|---|---|---|
| Charge a wallet | `POST /transactions/amount/` | `200`, `status: PENDING` |
| Look up a charge | `GET /{endUserId}/transactions/amount/{clientCorrelator}` (no trailing slash) | `200` with `status` |
| Refund (`REF`) / reversal (`REV`) | `POST /transactions/refund/` | `200`, `status: SUCCESS` |

Every field, response and status table: `references/api-reference.md`.

## 3. Payload rules (the unusual part)

- **Exact key spelling**, because serialisers that "fix" casing break the request:
  `charginginformation` (all lowercase), `chargeMetaData` (capital M and D), `terminalID`
  (capital ID), `endUserId`, `clientCorrelator`, `merchantPin`, `notifyUrl`, `superMerchantName`.
  In typed languages use explicit JSON names (`[JsonPropertyName]`, `@JsonProperty`) or maps.
- **`amount` and `currency` sit inside `paymentAmount.charginginformation`**, with `description`;
  `chargeMetaData.channel` sits next to it. They are not top-level keys.
- A **charge** sends all 16 documented keys: `clientCorrelator`, `notifyUrl` (may be `""`),
  `referenceCode`, `tranType: "MER"`, `endUserId`, `remarks`, `transactionOperationStatus: "Charged"`,
  `paymentAmount`, `merchantCode`, `merchantPin`, `merchantNumber`, `countryCode: "ZW"`,
  `terminalID`, `location`, `superMerchantName`, `merchantName`.
- A **refund** is the same shape plus **`originalEcocashReference`** (required even though the
  portal's example body omits it) = the charge's `transactionId`; take `ecocashReference` if a
  response carries it. It needs a **new** `clientCorrelator`, an amount no greater than the
  original, and only works on a **SUCCESS** charge. The response returns the reference as
  `originalReference`.
- **`endUserId`**: use `263XXXXXXXXX`. The portal normalises `263…` and `07…`; the 9-digit form in
  its examples is not covered by that note. Only whitelisted, verified numbers work in the sandbox.
- **`clientCorrelator`**: a new unique value (UUID) per charge and per refund, **saved before the
  request is sent**. It is the only key for lookups. Portal samples hard-code `"REF-001"`: never do.
- **Currencies:** `USD`, `ZWG`. Amount: positive, at most 2 decimal places.

`python3 scripts/eip_cli.py lint body.json` checks a payload against all of these.

## 4. Three details the portal contradicts itself on

Keep each one as **one config value** so it can be switched after the first sandbox run. Never
present either side as settled; say it must be confirmed.

| Detail | Try first | Fallback if rejected |
|---|---|---|
| `amount` format | two-decimal string `"10.00"` (Playground + SDK samples) | JSON number `10` (Documentation examples) |
| Refund `tranType` | `REF` / `REV` (Documentation) → `EIP_REFUND_TRAN_TYPE` | `MER` plus top-level `currencyCode` (Playground + SDK samples) |
| Merchant values | the developer's Authentication tab set | the Documentation's Test Data set |

The full list, including contradictions inside the Documentation tab (e.g. `E005` vs "reuse returns
the existing transaction"; PINs `1111`/`9999` as `200` vs `422`), is in `references/known-issues.md`.

## 5. The payment flow

```
save order + new clientCorrelator → POST charge → 200 PENDING (accepted, NOT paid)
→ customer approves USSD prompt → callback to notifyUrl and/or lookup → SUCCESS | FAILED
→ fulfil only on SUCCESS → (refund later: new correlator + originalEcocashReference)
```

- **HTTP 200 means accepted, not paid.** Every sandbox PIN outcome, failures included, returns
  `200`. Branch on `status`, never on the transport code or on `statusMessage` (the documented
  charge example says "Transaction Successful" while `status` is `PENDING`).
- **Read the status defensively**: `status`, then `transactionStatus`, then
  `transactionOperationStatus` - the portal's SDK samples read the latter two names.
- **Final statuses:** `SUCCESS`, `FAILED`. Treat anything else as **not final**: keep checking, then
  mark it *unknown* for review. Never turn a timeout into "failed".
- **Never re-send a charge after a timeout or network error.** It may already have reached the
  phone. Look it up with the **same** `clientCorrelator` first.
- **Polling:** wait ~3 s, look up every 3 s (sandbox resolves in 12-30 s), stop after ~90 s and mark
  unknown; re-check later in a background job, not inside the web request.
- **Callbacks (`notifyUrl`, HTTPS):** the payload, signature header and retry policy are not
  published. Answer `200` fast, confirm with a lookup before fulfilling, process each correlator
  once. The portal's Terms of Use require validating the HMAC signature; the header and secret must
  come from EcoCash.
- **Retries:** only `500` (`E014`, with backoff) and `503` (`E015`). Every `4xx` fails identically on
  replay. Log `statusCode` (a string) and `statusMessage`; redact `merchantPin` from logs.
- **Rate limit:** 500 requests/minute; the response to exceeding it is undocumented - back off on `429`.

Status and error tables (E001-E015, with fixes): `references/statuses-and-errors.md`.

## 6. Templates

Copy the matching template into the project and adapt it; don't write a client from scratch.
Each one was run against a mock EIP server that checks paths, auth and exact field names.

| Stack | Files |
|---|---|
| PHP / Laravel | `templates/php-laravel/EcoCash.php` (service: `charge`, `lookup`, `refund`, `status`, `reference`) + `config-services-ecocash.php` (the `services.ecocash` entry) |
| Node.js 18+ | `templates/node/ecocash.js` (`charge`, `lookup`, `refund`, `statusOf`, `referenceOf`, `waitForResult`) |
| Python | `templates/python/ecocash.py` (`requests`; `charge`, `lookup`, `refund`, `wait_for_result`) |
| Java / Spring Boot 3.2+ | `templates/java/EcoCashClient.java` + `application.yml` (`RestClient`, maps keep exact keys) |
| C# / .NET 8 | `templates/dotnet/EcoCashClient.cs` (`HttpClient`, `JsonObject` keeps exact keys) |

When adapting: keep URL building by plain string joining (or a trailing-slash base plus relative
paths), keep the fallback status reader, keep the correlator saved before the call, and move
polling into a queue/job. If the stack is clear from the repo, pick its template without asking.

**Reviewing or fixing code copied from the portal's SDK tab?** Read `references/code-examples.md`
§8.7 first. The big ones: base path `/sandbox/payment/v1` silently dropped (PHP Guzzle/Symfony
`base_uri`, C# `HttpClient` `BaseAddress`, Python aiohttp - a leading-slash path replaces the base
path), status read under the wrong name, hard-coded correlators, C# `await using` on an
`IDisposable`, Refit sending `Bearer` instead of `Basic`, undefined DTOs losing the key casing.
The verbatim samples are in `references/portal-sdk-samples.md`.

## 7. Scripts

`scripts/eip_cli.py` (Python 3, standard library only; reads the same `EIP_*` variables):

- `header` - the Basic `Authorization` header.
- `lint FILE|-` - checks a charge/refund body: key casing, placement of amount/currency, amount
  format, currency, `tranType`, MSISDN, hard-coded correlators, missing `originalEcocashReference`.
- `charge`, `lookup`, `wait`, `refund` - sandbox calls; `--dry-run` prints the request with secrets
  masked. It refuses a non-sandbox base URL without `--allow-live`, and `charge` never retries.
- `self-test` - checks the linter.

Use it to prove credentials, reproduce a user's failure outside their app, or lint a payload they
paste.

## 8. Sandbox testing and go-live

- **Test PINs** (entered by the customer at the USSD prompt; merchant PIN stays `1234`): `0000`
  success, `1111` insufficient balance, `2222` invalid PIN, `9999` limit exceeded. SMS starts
  `SANDBOX TEST:`. Checklist `TC-001`…`TC-006` and portal tools (Playground, Test Scenarios,
  Request Console): `references/sandbox-testing.md`.
- **Production** (Production tab): validate the merchant MSISDN → capture sandbox test evidence →
  download the *completed* test script → submit; review target 2 business days; production
  credentials arrive in the portal Inbox. Walk through `references/go-live.md` before a user applies.

## 9. When answering or reviewing

- **Debugging starts from the symptom**: `references/troubleshooting.md` maps symptoms to causes
  (404 everywhere = dropped base path; 401/403; E001-E015; stuck PENDING; refund 409/422; no SMS; no
  OTP). A first-principles walkthrough of a working charge is in `references/first-payment.md`.
- **Cite the rule and its reason**, e.g. "this re-sends the charge after a timeout, which can charge
  the customer twice; look it up with the same clientCorrelator instead".
- **Keep official facts separate from recommendations.** The portal does not document: the
  callback payload, signature header or retries; the full `status` list; which `statusCode` goes with
  each `Exxx`; the rate-limit response; a production base URL; whether `ZWG` works on every
  endpoint. Say so and point to EcoCash support (servicedelivery@ecocash.co.zw) rather than inventing.
- **Reviewing an integration:** check it against §3 and §5 line by line, then `references/go-live.md`.
