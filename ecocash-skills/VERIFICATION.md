# Verifying the ecocash-instant-payment skill

What was run against the skill before it was published, and how to repeat it. Everything below
runs offline: nothing touches the real EcoCash sandbox, and no credentials are needed.

## 1. It loads

`tools/check_skill.py` checks what Claude Code and claude.ai need to load the skill:

- `SKILL.md` has YAML frontmatter with `name` and `description`
- `name` is `ecocash-instant-payment`, kebab-case, and matches the folder name
- `description` is under 1024 characters (993) and has no angle brackets
- `SKILL.md` is under 500 lines (about 180)
- every `references/`, `templates/`, `scripts/` and `config/` path that `SKILL.md` mentions exists

## 2. It says what the guide says

`tools/build_skill.py --check` regenerates `references/`, `templates/` and `config/` from
`README.md` and `reference/` in memory and fails if a single byte differs, or if either folder holds
a file the generator didn't write. CI runs it on every push.

## 3. Its code works

`tools/test_examples.py` starts `tools/mock/eip_mock_server.py`, a mock that answers only the three
documented routes under `/sandbox/payment/v1`, and only with the right Basic auth. Then it:

| Run | What is checked | Result |
|:---|:---|:---|
| `templates/node/ecocash.js` | charge, lookup, refund: routes, auth, exact keys, `charginginformation` / `chargeMetaData`, amount `"10.00"` | PASS |
| `templates/python/ecocash.py` | the same | PASS |
| `scripts/eip_cli.py self-test` | the linter against built-in good and bad payloads | PASS |
| `scripts/eip_cli.py charge / lookup / refund` | the same route, auth and key checks as the templates | PASS |
| `templates/php-laravel/*.php` | `php -l` syntax check | PASS |

The templates are the README's section 8 code blocks, byte for byte, so this is the same code the
guide publishes. The Java (Spring `RestClient`) and C# (.NET 8 `HttpClient`) templates were run
against the same mock when the guide was written; CI syntax-checks only what its runner has
toolchains for.

`eip_cli.py` also refuses a non-sandbox base URL without `--allow-live`, masks the password and
merchant PIN under `--dry-run`, and never retries `charge`.

## 4. It helps

Three realistic tasks from `evals/evals.json` were each given to Claude with the skill installed
and without it (same model, no network access), and the answers graded against the same checks:

| Task | With the skill | Without |
|:---|:---|:---|
| `laravel-ticket-checkout`: service, config, start and poll endpoints | 7/7 | 4/7 |
| `broken-refund-payload`: diagnose a refund returning 400 and 409 | 8/8 | 7/8 |
| `dotnet-404-base-path`: every .NET call returns 404 | 5/5 | 2/5 |
| **Pass rate** | **100%** | **62%** |
| Tokens per task (mean) | about 108k | about 87k |
| Time per task (mean) | about 121 s | about 74 s |

Without the skill, the answers built against a different, invented EcoCash API (an `X-API-KEY`
header, other paths and field names), removed the required trailing slash, read the wrong status
field, and presented the unconfirmed refund `tranType` as settled. With it, the answers used the
documented routes and field names and flagged the three open portal questions instead of guessing.
The cost is about 20k extra tokens per task, mostly from reading reference files.

Three tasks is a small sample. Treat the numbers as a sanity check rather than a guarantee, and
review generated payment code as you would any other.

## Repeat it

```bash
python3 tools/check_skill.py
python3 tools/build_skill.py --check
python3 tools/test_examples.py
python3 ecocash-skills/ecocash-instant-payment/scripts/eip_cli.py self-test
```
