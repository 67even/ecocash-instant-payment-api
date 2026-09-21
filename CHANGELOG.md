# Changelog

All notable changes to this guide are recorded here. Each version is tagged `vX.Y.Z` and
published as a [GitHub Release](https://github.com/67even/ecocash-instant-payment-api/releases)
with the Claude skill zip attached.

## 1.0.0 — 2026-09-21

First release.

- **README guide** in thirteen sections: overview, sandbox access, authentication, first
  payment, API reference, statuses and errors, sandbox testing, SDKs and code examples,
  going live, troubleshooting, known portal inconsistencies, Claude skill, and about.
- **Claude skill** `ecocash-instant-payment` in `ecocash-skills/`, installable in Claude Code
  and on claude.ai. Its references, templates and `.env` template are generated from the
  README by `tools/build_skill.py`; `scripts/eip_cli.py` builds the auth header, lints
  payloads and runs charge, lookup and refund against the sandbox. Benchmarked on three
  tasks: 100% of checks passed with the skill, 62% without. Install guide on the site at
  `/install/`.
- **Code examples** for PHP/Laravel, Node.js, Python, Java (Spring `RestClient`) and
  C# (.NET 8 `HttpClient`). Each was run against a mock EIP server that checks the
  paths, the Basic auth header and the exact field names.
- **Portal screenshots** for every onboarding step.
- **Documentation site** at https://67even.github.io/ecocash-instant-payment-api/, generated from the
  README by `tools/build_docs.py`, with Open Graph cards, sitemap and JSON-LD
  structured data.
- **Reference files**: the portal's Documentation tab and SDKs & Codegen tab reproduced
  verbatim in `reference/`, plus a portal walkthrough.
