# What I stole

| Taken from | What was taken |
|---|---|
| JSON Schema | Writing the shape of a record down as data rather than prose, so a program can check it instead of a person having to remember it. |
| Linters generally (ESLint, ruff, and their ancestors) | Report, do not repair. Anything a tool fixes by guessing is a defect it introduced. |
| Ratchets in test suites | A number may fall and may not rise. It converts "we should tidy this up one day" into something that holds without anybody tidying anything. |
| Obsidian's own link resolution | Links resolve by name, which is exactly why a name is an identity and two notes sharing one is a fault. |

## What was learned the hard way, not stolen

Six of the rules inside `doctor.py` exist because the naive version got them wrong on a real
system of nearly five thousand notes, and each time the error was in the same direction: it said a
healthy system was broken.

An invisible marker at the start of a file made 290 good notes look faulty. Reading a link up to
the first `]` instead of the first `]]` called hundreds of working links broken. Links to things
that live outside the notes on purpose were counted as missing. Deliberate pairs of notes were
called duplicates.

The lesson is worth more than the code: a check that cries wolf gets switched off, and then
nothing is being checked at all. Every rule in there is marked WHY, so you can read the reasoning
rather than trust it.
