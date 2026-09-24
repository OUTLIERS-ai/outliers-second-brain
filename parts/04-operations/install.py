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
import plistlib
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

LAYER = 4
LAYER_NAME = "Operations"
NEEDS_LAYER = 3
HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".outliers-sb"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# The command a member types to run Python: "python3" on a Mac, "python" on Windows. Used only in
# lines printed for the member to type; the programs themselves run with sys.executable.
PY = "python3" if sys.platform == "darwin" else "python"

# The Mac copy of each part (its name ends in -mac) prints Mac commands, but it is not published
# yet. Until it is, a Mac member is sent to the same repo as a Windows member, whose code also
# runs on a Mac. The Mac build plan's wave 6 publishes the Mac copies and sets this 1 line to True.
MAC_REPOS_PUBLISHED = False


def repo(name):
    """The name of the repo a member downloads the part `name` from, on this computer."""
    return name + "-mac" if MAC_REPOS_PUBLISHED and sys.platform == "darwin" else name
IS_MAC = sys.platform == "darwin"
TASK = "OutliersSecondBrain-Morning"
MAC_LABEL = "ai.outliers.sb.morning"
MAC_PLIST = Path.home() / "Library" / "LaunchAgents" / (MAC_LABEL + ".plist")
# On a Mac the job runs from outside the second brain, so that if macOS refuses it the second
# brain's folder, the job can still say so in the morning log instead of failing in silence.
MAC_JOB_DIR = Path.home() / "Library" / "Application Support" / "Outliers Second Brain"
# The morning job's log, in the home folder (see sb/morning_job.py).
MORNING_LOG = Path.home() / ".outliers-sb-morning.log"
REMOVE_WIN = "schtasks /Delete /TN %s /F" % TASK
REMOVE_MAC = ["launchctl unload ~/Library/LaunchAgents/%s.plist" % MAC_LABEL,
              "rm ~/Library/LaunchAgents/%s.plist" % MAC_LABEL]


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


def places_to_look():
    """On a Mac a new second brain lives at ~/Second Brain (Part 1 puts it outside Documents), so
    that is looked at first; one made earlier in Documents is still found. Windows is unchanged."""
    places = [Path.cwd()]
    if IS_MAC:
        places.append(Path.home() / "Second Brain")
    places.append(Path.home() / "Documents" / "Second Brain")
    return places


def find_vault():
    if POINTER.exists():
        p = POINTER.read_text(encoding="utf-8").strip()
        if p and (Path(p) / "_layers" / "config.json").exists():
            return Path(p)
    for c in places_to_look():
        if (Path(c) / "_layers" / "config.json").exists():
            return Path(c)
    return None


def install_silent_launcher(engine, when, warn_to):
    """A job that opens a window while you are working gets switched off within a week, and a job
    that is off is a job that is not running. So on Windows the timetable points at a launcher that
    runs the work with no window at all, rather than at Python directly. On a Mac the timetable is
    a LaunchAgent, which never opens a window. Returns (what to tell the member, whether it worked)."""
    if IS_MAC:
        return install_mac_job(when)
    if os.name != "nt":
        return ("Nothing was put on a timetable: this installer knows the Windows and Mac "
                "timetables only. Run '%s _engine/today.py' yourself." % PY, False)
    vbs = engine / "run-quiet.vbs"
    vbs.write_text(
        'Set sh = CreateObject("WScript.Shell")\n'
        'cmd = """" & WScript.Arguments(0) & """ """ & WScript.Arguments(1) & """"\n'
        'WScript.Quit sh.Run(cmd, 0, True)\n', encoding="utf-8")
    pyw = Path(sys.executable).with_name("pythonw.exe")
    runner = str(pyw if pyw.exists() else sys.executable)
    try:
        subprocess.run(
            ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", when, "/TN", TASK,
             "/TR", 'wscript.exe //B //Nologo "%s" "%s" "%s"'
                    % (vbs, runner, engine / "morning_job.py")],
            capture_output=True, text=True, check=True, creationflags=NO_WINDOW, timeout=60)
        return ("The morning list is on a timetable for %s, and runs with no window.\n"
                "  To take it off the timetable later, type:  %s" % (when, REMOVE_WIN), True)
    except Exception as exc:
        return ("Could not put it on a timetable (%s). Everything else works - run "
                "'%s _engine/today.py' yourself until this is sorted." % (exc, PY), False)


def install_mac_job(when):
    """The Mac timetable: a LaunchAgent that runs the morning job at the same time each day.
    Written the way outliers-gather-05-timetable writes its own, then loaded straight away so it
    runs tomorrow without waiting for you to log out and in."""
    try:
        hour, minute = [int(x) for x in when.split(":")[:2]]
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(when)
    except ValueError:
        return ("'%s' is not a time like 07:00, so nothing was put on a timetable. Run this "
                "installer again with a time like 07:00." % when, False)
    try:
        MAC_JOB_DIR.mkdir(parents=True, exist_ok=True)
        job = MAC_JOB_DIR / "morning_job.py"
        tmp = job.with_name(job.name + ".tmp")
        shutil.copy2(str(HERE / "sb" / "morning_job.py"), str(tmp))
        os.replace(str(tmp), str(job))
        plan = {
            "Label": MAC_LABEL,
            "ProgramArguments": [sys.executable, str(job)],
            "StartCalendarInterval": {"Hour": hour, "Minute": minute},
            # Home, not the second brain: a job refused its folder must still be able to start.
            "WorkingDirectory": str(Path.home()),
            "StandardOutPath": str(MAC_JOB_DIR / "morning-job-output.log"),
            "StandardErrorPath": str(MAC_JOB_DIR / "morning-job-output.log"),
        }
        MAC_PLIST.parent.mkdir(parents=True, exist_ok=True)
        tmp = MAC_PLIST.with_name(MAC_PLIST.name + ".tmp")
        with open(str(tmp), "wb") as fh:
            plistlib.dump(plan, fh)
        os.replace(str(tmp), str(MAC_PLIST))
    except OSError as exc:
        return ("Could not write the timetable entry (%s). Everything else works - run "
                "'%s _engine/today.py' yourself until this is sorted." % (exc, PY), False)
    try:
        subprocess.run(["launchctl", "unload", str(MAC_PLIST)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        done = subprocess.run(["launchctl", "load", "-w", str(MAC_PLIST)],
                              capture_output=True, text=True, timeout=60)
        # launchctl load can print an error and still end with 0, so ask launchd directly.
        listed = subprocess.run(["launchctl", "list", MAC_LABEL],
                                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return ("The timetable entry was written but macOS did not answer (%s). Everything else "
                "works - run '%s _engine/today.py' yourself until this is sorted." % (exc, PY),
                False)
    if done.returncode != 0 or listed.returncode != 0:
        return ("The timetable entry was written but macOS did not accept it (%s). Everything "
                "else works - run '%s _engine/today.py' yourself until this is sorted."
                % ((done.stderr or done.stdout or listed.stderr).strip()[:200]
                   or "no reason given", PY), False)
    return ("The morning list is on a timetable for %s, and runs with no window.\n"
            "  To take it off the timetable later, type:\n     %s"
            % (when, "\n     ".join(REMOVE_MAC)), True)


def entry_already_there():
    """Whether an earlier install left the morning list on this computer's timetable."""
    if IS_MAC:
        return MAC_PLIST.exists()
    if os.name != "nt":
        return False
    try:
        return subprocess.run(["schtasks", "/Query", "/TN", TASK], capture_output=True,
                              creationflags=NO_WINDOW, timeout=60).returncode == 0
    except Exception:
        return False


def log_installed(home):
    """A line in the morning log saying a timetable entry was just added, so an old refusal or
    failure is no longer reported as the latest news."""
    try:
        with open(str(MORNING_LOG), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\t".join([datetime.now().isoformat(timespec="minutes"), "installed",
                                str(home), "timetable entry added by Part 4"]) + "\n")
    except OSError:
        pass


def point_at(home):
    """On a Mac: if the second brain was found somewhere other than where Layer 1 recorded it (it
    was moved out of Documents), record the new address and change the line in ~/.claude/CLAUDE.md
    that tells your AI where it is. Returns a sentence for the member, or "" if nothing changed.
    Windows is unchanged: nothing here runs there."""
    if not IS_MAC:
        return ""
    try:
        old = POINTER.read_text(encoding="utf-8").strip() if POINTER.is_file() else ""
    except (OSError, UnicodeError):
        old = ""
    if old and Path(old) == home:
        return ""
    try:
        tmp = POINTER.with_name(POINTER.name + ".tmp")
        tmp.write_text(str(home), encoding="utf-8")
        os.replace(str(tmp), str(POINTER))
    except OSError as exc:
        return "Could not record the second brain's new address in %s (%s)." % (POINTER, exc)
    manual = Path.home() / ".claude" / "CLAUDE.md"
    begin, end = "<!-- OUTLIERS-SECOND-BRAIN:BEGIN -->", "<!-- OUTLIERS-SECOND-BRAIN:END -->"
    told = False
    try:
        with open(str(manual), encoding="utf-8", newline="") as fh:
            text = fh.read()
        if begin in text and end in text:
            i, j = text.index(begin), text.index(end) + len(end)
            section = text[i:j]
            m = re.search(r"My second brain is at: (.+?)\r?\n", section)
            was = m.group(1) if m else old
            if was and was != str(home):
                text = text[:i] + section.replace(was, str(home)) + text[j:]
                tmp = manual.with_name(manual.name + ".tmp")
                with open(str(tmp), "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
                os.replace(str(tmp), str(manual))
                told = True
    except (OSError, UnicodeError):
        pass
    if told:
        return ("Your second brain is at a new address. Recorded it, and changed the line in "
                "~/.claude/CLAUDE.md that tells your AI where it is.")
    return ("Your second brain is at a new address, and it is recorded. The line in "
            "~/.claude/CLAUDE.md that tells your AI where it is was not changed: run Part 1 "
            "again and give it %s, or edit that line yourself." % home)


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
            "   git clone https://github.com/OUTLIERS-ai/%s" % repo("outliers-sb-03-capture"),
            "   cd %s" % repo("outliers-sb-03-capture"), "   %s install.py" % PY, "",
            "Nothing has been changed.", "")
        return 1

    say("Found your second brain: %s" % home, "")
    when = ask("When do you want the morning list? (24-hour, e.g. 07:00)", "07:00")
    human_gate = yes("Your hand on anything that reaches a person?", True)
    warn_to = ask("Where should it tell you when something breaks? (a note name)",
                  "Areas/System warnings")
    no_schedule = "--no-schedule" in sys.argv
    schedule = False
    if not no_schedule:
        schedule = yes("Put the morning list on this computer's timetable, so it runs by itself "
                       "at %s each day?" % when, True)

    say("", "-" * 66, "")
    engine = home / "_engine"
    engine.mkdir(exist_ok=True)
    for f in ("today.py", "ledger.py", "morning_job.py"):
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

    moved = point_at(home)
    if moved:
        say(moved)

    on_timetable = False
    if no_schedule:
        say("Skipped the timetable because you asked (--no-schedule).",
            "Run '%s _engine/today.py' yourself, or run this installer again without the flag."
            % PY)
    elif not schedule:
        say("Nothing was put on a timetable, because you said no.",
            "Run '%s _engine/today.py' yourself, or run this installer again and answer yes."
            % PY)
    else:
        told, on_timetable = install_silent_launcher(engine, when, warn_to)
        say(told)
        if on_timetable:
            log_installed(home)
    if not schedule and entry_already_there():
        say("An earlier install put the morning list on this computer's timetable, and it is "
            "still there. To take it off, type:")
        for line in (REMOVE_MAC if IS_MAC else [REMOVE_WIN]):
            say("   " + line)

    cfg["layer"] = max(int(cfg.get("layer", 0)), LAYER)
    cfg["layer_%d_installed" % LAYER] = date.today().isoformat()
    cfg["morning_list_at"] = when
    cfg["human_gate"] = bool(human_gate)
    cfg["warnings_go_to"] = warn_to
    cfg["morning_list_on_timetable"] = bool(on_timetable)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    say("", "-" * 66, "", "From now on:", "",
        "   %-30sthe morning list, on demand" % (PY + " _engine/today.py"),
        "   %-30sthe check from Layer 2" % (PY + " _engine/doctor.py"),
        "   %-30swhat has happened, most recent first" % (PY + " _engine/ledger.py"), "")
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
