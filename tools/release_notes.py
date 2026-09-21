#!/usr/bin/env python3
"""Print the release notes for one version, taken from CHANGELOG.md.

The release workflow (.github/workflows/release.yml) runs this when a `vX.Y.Z` tag is
pushed. It fails if CHANGELOG.md has no `## X.Y.Z` entry, so a tag cannot be released
without notes.

    python3 tools/release_notes.py v1.0.0            # notes for v1.0.0
    python3 tools/release_notes.py v1.0.0 --title    # just the release title
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/67even/ecocash-instant-payment-api"
SITE = "https://67even.github.io/ecocash-instant-payment-api"


def entry(version):
    text = io.open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(r"^## %s(?: [^\n]*)?\n(.*?)(?=^## |\Z)" % re.escape(version), text, re.S | re.M)
    if not m:
        sys.exit("CHANGELOG.md has no '## %s' entry - add one before tagging v%s" % (version, version))
    heading = text[m.start():text.index("\n", m.start())]
    return heading, m.group(1).strip()


def main():
    if len(sys.argv) < 2 or not re.fullmatch(r"v\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: release_notes.py vX.Y.Z [--title]")
    tag = sys.argv[1]
    heading, body = entry(tag[1:])
    if "--title" in sys.argv:
        date = heading.split(" ", 2)[2].lstrip("—- ").strip() if heading.count(" ") >= 2 else ""
        print("EcoCash EIP developer guide %s%s" % (tag, " (%s)" % date if date else ""))
        return 0
    print(body)
    print("""
## Downloads

- **`ecocash-instant-payment.zip`**: the Claude skill, ready to upload on claude.ai
  (**Customize → Skills → + → Create skill → Upload a skill**). For Claude Code, unzip it into
  `~/.claude/skills/` or your project's `.claude/skills/`.
  [Install guide](%(site)s/install/)

## Links

- Documentation: %(site)s/
- Changes since the previous release: see [CHANGELOG.md](%(repo)s/blob/%(tag)s/CHANGELOG.md)

This is an independent, community-maintained guide. It is not affiliated with, endorsed by,
or supported by EcoCash Holdings Zimbabwe.""" % {"site": SITE, "repo": REPO, "tag": tag})
    return 0


if __name__ == "__main__":
    sys.exit(main())
