# -*- coding: utf-8 -*-
"""SHOULD: the check reports a fault only where one exists.

DID (before these tests existed): on a real system of about 4,900 notes it reported six kinds of
fault that were not faults, and every one of them pointed the same way - it said a healthy system
was broken. A check that cries wolf gets switched off, and then nothing is being checked at all.
Each of the six is pinned here so it cannot come back.

Run it:  python tests/test_check_does_not_cry_wolf.py
No test framework needed. It prints what it checked and exits 1 if anything failed.
"""

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PASS, FAIL = [], []


def check(name, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(name)
    print("  %-58s %s" % (name, "ok" if ok else "FAILED  got %r want %r" % (got, want)))


NOTE = "---\ndate: 2026-01-01\ntype: note\n---\n%s\n"


def build(files):
    """A throwaway second brain with the layer-2 check installed into it."""
    home = Path(tempfile.mkdtemp(prefix="sbcheck-"))
    engine = home / "_engine"
    (engine / "_schema").mkdir(parents=True)
    shutil.copy2(REPO / "sb" / "doctor.py", engine / "doctor.py")
    shutil.copy2(REPO / "sb" / "_schema" / "note-types.json", engine / "_schema" / "note-types.json")
    for rel, text in files.items():
        p = home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return home, engine


def counts(home, engine):
    spec = importlib.util.spec_from_file_location("doctor_%d" % id(home), engine / "doctor.py")
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    d.VAULT = home
    d.HERE = engine
    d.SCHEMA_PATH = engine / "_schema" / "note-types.json"
    schema = json.loads(d.SCHEMA_PATH.read_text(encoding="utf-8"))
    scan = d.Scan(schema)
    checks, links, names = d.build_checks(scan, schema)
    return dict((c["id"], c["did"]) for c in checks)


print("")
print("Does the check invent faults that are not there?")
print("")

# WHY 1 - a file may open with an invisible marker before its first line
c = counts(*build({"Ideas/Marked.md": "﻿" + NOTE % "has frontmatter, behind a marker"}))
check("a note opening with an invisible marker is not 'missing frontmatter'",
      c["frontmatter-present"], 0)

# WHY 2 - a filename may contain a square bracket
c = counts(*build({
    "Meetings/[2026-06-03] Session 3.md": NOTE % "the meeting",
    "People/Sam.md": NOTE % "spoke at [[[2026-06-03] Session 3]] about it",
}))
check("a link to a note whose name contains a bracket resolves", c["links-resolve"], 0)

# WHY 4 - a stray .md is its own category, not a missing note
c = counts(*build({
    "Resources/Pricing.md": NOTE % "x",
    "People/Sam.md": NOTE % "see [[Pricing.md]]",
}))
check("a link with a stray .md is not counted as a missing note", c["links-resolve"], 0)
check("...it is counted as a typo instead", c["link-typos"], 1)

# WHY 5 - naming the folder removes the ambiguity
c = counts(*build({
    "Resources/Pricing.md": NOTE % "x",
    "Ideas/Pricing.md": NOTE % "y",
    "People/Sam.md": NOTE % "see [[Resources/Pricing]]",
}))
check("a link that names the folder is not ambiguous", c["bare-ambiguous-links"], 0)

# WHY 6 - a deliberate pair references itself across
c = counts(*build({
    "Resources/Jung.md": NOTE % "the full thing",
    "Areas/Jung.md": NOTE % "a short index record. Full note: [[Resources/Jung]]",
}))
check("two notes that reference each other are a pair, not a duplicate", c["duplicate-pairs"], 0)
check("...though still reported as a name used twice", c["names-used-twice"], 1)

# the machinery beside your notes is not a note
c = counts(*build({"CLAUDE.md": "# the rulebook, deliberately without frontmatter"}))
check("the rulebook is not counted as a note", c["frontmatter-present"], 0)

print("")
print("Does it still catch a real fault?")
print("")

c = counts(*build({
    "Ideas/Empty.md": "",
    "Areas/Loose.md": "no frontmatter here",
    "People/Sam.md": NOTE % "see [[Never Written]]",
}))
check("an empty note is caught", c["empty-notes"], 1)
check("a note with no frontmatter is caught", c["frontmatter-present"], 2)
check("a link to a note that was never written is caught", c["links-resolve"], 1)

print("")
print("  %d passed, %d failed" % (len(PASS), len(FAIL)))
print("")
sys.exit(1 if FAIL else 0)
