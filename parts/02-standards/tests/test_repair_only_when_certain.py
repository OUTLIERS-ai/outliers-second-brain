# -*- coding: utf-8 -*-
"""SHOULD: the repair tool changes a note only where there is one correct answer.

DID (found by testing this, not in use): repairing [[Pricing.md]] to [[Pricing]] in a system where
two notes are called Pricing swapped a link that pointed at nothing for one that silently resolves
to whichever note was found first. That is worse, not better. A broken link announces itself; an
ambiguous one does not.

Run it:  python tests/test_repair_only_when_certain.py
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
    home = Path(tempfile.mkdtemp(prefix="sbrepair-"))
    engine = home / "_engine"
    (engine / "_schema").mkdir(parents=True)
    shutil.copy2(REPO / "sb" / "repair.py", engine / "repair.py")
    shutil.copy2(REPO / "sb" / "_schema" / "note-types.json", engine / "_schema" / "note-types.json")
    for rel, text in files.items():
        p = home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("repair_%d" % id(home), engine / "repair.py")
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    r.VAULT = home
    r.HERE = engine
    r.SCHEMA_PATH = engine / "_schema" / "note-types.json"
    schema = json.loads(r.SCHEMA_PATH.read_text(encoding="utf-8"))
    return home, r, schema


print("")
print("Does the repair tool know when to stop?")
print("")

home, r, schema = build({"Areas/Notes2.md": NOTE % "the only one by this name",
                         "People/Sam.md": NOTE % "see [[Notes2.md]]"})
res = r.fix_links(r.scoped(schema), True)
check("one note by that name: the stray .md is removed", res["count"], 1)
check("nothing is left undecided", len(res["ambiguous"]), 0)
check("the link now resolves",
      "[[Notes2]]" in (home / "People" / "Sam.md").read_text(encoding="utf-8"), True)

home, r, schema = build({"Resources/Pricing.md": NOTE % "x",
                         "Ideas/Pricing.md": NOTE % "y",
                         "People/Sam.md": NOTE % "see [[Pricing.md]]"})
res = r.fix_links(r.scoped(schema), True)
check("two notes by that name: nothing is changed", res["count"], 0)
check("it is reported for a person to decide", len(res["ambiguous"]), 1)
check("the note is left exactly as it was",
      "[[Pricing.md]]" in (home / "People" / "Sam.md").read_text(encoding="utf-8"), True)

home, r, schema = build({"Resources/Book.md": "---\ndate: 2026-01-01\ntype: book\n---\nx\n"})
res = r.fix_kinds(r.scoped(schema), schema, True)
check("a kind with one proper home is rewritten", res["count"], 1)
check("...to the right one",
      "type: resource" in (home / "Resources" / "Book.md").read_text(encoding="utf-8"), True)

home, r, schema = build({"Resources/Odd.md": "---\ndate: 2026-01-01\ntype: invented\n---\nx\n"})
res = r.fix_kinds(r.scoped(schema), schema, True)
check("a kind with no obvious home is left alone", res["count"], 0)

home, r, schema = build({"Ideas/Marked.md": "﻿---\ndate: 2026-01-01\ntype: book\n---\nx\n"})
res = r.fix_kinds(r.scoped(schema), schema, True)
after = (home / "Ideas" / "Marked.md").read_text(encoding="utf-8")
check("a file opening with an invisible marker still gets repaired", res["count"], 1)
check("...and keeps its marker, because removing it would change bytes nobody asked about",
      after.startswith("﻿"), True)

print("")
print("  %d passed, %d failed" % (len(PASS), len(FAIL)))
print("")
sys.exit(1 if FAIL else 0)
