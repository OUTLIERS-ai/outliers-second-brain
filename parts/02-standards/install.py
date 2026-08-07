# -*- coding: utf-8 -*-
"""
Outliers Second Brain - Layer 2 - Standards

Layer 1 gave you somewhere to put things. A folder accepts anything, and the rules you wrote
in ordinary sentences are advice - nothing reads them and refuses a note for breaking them.

This layer writes your rules down as data a program can check, and installs the check.

    python install.py

It finds the second brain you built in Layer 1, asks you three questions, and installs itself
into that folder. Then it runs the check once so you can see where you are starting from.

If Layer 1 is not installed, this refuses and tells you so. Nothing is changed.

Needs: Python 3.8 or newer, and Layer 1 already installed.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

LAYER = 2
LAYER_NAME = "Standards"
NEEDS_LAYER = 1
HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".outliers-sb"


def ask(question, default=""):
    suffix = " [%s]: " % default if default else ": "
    try:
        got = input("  " + question + suffix).strip()
    except EOFError:
        got = ""
    return got or default


def yes(question, default=True):
    got = ask("%s (%s)" % (question, "Y/n" if default else "y/N")).lower()
    return default if not got else got.startswith("y")


def say(*lines):
    for ln in lines:
        print("  " + ln if ln else "")


def looks_installed(p):
    return (Path(p) / "_layers" / "config.json").exists()


def find_vault():
    """Look where Layer 1 said it put things, then in the obvious places."""
    if POINTER.exists():
        p = POINTER.read_text(encoding="utf-8").strip()
        if p and looks_installed(p):
            return Path(p)
    for c in (Path.cwd(), Path.home() / "Documents" / "Second Brain"):
        if looks_installed(c):
            return Path(c)
    return None


def main():
    say("", "=" * 66, "  OUTLIERS SECOND BRAIN - LAYER %d - %s" % (LAYER, LAYER_NAME),
        "=" * 66, "")

    home = find_vault()
    if home is None:
        say("I cannot find a second brain to install this into.", "",
            "This layer sits on top of Layer %d. Install that first:" % NEEDS_LAYER,
            "   git clone https://github.com/OUTLIERS-ai/outliers-sb-01-memory",
            "   cd outliers-sb-01-memory",
            "   python install.py", "", "Nothing has been changed.", "")
        return 1

    cfg_path = home / "_layers" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if int(cfg.get("layer", 0)) < NEEDS_LAYER:
        say("Found %s, but Layer %d is not finished there." % (home, NEEDS_LAYER),
            "Nothing has been changed.", "")
        return 1

    say("Found your second brain: %s" % home, "")

    tops = sorted(d.name for d in home.iterdir()
                  if d.is_dir() and not d.name.startswith((".", "_")))
    say("Top-level folders here: %s" % (", ".join(tops) if tops else "none yet"), "")
    skip = ask("Which of those hold things that are NOT notes? (comma separated, blank for none)",
               "Archive")
    from_here = yes("Start from what you have, rather than from zero?", True)
    run_alone = yes("Let the check run on its own, rather than only when asked?", True)

    say("", "-" * 66, "")
    engine = home / "_engine"
    engine.mkdir(exist_ok=True)
    (engine / "_schema").mkdir(exist_ok=True)

    schema = json.loads((HERE / "sb" / "_schema" / "note-types.json").read_text(encoding="utf-8"))
    excl = schema["scope"]["exclude_path_parts"]
    for name in [s.strip() for s in skip.split(",") if s.strip()]:
        if name not in excl:
            excl.append(name)
    (engine / "_schema" / "note-types.json").write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    say("Wrote your rules: _engine/_schema/note-types.json  (yours to edit)")

    for f in ("doctor.py", "repair.py"):
        shutil.copy2(HERE / "sb" / f, engine / f)
    say("Installed the check and the repair tool into _engine/")

    if not from_here:
        say("Starting from zero: every count has to reach zero to be clean.")
    say("", "-" * 66, "", "Running the check for the first time.", "")

    sys.stdout.flush()   # the check writes straight to the screen; without this our
                         # own buffered lines arrive after it when output is piped
    r = subprocess.run([sys.executable, str(engine / "doctor.py")] +
                       (["--set-ceiling"] if from_here else []),
                       cwd=str(home))

    cfg["layer"] = max(int(cfg.get("layer", 0)), LAYER)
    cfg["layer_%d_installed" % LAYER] = date.today().isoformat()
    cfg["check_runs_on_its_own"] = bool(run_alone)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    say("-" * 66, "")
    say("From now on:", "",
        "   python _engine/doctor.py      see what changed",
        "   python _engine/repair.py      show what could be fixed automatically",
        "   python _engine/repair.py --apply    fix it", "")
    if run_alone:
        say("You said the check should run on its own. It has no timetable of its own yet -",
            "that arrives in Layer 4, which is where things start running to a clock.", "")
    say("Nothing in your notes was changed by installing this.", "")
    return r.returncode if r.returncode in (0, 1) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped. Nothing changed.\n")
        sys.exit(1)
