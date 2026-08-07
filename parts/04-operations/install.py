# -*- coding: utf-8 -*-
"""
Outliers Second Brain - Layer 4 - Operations

You have assistants that can read your material and write into it. They run when you ask, in
whatever order you happen to ask, with nothing standing between them and another person.

This layer adds an order, a gate, a record of what happened, and one list each morning. Then a
check that compares what should be true against what is, because a system left running fails
quietly by default.

    python install.py

Needs: Python 3.8 or newer, and Layers 1 to 3 already installed.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

LAYER = 4
LAYER_NAME = "Operations"
NEEDS_LAYER = 3
HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".outliers-sb"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ask(q, default=""):
    try:
        got = input("  " + q + (" [%s]: " % default if default else ": ")).strip()
    except EOFError:
        got = ""
    return got or default


def yes(q, default=True):
    got = ask("%s (%s)" % (q, "Y/n" if default else "y/N")).lower()
    return default if not got else got.startswith("y")


def say(*lines):
    for ln in lines:
        print("  " + ln if ln else "")


def find_vault():
    if POINTER.exists():
        p = POINTER.read_text(encoding="utf-8").strip()
        if p and (Path(p) / "_layers" / "config.json").exists():
            return Path(p)
    for c in (Path.cwd(), Path.home() / "Documents" / "Second Brain"):
        if (Path(c) / "_layers" / "config.json").exists():
            return Path(c)
    return None


def install_silent_launcher(engine, when, warn_to):
    """A job that opens a window while you are working gets switched off within a week, and a job
    that is off is a job that is not running. So on Windows the timetable points at a launcher that
    runs the work with no window at all, rather than at Python directly."""
    if os.name != "nt":
        return ("This machine is not Windows, so nothing was put on a timetable. To run the "
                "morning list on a clock, add this to your crontab:\n"
                "     0 %s * * * cd %s && python _engine/today.py"
                % (when.split(":")[0], engine.parent))
    vbs = engine / "run-quiet.vbs"
    vbs.write_text(
        'Set sh = CreateObject("WScript.Shell")\n'
        'cmd = """" & WScript.Arguments(0) & """ """ & WScript.Arguments(1) & """"\n'
        'WScript.Quit sh.Run(cmd, 0, True)\n', encoding="utf-8")
    pyw = Path(sys.executable).with_name("pythonw.exe")
    runner = str(pyw if pyw.exists() else sys.executable)
    task = "OutliersSecondBrain-Morning"
    try:
        subprocess.run(
            ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", when, "/TN", task,
             "/TR", 'wscript.exe //B //Nologo "%s" "%s" "%s"'
                    % (vbs, runner, engine / "today.py")],
            capture_output=True, text=True, check=True, creationflags=NO_WINDOW, timeout=60)
        return "The morning list is on a timetable for %s, and runs with no window." % when
    except Exception as exc:
        return ("Could not put it on a timetable (%s). Everything else works - run "
                "'python _engine/today.py' yourself until this is sorted." % exc)


def main():
    say("", "=" * 66, "  OUTLIERS SECOND BRAIN - LAYER %d - %s" % (LAYER, LAYER_NAME),
        "=" * 66, "")

    home = find_vault()
    if home is None:
        say("I cannot find a second brain to install this into.",
            "Install Layer 1 first, then 2 and 3.", "", "Nothing has been changed.", "")
        return 1

    cfg_path = home / "_layers" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if int(cfg.get("layer", 0)) < NEEDS_LAYER:
        say("Found %s, but Layer %d is not installed there." % (home, NEEDS_LAYER), "",
            "This layer arranges things that already work, so there has to be something to",
            "arrange.", "",
            "   git clone https://github.com/OUTLIERS-ai/outliers-sb-03-capture",
            "   cd outliers-sb-03-capture", "   python install.py", "",
            "Nothing has been changed.", "")
        return 1

    say("Found your second brain: %s" % home, "")
    when = ask("When do you want the morning list? (24-hour, e.g. 07:00)", "07:00")
    human_gate = yes("Your hand on anything that reaches a person?", True)
    warn_to = ask("Where should it tell you when something breaks? (a note name)",
                  "Areas/System warnings")

    say("", "-" * 66, "")
    engine = home / "_engine"
    engine.mkdir(exist_ok=True)
    for f in ("today.py", "ledger.py"):
        shutil.copy2(HERE / "sb" / f, engine / f)
    say("Installed the record and the morning list into _engine/")

    gate = home / "Areas" / "The gate.md"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(
        "---\ndate: %s\ntype: reference\n---\n\n## For future Claude\n\n"
        "The rule about anything leaving this system, written by Layer 4 of the Second Brain "
        "build. It governs every assistant here.\n\n"
        "## The rule\n\n%s\n\n"
        "## Why it is here and not in an assistant's instructions\n\n"
        "Instructions are what a busy system stops reading first. A rule that matters is built "
        "into the machinery: the work stops at a queue, and a person moves it.\n\n"
        "## Nothing marks its own homework\n\n"
        "Whatever writes a thing does not get to approve it. A second pass by something else is "
        "the cheapest check there is, and the one most often skipped because the first pass "
        "sounded confident.\n"
        % (date.today().isoformat(),
           "Anything intended for another human being is written, checked by something other than "
           "the thing that wrote it, and then stops. You send it."
           if human_gate else
           "You have chosen to let approved work go out without a final human tap. Whatever "
           "sends is now the last line of defence, and the system's mistakes become other "
           "people's problem. Reverse this by editing this note and telling your AI you have."),
        encoding="utf-8")
    say("Wrote Areas/The gate.md - %s" % ("your hand on everything that leaves."
                                          if human_gate else "no final human tap. Your decision."))

    if "--no-schedule" in sys.argv:
        say("Skipped the timetable because you asked (--no-schedule).",
            "Run 'python _engine/today.py' yourself, or run this installer again without the flag.")
    else:
        say(install_silent_launcher(engine, when, warn_to))

    cfg["layer"] = max(int(cfg.get("layer", 0)), LAYER)
    cfg["layer_%d_installed" % LAYER] = date.today().isoformat()
    cfg["morning_list_at"] = when
    cfg["human_gate"] = bool(human_gate)
    cfg["warnings_go_to"] = warn_to
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    say("", "-" * 66, "", "From now on:", "",
        "   python _engine/today.py       the morning list, on demand",
        "   python _engine/doctor.py      the check from Layer 2",
        "   python _engine/ledger.py      what has happened, most recent first", "")
    say("Your system is now built. What changes from here is that it starts telling you things,",
        "and what it tells you goes back down the ladder: a rule that keeps misfiring gets",
        "rewritten in Layer 2, a source that never produces anything useful gets dropped in",
        "Layer 3.", "")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped. Nothing changed.\n")
        sys.exit(1)
