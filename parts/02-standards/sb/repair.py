# -*- coding: utf-8 -*-
"""repair.py - fixes only the things that have one correct answer.

Two of them:

  links   A link with a stray '.md' on the end, where the note it means plainly exists.
          [[Pricing.md]] never finds anything; [[Pricing]] does.
  kinds   A note whose kind has exactly one proper home on your list - 'book' meaning
          'resource', 'people' meaning 'person'.

Everything else is left for you. A name used twice, a link to a note that was never written,
a kind that is not on the list and has nowhere obvious to go - all of those need a decision,
and a program guessing at your meaning is worse than a problem you can see.

Nothing is written unless you add --apply. Run it without that first and read what it would do.
"""

import collections
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
SCHEMA_PATH = HERE / "_schema" / "note-types.json"

# Non-greedy to the first ']]' - see doctor.py, WHY 2.
LINK = re.compile(r"\[\[(.+?)\]\]")
SKIPPED = []


def split_link(inner):
    """Separate the note being pointed at from any heading or alias after it, so a rewrite
    puts back exactly what it found."""
    rest = ""
    if "|" in inner:
        inner, alias = inner.split("|", 1)
        rest = "|" + alias
    if "#" in inner:
        inner, head = inner.split("#", 1)
        rest = "#" + head + rest
    return inner, rest


def read_text(path):
    """Strict reading only. The check may read a damaged file loosely because it only counts;
    a repair must not, because writing a loosely-read file back would replace the damaged parts
    with question marks and destroy them for good."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        SKIPPED.append(path)
        return ""


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def scoped(schema):
    excl = set(schema.get("scope", {}).get("exclude_path_parts", []))
    excl_files = set(schema.get("scope", {}).get("exclude_files", []))
    return [p for p in VAULT.rglob("*.md")
            if not (set(p.parts) & excl) and p.name not in excl_files]


def fix_links(files, apply_it):
    """Removing a stray '.md' is only a fix when the name it leaves behind means ONE note.

    Found by testing: [[Pricing.md]] pointed at nothing, and 'fixing' it to [[Pricing]] where two
    notes are called Pricing swapped a broken link for one that silently resolves to whichever was
    found first. That is worse - a broken link announces itself, an ambiguous one does not. So a
    target whose name is used more than once is left alone and reported for you to decide.
    """
    stems = collections.Counter(p.stem.lower() for p in files)
    ambiguous = []
    changed, total = [], 0
    for p in files:
        s = read_text(p)
        if ".md" not in s or "[[" not in s:
            continue
        hits = [0]

        def repl(m):
            target, rest = split_link(m.group(1))
            t = target.rstrip()
            if not t.lower().endswith(".md"):
                return m.group(0)
            leaf = re.split(r"[\\/]", t)[-1]
            n = stems.get(leaf[:-3].lower(), 0)
            if n == 1:
                hits[0] += 1
                return "[[%s%s]]" % (t[:-3], rest)
            if n > 1:
                ambiguous.append((p, leaf[:-3]))
            return m.group(0)

        new = LINK.sub(repl, s)
        if hits[0]:
            total += hits[0]
            changed.append((p, hits[0]))
            if apply_it and new != s:
                atomic_write(p, new)
    return {"count": total, "files": changed, "ambiguous": ambiguous}


def fix_kinds(files, schema, apply_it):
    aliases = dict((k.lower(), v) for k, v in schema.get("aliases", {}).items()
                   if not k.startswith("$"))
    changed = []
    for p in files:
        s = read_text(p)
        if not s:
            continue
        bom = "﻿" if s.startswith("﻿") else ""      # keep it; removing it changes bytes
        body = s[len(bom):]
        if not body.startswith("---"):
            continue
        end = body.find("\n---", 3)
        if end == -1:
            continue
        head, tail = bom + body[:end + 1], body[end + 1:]
        m = re.search(r"^(type:\s*)([^\r\n]+)$", head, re.M)
        if not m:
            continue
        raw = m.group(2).strip().strip("\"'")
        canon = aliases.get(raw.lower())
        if not canon or canon == raw:
            continue
        changed.append((p, "%s -> %s" % (raw, canon)))
        if apply_it:
            atomic_write(p, head[:m.start(2)] + canon + head[m.end(2):] + tail)
    return {"count": len(changed), "files": changed}


def main(argv):
    apply_it = "--apply" in argv
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    files = scoped(schema)
    print("\n  %s - %d notes\n" % ("REPAIRING" if apply_it else "SHOWING WHAT WOULD CHANGE",
                                   len(files)))

    r = fix_links(files, apply_it)
    print("  links   %d with a stray .md, in %d notes" % (r["count"], len(r["files"])))
    for p, n in sorted(r["files"], key=lambda x: -x[1])[:6]:
        print("            %3d  %s" % (n, p.relative_to(VAULT)))
    if r["ambiguous"]:
        print("  left    %d link(s) alone: the name they would resolve to belongs to more than"
              % len(r["ambiguous"]))
        print("          one note, so there is no single right answer. Yours to decide:")
        for p, name in r["ambiguous"][:6]:
            print("            %-24s in %s" % (name, p.relative_to(VAULT)))

    k = fix_kinds(files, schema, apply_it)
    print("  kinds   %d with a kind that has one proper home" % k["count"])
    for p, d in k["files"][:6]:
        print("            %-22s %s" % (d, p.relative_to(VAULT)))

    if SKIPPED:
        print("\n  %d file(s) could not be read safely and were left alone:" % len(set(SKIPPED)))
        for p in sorted(set(SKIPPED))[:5]:
            print("            %s" % p.relative_to(VAULT))

    if not apply_it:
        print("\n  Nothing written. Add --apply to make these changes.\n")
    else:
        print("\n  Done. Run the check again to see the numbers move.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
