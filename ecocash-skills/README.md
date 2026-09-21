# EcoCash Claude skills

Claude skills built from this repository's guide to the **EcoCash Instant Payment (EIP) API**.
Install and usage instructions are in [section 12 of the README](../README.md#12-claude-skill) and
on the site at <https://67even.github.io/ecocash-instant-payment-api/install/>.

| Skill | Use it for |
|:---|:---|
| [`ecocash-instant-payment`](ecocash-instant-payment/) | Building, debugging and reviewing server-side integrations that charge an EcoCash wallet by USSD PIN prompt, look the transaction up and refund it. |

## Layout

```text
ecocash-instant-payment/
├── SKILL.md                    hand-written: setup, endpoints, payload and payment-flow rules,
│                               the three unconfirmed portal details, when to read what
├── references/                 GENERATED from README sections 2-11 and reference/
│   ├── portal-onboarding.md        section 2  - sandbox access, credentials, test numbers
│   ├── authentication.md           section 3  - Basic auth, storing credentials, 401/403
│   ├── first-payment.md            section 4  - charge, approve, look up, refund with cURL
│   ├── api-reference.md            section 5  - every endpoint, field and HTTP status
│   ├── statuses-and-errors.md      section 6  - statuses, E001-E015, retry rules
│   ├── sandbox-testing.md          section 7  - PIN matrix, merchant values, checklist
│   ├── code-examples.md            section 8  - language guidance, SDK sample pitfalls
│   ├── go-live.md                  section 9  - production access and checklist
│   ├── troubleshooting.md          section 10 - symptom, cause, fix
│   ├── known-issues.md             section 11 - where the portal contradicts itself
│   ├── portal-documentation-tab.md reference/ECOCASH-EIP-API.md, verbatim
│   └── portal-sdk-samples.md       reference/ECOCASH-EIP-SDK-REFERENCE.md, verbatim
├── templates/                  GENERATED from the tested code blocks of README section 8
│   ├── php-laravel/            config-services-ecocash.php, EcoCash.php
│   ├── node/ecocash.js
│   ├── python/ecocash.py
│   ├── java/                   application.yml, EcoCashClient.java
│   └── dotnet/EcoCashClient.cs
├── config/eip.env.example      GENERATED from the .env block in README section 3.2
├── scripts/eip_cli.py          hand-written, standard library only: header, lint, charge,
│                               lookup, wait, refund, self-test
└── evals/evals.json            benchmark prompts and checks (left out of the claude.ai zip)
```

## Keeping it in sync

Only `SKILL.md`, `scripts/` and `evals/` are edited by hand. Everything else is regenerated from
the README, so the skill never knows more or less than the guide:

```bash
python3 tools/build_skill.py          # regenerate references/, templates/, config/
python3 tools/build_skill.py --check  # CI: fail if the skill has drifted from the README
python3 tools/check_skill.py          # CI: frontmatter, size and file references
python3 tools/test_examples.py        # CI: templates and eip_cli.py against the mock EIP server
```

What was run to check the skill, and the results, are in [VERIFICATION.md](VERIFICATION.md).
