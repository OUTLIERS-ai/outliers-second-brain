# -*- coding: utf-8 -*-
"""morning_job.py - what the timetable runs each morning.

It writes the morning list to _engine/reports/today.txt in your second brain, then adds one line
to the morning log, ~/.outliers-sb-morning.log, saying what happened. The log lives in your home
folder, outside the second brain, on purpose: if the computer ever refuses this job access to the
second brain's folder, the log is still written, and today.py tells you the next time you run it.

A job that fails with nobody watching looks exactly like a job that had nothing to do. This is the
difference.
"""

import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path

POINTER = Path.home() / ".outliers-sb"
LOG = Path.home() / ".outliers-sb-morning.log"


def log(status, folder, detail=""):
    """One line per run, added to the end, never rewritten: when, what happened, which folder."""
    line = "\t".join([datetime.now().isoformat(timespec="minutes"), status, str(folder),
                      " ".join(str(detail).split())])
    with open(str(LOG), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def main():
    try:
        vault = Path(POINTER.read_text(encoding="utf-8").strip())
    except OSError as exc:
        log("failed", POINTER, "cannot read where the second brain is: %s" % exc)
        return 1
    engine = vault / "_engine"
    try:
        # Touch the folder first. If the computer refuses this job the folder, this is where it
        # shows: macOS says "Operation not permitted".
        os.listdir(str(engine))
        spec = importlib.util.spec_from_file_location("sb_today", str(engine / "today.py"))
        today = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(today)
        written = today.write_list()
    except PermissionError as exc:
        log("refused", vault, exc)
        return 1
    except Exception as exc:
        log("failed", vault, "%s: %s" % (type(exc).__name__, exc))
        return 1
    log("written", vault, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
