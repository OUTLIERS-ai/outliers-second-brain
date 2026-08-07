# -*- coding: utf-8 -*-
"""
Outliers Second Brain - Layer 3 - Capture

Layers 1 and 2 gave you a sound place to put things and a way to know it is still sound.
Everything in it still arrives because you sat down and typed it. That is where these systems
die: keeping one fed by hand is admin, and admin loses to every other thing in a day.

This layer opens the four ways in - long documents, spoken word, the web, and your own head -
and installs the assistants that read what arrives.

    python install.py

It finds the second brain you built in Layer 1, asks you three questions, and installs into it.

If Layers 1 and 2 are not installed, this refuses and tells you so. Nothing is changed.

Needs: Python 3.8 or newer, and Layers 1 and 2 already installed.
"""

import json
import sys
from datetime import date
from pathlib import Path

LAYER = 3
LAYER_NAME = "Capture"
NEEDS_LAYER = 2
HERE = Path(__file__).resolve().parent
POINTER = Path.home() / ".outliers-sb"

ASSISTANTS = {
    "the-archivist": ("Documents", "Contracts, reports, proposals, anything of length. Turns them "
                                   "into clean notes and flags anything committing you to a future "
                                   "action, so a deadline on page nine does not stay buried."),
    "the-librarian": ("Books and courses", "Captures ideas on the author's own terms, deliberately "
                                           "without bending them to fit what you already believe - "
                                           "because that is how you lose the parts that disagree "
                                           "with you."),
    "the-scribe": ("Anything spoken", "A transcript, rough notes, a recording. Gives back what was "
                                      "decided, what was promised and by whom, what was learned, "
                                      "and who was mentioned."),
    "the-researcher": ("The web", "Research saved with its sources, dated, showing where sources "
                                  "disagree rather than quietly picking one."),
    "the-curator": ("Housekeeping", "Reconciles anything that contradicts itself, merges "
                                    "duplicates, and works from the original note rather than its "
                                    "own previous tidy-up."),
}

CAPTURE_CMD = """---
description: Put something into the second brain without deciding where it goes
---

Take what follows and file it. Work out for yourself which room it belongs in - a person, a
project, a meeting, something read, an idea, a decision - and write it there with the date and
the kind at the top.

Link every person, project and idea mentioned to its own note by name.

If it is a decision, write down the reasoning as well as the decision. The reasoning is the half
that gets reused and the half everybody loses.

If you are unsure which room it belongs in, say which two you were choosing between and why you
picked one. Do not ask first - file it, then say what you did.

$ARGUMENTS
"""

AGENT_TEMPLATE = """---
name: %s
description: %s
tools: Read, Write, Edit, Glob, Grep
---

# %s

## The one job

%s

## Rules

- Every fact you write down says where it came from.
- Never state a figure, date, name or quote you cannot point at a source for. If it is your own
  reading rather than the source's words, say so.
- Write into the rooms this second brain already has. Do not invent new ones.
- Link every person, project and idea you mention to its own note by name.
- Capture on the source's own terms first. Translating it into what it means here is a separate
  pass, and doing both at once produces neither.

## When you are unsure

Say so plainly and leave it out. Something missing is a gap. Something invented is a fault that
everything downstream inherits, and nobody rechecks the bottom of the pile.
"""


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


def main():
    say("", "=" * 66, "  OUTLIERS SECOND BRAIN - LAYER %d - %s" % (LAYER, LAYER_NAME),
        "=" * 66, "")

    home = find_vault()
    if home is None:
        say("I cannot find a second brain to install this into.", "",
            "Install Layer 1 first:",
            "   git clone https://github.com/OUTLIERS-ai/outliers-sb-01-memory",
            "   cd outliers-sb-01-memory", "   python install.py", "",
            "Nothing has been changed.", "")
        return 1

    cfg_path = home / "_layers" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if int(cfg.get("layer", 0)) < NEEDS_LAYER:
        say("Found %s, but Layer %d is not installed there." % (home, NEEDS_LAYER), "",
            "This layer fills your system faster than you can read it, which is exactly why the",
            "check from Layer %d has to be underneath it first." % NEEDS_LAYER, "",
            "   git clone https://github.com/OUTLIERS-ai/outliers-sb-02-standards",
            "   cd outliers-sb-02-standards", "   python install.py", "",
            "Nothing has been changed.", "")
        return 1

    say("Found your second brain: %s" % home, "")
    recorder = ask("What do you record calls with? (or 'nothing yet')", "nothing yet")
    want_assistants = yes("Install the assistants that read what arrives?", True)
    never = ask("Anything it should never read? (folder names, comma separated, blank for none)",
                "")

    say("", "-" * 66, "")

    cmd_dir = home / ".claude" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    (cmd_dir / "capture.md").write_text(CAPTURE_CMD, encoding="utf-8")
    say("Installed /capture - throw anything at it and it decides where it goes.")

    if want_assistants:
        agents = home / ".claude" / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        for name, (channel, job) in ASSISTANTS.items():
            (agents / ("%s.md" % name)).write_text(
                AGENT_TEMPLATE % (name, "%s. %s" % (channel, job.split(".")[0] + "."),
                                  name, job), encoding="utf-8")
        say("Installed %d assistants: %s" % (len(ASSISTANTS), ", ".join(ASSISTANTS)))

    if never.strip():
        schema_path = home / "_engine" / "_schema" / "note-types.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for n in [s.strip() for s in never.split(",") if s.strip()]:
            if n not in schema["scope"]["exclude_path_parts"]:
                schema["scope"]["exclude_path_parts"].append(n)
        schema_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        say("Told the check to leave alone: %s" % never)

    routes = home / "Resources" / "How material gets in.md"
    routes.write_text(
        "---\ndate: %s\ntype: reference\n---\n\n"
        "## For future Claude\n\nThe four ways material reaches this business, and what handles "
        "each. Written by Layer 3 of the Second Brain build.\n\n"
        "| Channel | What goes in | Handled by |\n|---|---|---|\n"
        "| Long documents | Contracts, reports, books, anything of length | the-archivist, "
        "the-librarian |\n"
        "| Spoken word | Client calls, meetings, voice notes (%s) | the-scribe |\n"
        "| The web | Articles, competitor pages, research questions | the-researcher |\n"
        "| Your own head | Decisions and their reasoning, what you charge, what you refuse, "
        "what you changed your mind about | /capture |\n\n"
        "The fourth is the one nobody else can supply, and the one that gets skipped.\n"
        % (date.today().isoformat(), recorder), encoding="utf-8")
    say("Wrote Resources/How material gets in.md")

    cfg["layer"] = max(int(cfg.get("layer", 0)), LAYER)
    cfg["layer_%d_installed" % LAYER] = date.today().isoformat()
    cfg["recorder"] = recorder
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    say("", "-" * 66, "", "This week, the only instruction that matters:", "",
        "   Put more in than feels sensible, and tidy none of it.", "",
        "Organising is the reflex that kills these systems. It feels like progress and produces",
        "nothing. You cannot find a connection in material you have not loaded.", "",
        "When a fair amount is in, ask it:",
        "   what do you now know about my business that I never told you directly?", "")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped. Nothing changed.\n")
        sys.exit(1)
