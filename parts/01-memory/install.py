# -*- coding: utf-8 -*-
"""
Outliers Second Brain - Layer 1 - Memory

You explain your business to an AI, it understands, you close the window, and all of it is
gone. This layer gives it somewhere to write things down that is still there tomorrow.

    python install.py

It asks you three questions, makes the folder, writes the rulebook your AI reads before it
does anything, and points your AI at it so it can be found from anywhere.

Nothing here costs money and nothing leaves your computer. No account, no sign-up.

Needs: Python 3.8 or newer. Nothing beneath it - this is the bottom of the ladder.
"""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

LAYER = 1
LAYER_NAME = "Memory"
HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".outliers-sb"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

ROOMS = {
    "People": "One note per human being you deal with.",
    "Projects": "Things with an outcome and an end.",
    "Areas": "Things that are ongoing and have no end.",
    "Meetings": "What happened when people spoke.",
    "Resources": "Things you read or watched, kept on their author's terms.",
    "Ideas": "Unformed things you did not want to lose.",
    "Decisions": "A decision and the reasoning behind it. The reasoning is the reusable half.",
    "Archive": "Things that are finished. Nothing is ever deleted; it comes here.",
}


def ask(question, default=""):
    suffix = " [%s]: " % default if default else ": "
    try:
        got = input("  " + question + suffix).strip()
    except EOFError:
        got = ""
    return got or default


def yes(question, default=True):
    d = "Y/n" if default else "y/N"
    got = ask("%s (%s)" % (question, d)).lower()
    if not got:
        return default
    return got.startswith("y")


def say(*lines):
    for ln in lines:
        print("  " + ln if ln else "")


def rulebook(business):
    return """# How to work in this second brain

This file is read before anything else happens here. Edit it when something is wrong, and the
whole system changes at once instead of you repeating yourself.

## What this is

%s

## The rooms

%s

## Rules

- Every note says what kind of thing it is and when it was written, at the top.
- Link people, projects and ideas to each other by name whenever they are mentioned.
- Write down decisions AND the reasoning behind them. The reasoning is the half that gets reused.
- Nothing is deleted. Finished things go to Archive.
- If a fact came from somewhere, say where it came from.

## When something is wrong

Change this file. Do not repeat the correction in every conversation.
""" % (business, "\n".join("- **%s/** - %s" % (k, v) for k, v in ROOMS.items()))


def main():
    say("", "=" * 66, "  OUTLIERS SECOND BRAIN - LAYER %d - %s" % (LAYER, LAYER_NAME),
        "=" * 66, "")
    say("Three questions, then it builds.", "")

    default_home = str(Path.home() / "Documents" / "Second Brain")
    where = ask("Where should it live?", default_home)
    home = Path(os.path.expanduser(where)).resolve()

    if home.exists() and any(home.iterdir()):
        say("", "There are already files in %s." % home)
        if not yes("Add the second brain alongside them? Nothing is deleted", True):
            say("Stopped. Nothing changed.", "")
            return 1

    business = ask("What is your business, in a sentence?",
                   "A one-person business.")
    keep_copies = yes("Keep a copy of every change, so nothing can be lost?", True)

    say("", "-" * 66, "")
    home.mkdir(parents=True, exist_ok=True)
    for room, purpose in ROOMS.items():
        d = home / room
        d.mkdir(exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
    say("Made the rooms: %s" % ", ".join(ROOMS))

    manual = home / "CLAUDE.md"
    if manual.exists():
        say("Left your existing CLAUDE.md alone.")
    else:
        manual.write_text(rulebook(business), encoding="utf-8")
        say("Wrote the rulebook: CLAUDE.md")

    gitignore = home / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Never keep secrets in your history. Once one is in, it stays in.\n"
            "*.key\n*.pem\n*.crt\n*.env\n.env\nsecrets/\ncredentials/\n\n"
            "# Machine clutter\n.obsidian/workspace.json\n__pycache__/\n.DS_Store\nThumbs.db\n",
            encoding="utf-8")
        say("Wrote .gitignore, which refuses to keep passwords and keys.")

    if keep_copies:
        if (home / ".git").exists():
            say("Copies already being kept here.")
        else:
            try:
                subprocess.run(["git", "init", "-q"], cwd=str(home), check=True,
                               creationflags=NO_WINDOW, timeout=60)
                # A machine where git has just been installed has no name or email set, and the
                # first commit fails with "Author identity unknown". Almost everybody installing
                # this is in exactly that position, so set a name for THIS folder only. Their
                # own settings elsewhere are not touched.
                who = subprocess.run(["git", "config", "user.email"], cwd=str(home),
                                     capture_output=True, text=True,
                                     creationflags=NO_WINDOW, timeout=30)
                if not who.stdout.strip():
                    subprocess.run(["git", "config", "user.name", "Second Brain"], cwd=str(home),
                                   check=True, creationflags=NO_WINDOW, timeout=30)
                    subprocess.run(["git", "config", "user.email",
                                    "second-brain@localhost"], cwd=str(home),
                                   check=True, creationflags=NO_WINDOW, timeout=30)
                    say("Git had no name set on this machine, so I set one for this folder only.")
                subprocess.run(["git", "add", "-A"], cwd=str(home), check=True,
                               creationflags=NO_WINDOW, timeout=120)
                subprocess.run(["git", "commit", "-qm", "Second brain, layer 1"], cwd=str(home),
                               check=True, creationflags=NO_WINDOW, timeout=120)
                say("Copies are being kept. Every change from now on can be undone.")
            except FileNotFoundError:
                say("Git is not installed, so copies are not being kept.",
                    "Everything else worked. Install git from git-scm.com and run this again.")
            except Exception as exc:
                say("Everything else worked, but copies could not be started:",
                    "   %s" % exc,
                    "Tell your AI what it said and it will sort it out.")

    layers = home / "_layers"
    layers.mkdir(exist_ok=True)
    (layers / "config.json").write_text(json.dumps({
        "series": "outliers-second-brain",
        "layer": LAYER,
        "business": business,
        "layer_1_installed": date.today().isoformat(),
    }, indent=2) + "\n", encoding="utf-8")
    POINTER.write_text(str(home), encoding="utf-8")

    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(exist_ok=True)
    global_manual = claude_dir / "CLAUDE.md"
    block = ("<!-- OUTLIERS-SECOND-BRAIN:BEGIN -->\n"
             "## My second brain\n"
             "My second brain is at: %s\n"
             "When I ask about my notes, people, projects, meetings or decisions, that folder is\n"
             "the source of truth. Read %s/CLAUDE.md before acting in it.\n"
             "<!-- OUTLIERS-SECOND-BRAIN:END -->\n" % (home, home))
    existing = global_manual.read_text(encoding="utf-8") if global_manual.exists() else ""
    if "OUTLIERS-SECOND-BRAIN:BEGIN" in existing:
        start = existing.index("<!-- OUTLIERS-SECOND-BRAIN:BEGIN -->")
        end = existing.index("<!-- OUTLIERS-SECOND-BRAIN:END -->") + len(
            "<!-- OUTLIERS-SECOND-BRAIN:END -->\n")
        existing = existing[:start] + block + existing[end:]
    else:
        existing = (existing + "\n" if existing else "") + block
    global_manual.write_text(existing, encoding="utf-8")
    say("Pointed your AI at it. You can now ask from anywhere, not only inside the folder.")

    say("", "-" * 66, "", "Done. Your second brain is at:", "   %s" % home, "",
        "Try this next:", "   Open your AI there and tell it something that happened today.",
        "   Then ask it something only your notes would know.", "",
        "It is empty, and that is correct. An empty room you own beats a full one you rent.", "")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped. Nothing changed.\n")
        sys.exit(1)
