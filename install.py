# -*- coding: utf-8 -*-
"""
The Outliers Second Brain - all four parts, one command.

    python install.py

It runs the four parts in order, handing each one the second brain the last one built. Every
part still checks for the one before it, so if anything goes wrong it stops there rather than
building something that half works.

If you would rather take them one at a time, each part is its own folder in here and its own
installer. Nothing is lost by doing it that way; it is the same code.

Nothing here costs money and nothing leaves your computer.

Needs: Python 3.8 or newer. Git, if you want a copy of every change kept.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYERS = [
    (1, "parts/01-memory", "Memory", "somewhere to put things that is still there tomorrow"),
    (2, "parts/02-standards", "Standards", "rules a program can check, and the check"),
    (3, "parts/03-capture", "Capture", "four ways in, so you are not typing it all"),
    (4, "parts/04-operations", "Operations", "an order, a gate, and one list each morning"),
]


def main():
    print("")
    print("  " + "=" * 64)
    print("  THE OUTLIERS SECOND BRAIN")
    print("  " + "=" * 64)
    print("")
    print("  Four parts, in order. Each one asks you a few questions.")
    print("  If any part stops, fix what it says and run this again - it is safe to")
    print("  run twice, and finished parts are left alone.")
    print("")

    for n, folder, name, what in LAYERS:
        print("")
        print("  ---- Part %d of 4: %s - %s" % (n, name, what))
        print("")
        sys.stdout.flush()   # the part writes straight to the screen; without this our own
                             # buffered lines arrive after it when output is piped or logged
        r = subprocess.run([sys.executable, "install.py"] + sys.argv[1:],
                           cwd=str(HERE / folder))
        if r.returncode not in (0, 1):
            print("")
            print("  Part %d stopped. Nothing after it has been run." % n)
            return r.returncode
        if r.returncode == 1:
            print("")
            print("  Part %d did not complete. Read what it said above, then run this again."
                  % n)
            return 1

    print("")
    print("  " + "-" * 64)
    print("  All four parts are in. Your second brain is built.")
    print("")
    print("  Read guide/The-Outliers-Second-Brain.pdf if you have not already.")
    print("")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped.\n")
        sys.exit(1)
