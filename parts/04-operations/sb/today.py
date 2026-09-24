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
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
SCHEMA = HERE / "_schema" / "note-types.json"
HEALTH = HERE / "reports" / "latest.json"
LEDGER = HERE / "events.jsonl"
CONFIG = VAULT / "_layers" / "config.json"
WRITTEN = HERE / "reports" / "today.txt"
# The morning job's own record, outside the second brain (see morning_job.py).
JOB_LOG = Path.home() / ".outliers-sb-morning.log"
# The command a member types to run Python: "python3" on a Mac, "python" on Windows.
PY = "python3" if sys.platform == "darwin" else "python"

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
        return ["The check has not run yet - %s _engine/doctor.py" % PY]
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


def job_record():
    """What the morning job last did, from its log: (last written, last run, last time Part 4
    added the timetable entry). Each is a tuple (when, status, folder, detail) or None."""
    last_written = last_run = last_installed = None
    try:
        with open(str(JOB_LOG), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                row = (parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else "")
                if row[1] == "installed":
                    last_installed = row
                last_run = row
                if row[1] == "written":
                    last_written = row
    except OSError:
        pass
    return last_written, last_run, last_installed


def parse_stamp(stamp):
    for fmt, n in (("%Y-%m-%dT%H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(str(stamp)[:n], fmt)
        except ValueError:
            pass
    return None


def when_text(stamp):
    try:
        return datetime.strptime(stamp[:16], "%Y-%m-%dT%H:%M").strftime("%A %d %B %Y, %H:%M")
    except ValueError:
        return stamp


def same_folder(a, b):
    try:
        return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))
    except (TypeError, ValueError):
        return False


def job_lines():
    """The morning job's news: a refusal, a failure or a job that has stopped (warnings), then when
    the list was last written. Silent when there is no timetable and no log, as before. A refusal
    of a folder this second brain is no longer in (it was moved) is old news and is not shown."""
    last_written, last_run, last_installed = job_record()
    warn, note = [], []
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    on = bool(cfg.get("morning_list_on_timetable"))
    if last_run and last_run[1] == "refused" and same_folder(last_run[2], VAULT):
        if sys.platform == "darwin":
            new_home = Path.home() / "Second Brain"
            warn.append("macOS refused access to %s on %s, so the morning list was not written."
                        % (last_run[2], when_text(last_run[0])))
            warn.append("Fix: in Finder, drag the folder %s into your home folder (the one with "
                        "your name), so it becomes %s. Then install Part 4 again, the same way "
                        "as the first time. It finds the folder there and points the morning "
                        "list and your AI at it." % (last_run[2], new_home))
        else:
            warn.append("The computer refused access to %s on %s, so the morning list was not "
                        "written. Check the folder is still there and opens. This warning goes "
                        "once a morning run works." % (last_run[2], when_text(last_run[0])))
    elif last_run and last_run[1] == "failed" and same_folder(last_run[2], VAULT):
        warn.append("The morning job failed on %s. Start your AI in your second brain and paste "
                    "it this line: %s" % (when_text(last_run[0]), last_run[3]))
    if on:
        # Counted from the later of: the last list written, and the last time Part 4 added the
        # timetable entry, so installing again (what this warning advises) starts the clock again.
        since, written = None, False
        for row, is_written in ((last_written, True), (last_installed, False)):
            t = parse_stamp(row[0]) if row else None
            if t and (since is None or t > since):
                since, written = t, is_written
        if since is None:
            since = parse_stamp(cfg.get("layer_4_installed", ""))
        if since and datetime.now() - since > timedelta(hours=26):
            warn.append("The morning list has not been written since %s. The timetable may have "
                        "stopped: install Part 4 again to put it back."
                        % (when_text(last_written[0]) if written else
                           "the timetable entry was added on %s" % since.strftime("%A %d %B %Y")))
    if last_written:
        note.append("Morning list last written: %s (in _engine/reports/today.txt)."
                    % when_text(last_written[0]))
    elif on or last_run:
        note.append("Morning list last written: never. The timetable has not written one yet.")
    return warn, note


def lines(for_file=False):
    files = scoped()
    out = ["", "  TODAY  -  %s" % datetime.now().strftime("%A %d %B %Y"), ""]

    job_warn, job_note = ([], []) if for_file else job_lines()
    warns = job_warn + warnings()
    if warns:
        out.append("  Worth knowing")
        for w in warns[:4 + len(job_warn)]:
            out.append("    - %s" % w)
        out.append("")

    changed = recently_changed(files)
    if changed:
        out.append("  Moved in the last few days")
        for m, p in changed[:6]:
            out.append("    - %-11s %s" % (m.strftime("%a %H:%M"), p.relative_to(VAULT)))
        out.append("")

    todo = open_questions(files)
    if todo:
        out.append("  Left unfinished")
        for p, t in todo[:MAX_LINES - len(warns) - min(len(changed), 6)][:5]:
            out.append("    - %-46s %s" % (t[:46], p.name))
        out.append("")

    if not (warns or changed or todo):
        out.append("  Nothing has moved and nothing is owed. That is a real answer, not an "
                   "empty one.")
        out.append("")
    if job_note:
        for n in job_note:
            out.append("  %s" % n)
        out.append("")
    return out


def write_list():
    """The morning job's half: the same list, written to _engine/reports/today.txt through a
    temporary file, so a crash never leaves half a list. Returns where it went."""
    WRITTEN.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(WRITTEN.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines(for_file=True)) + "\n")
        os.replace(tmp, str(WRITTEN))
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return WRITTEN


def main():
    for line in lines():
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
