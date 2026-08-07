# -*- coding: utf-8 -*-
"""today.py - one short list each morning, ordered by what changed.

Not everything you could do. What has moved since you last looked, plus anything the system wants
to tell you. Each line says why it is there, because a list you cannot argue with is a list you
stop reading.

    python today.py

It is deliberately short. A morning list of forty things is a list of nothing.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
SCHEMA = HERE / "_schema" / "note-types.json"
HEALTH = HERE / "reports" / "latest.json"
LEDGER = HERE / "events.jsonl"
CONFIG = VAULT / "_layers" / "config.json"

MAX_LINES = 12


def scoped():
    # .claude holds instructions to your AI, not notes. Listing it as "moved" every
    # time a layer installs something buries the two lines that actually matter.
    excl = {".git", ".obsidian", ".claude", "node_modules", "__pycache__",
            "_engine", "_layers"}
    excl_files = set()
    files = []
    if SCHEMA.exists():
        try:
            s = json.loads(SCHEMA.read_text(encoding="utf-8"))
            excl |= set(s.get("scope", {}).get("exclude_path_parts", []))
            excl_files |= set(s.get("scope", {}).get("exclude_files", []))
        except Exception:
            pass
    for p in VAULT.rglob("*.md"):
        if not (set(p.parts) & excl) and p.name not in excl_files:
            files.append(p)
    return files


def recently_changed(files, days=3):
    cut = datetime.now() - timedelta(days=days)
    out = []
    for p in files:
        try:
            m = datetime.fromtimestamp(p.stat().st_mtime)
        except OSError:
            continue
        if m > cut:
            out.append((m, p))
    out.sort(key=lambda x: -x[0].timestamp())
    return out


def warnings():
    """What the check said last time it ran. A warning nobody surfaces is not a warning."""
    if not HEALTH.exists():
        return ["The check has not run yet - python _engine/doctor.py"]
    try:
        d = json.loads(HEALTH.read_text(encoding="utf-8"))
    except Exception:
        return ["The check's last report cannot be read."]
    out = []
    for c in d.get("checks", []):
        if c.get("status") == "WORSE":
            out.append("%s went up to %s - it was %s" % (c["id"], c["did"], c.get("ceiling")))
    stamp = d.get("run", "")
    if stamp and stamp != datetime.now().strftime("%Y-%m-%d"):
        out.append("The check last ran on %s, not today." % stamp)
    return out


def open_questions(files):
    """Anything you left with a question mark against it. Cheap to find, easy to lose."""
    out = []
    pat = re.compile(r"^\s*[-*]\s*\[ \]\s*(.+)$", re.M)
    for p in files:
        try:
            s = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in pat.finditer(s):
            out.append((p, m.group(1).strip()))
            if len(out) > 40:
                return out
    return out


def main():
    files = scoped()
    print("")
    print("  TODAY  -  %s" % datetime.now().strftime("%A %d %B %Y"))
    print("")

    warns = warnings()
    if warns:
        print("  Worth knowing")
        for w in warns[:4]:
            print("    - %s" % w)
        print("")

    changed = recently_changed(files)
    if changed:
        print("  Moved in the last few days")
        for m, p in changed[:6]:
            print("    - %-11s %s" % (m.strftime("%a %H:%M"), p.relative_to(VAULT)))
        print("")

    todo = open_questions(files)
    if todo:
        print("  Left unfinished")
        for p, t in todo[:MAX_LINES - len(warns) - min(len(changed), 6)][:5]:
            print("    - %-46s %s" % (t[:46], p.name))
        print("")

    if not (warns or changed or todo):
        print("  Nothing has moved and nothing is owed. That is a real answer, not an empty one.")
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
