# -*- coding: utf-8 -*-
"""ledger.py - the record of what happened, as opposed to how things are.

Your notes describe how things are. They are rewritten as things change, which is correct, and it
means they cannot answer 'what changed this week' or 'did that job actually run'.

This is the other half. One line per event, added and never rewritten, so what it said last month
still says the same thing today.

    python ledger.py                     the last 20 things that happened
    python ledger.py add "what happened" write one down
    python ledger.py add "x" --kind run  say what kind of thing it was

Every line carries when it happened and where it came from. A record with no provenance is a
rumour with a timestamp on it.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
LEDGER = VAULT / "_engine" / "events.jsonl"


def add(what, kind="note", source="hand"):
    """Append only. Never opens the file for writing in a way that could truncate it - a crash
    halfway through a rewrite would take the whole history with it."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.now().isoformat(timespec="seconds"),
           "kind": kind, "what": what, "source": source}
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read(limit=20):
    if not LEDGER.exists():
        return []
    rows = []
    with open(LEDGER, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                # A damaged line is skipped and counted, never silently dropped and never
                # "repaired" - rewriting history to make it tidy is how history stops being true.
                rows.append({"at": "?", "kind": "unreadable", "what": line[:60], "source": "?"})
    return rows[-limit:]


def main(argv):
    if argv and argv[0] == "add":
        what = argv[1] if len(argv) > 1 else ""
        if not what:
            print("  Nothing to write down. Try: python ledger.py add \"what happened\"")
            return 1
        kind = "note"
        if "--kind" in argv:
            i = argv.index("--kind")
            if i + 1 < len(argv):
                kind = argv[i + 1]
        row = add(what, kind=kind)
        print("  written: %s  %s" % (row["at"], row["what"]))
        return 0

    rows = read(20)
    if not rows:
        print("\n  Nothing has been written down yet.")
        print("  Try: python ledger.py add \"finished the pricing page\"\n")
        return 0
    print("\n  WHAT HAS HAPPENED  (most recent last)\n")
    for r in rows:
        print("  %-19s  %-10s %s" % (r.get("at", "?")[:19], r.get("kind", ""), r.get("what", "")))
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
