#!/usr/bin/env python3
"""Check that the Claude skill in ecocash-skills/ will load and install.

  * SKILL.md starts with YAML frontmatter holding `name` and `description`
  * `name` is kebab-case, at most 64 characters, and matches the folder name
    (claude.ai rejects an upload where they differ)
  * `description` is at most 1024 characters and has no angle brackets
  * SKILL.md stays under 500 lines, so it is cheap to load on every trigger
  * every file SKILL.md points at (references/, templates/, scripts/, config/) exists
  * evals/evals.json parses and names this skill

    python3 tools/check_skill.py
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "ecocash-skills")


def check(folder):
    errors = []
    name = os.path.basename(folder)
    path = os.path.join(folder, "SKILL.md")
    if not os.path.isfile(path):
        return ["%s: SKILL.md is missing" % name]
    text = io.open(path, encoding="utf-8").read()
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["%s: SKILL.md has no YAML frontmatter" % name]
    fm = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" "):
            fm[k.strip()] = v.strip().strip('"').strip("'")
    if fm.get("name") != name:
        errors.append("%s: name %r does not match the folder name" % (name, fm.get("name")))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm.get("name", "")) or len(fm.get("name", "")) > 64:
        errors.append("%s: name must be kebab-case, 64 characters at most" % name)
    desc = fm.get("description", "")
    if not desc:
        errors.append("%s: description is missing" % name)
    if len(desc) > 1024:
        errors.append("%s: description is %d characters (max 1024)" % (name, len(desc)))
    if "<" in desc or ">" in desc:
        errors.append("%s: description contains angle brackets" % name)
    lines = text.count("\n") + 1
    if lines >= 500:
        errors.append("%s: SKILL.md is %d lines (keep it under 500)" % (name, lines))
    body = text[m.end():]
    for ref in sorted(set(re.findall(r"\b((?:references|templates|scripts|config)/[\w./-]+\.\w+)", body))):
        if not os.path.exists(os.path.join(folder, ref)):
            errors.append("%s: SKILL.md points at %s, which does not exist" % (name, ref))
    evals = os.path.join(folder, "evals", "evals.json")
    if os.path.exists(evals):
        try:
            data = json.load(io.open(evals, encoding="utf-8"))
            if data.get("skill_name") != name:
                errors.append("%s: evals.json skill_name is %r" % (name, data.get("skill_name")))
        except ValueError as e:
            errors.append("%s: evals.json does not parse: %s" % (name, e))
    print("  %-28s %s (%d lines, description %d chars)" % (
        name, "PASS" if not errors else "FAIL", lines, len(desc)))
    return errors


def main():
    errors = []
    folders = sorted(os.path.join(SKILLS, d) for d in os.listdir(SKILLS)
                     if os.path.isdir(os.path.join(SKILLS, d)))
    if not folders:
        errors.append("no skill folders in ecocash-skills/")
    for f in folders:
        errors += check(f)
    for e in errors:
        print("::error::%s" % e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
