# What I stole

Each layer names its own borrowings. They are gathered here so the whole set can be read at once.

## Layer 1 - Memory

Nothing here is original, and none of it is paid for.

| Taken from | What was taken |
|---|---|
| Obsidian | The idea that a folder of plain text files is enough, and that the program should be optional rather than the point. |
| git | Every version of every file, kept on your own machine. It is thirty years old and still the correct answer to "can I undo that". |
| The PARA method (Tiago Forte) | Projects, Areas, Resources, Archive as the top-level split. Two rooms added - People and Decisions - because a one-person business runs on both. |
| Andrej Karpathy's LLM wiki pattern | Notes written for a machine to read as well as a person, with the rules kept in one file the machine reads first. |

The rulebook in one file, read before anything happens, is the piece that does the most work for
the least effort. Everything else here is arranging folders.

## Layer 2 - Standards

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

## Layer 3 - Capture

| Taken from | What was taken |
|---|---|
| Buzz and faster-whisper | Turning a recording into text on your own machine, so client conversations never leave it. |
| yt-dlp | Pulling the words out of a video without downloading the video. An hour of somebody talking becomes five minutes of reading. |
| Obsidian Web Clipper | One click saves a page as text with its source and date already filled in. |
| The two-pass reading habit | Capture on the author terms first, translate into your own second. Doing both at once produces neither, and the parts that disagree with you are the first thing lost. |

## What is not stolen

The four-channel split, and specifically the fourth one. Every tool above moves other people material.
Nothing exists that can put your own reasoning in for you, which is why that channel decides whether
the system sounds like you or like everybody else.

## Layer 4 - Operations

| Taken from | What was taken |
|---|---|
| cron, and Windows Task Scheduler | Things happen on a clock rather than when somebody remembers. Both are decades old and neither has been improved on for this job. |
| Append-only logs | A record that is only ever added to. What it said last month still says the same thing today, which is the whole point and the thing a rewritable note cannot do. |
| Rate limiting | One budget shared between everything rather than one each. Five things each politely limited still add up to an unreasonable number. |
| Human-in-the-loop review | The work stops at a queue and a person moves it. Old, unfashionable, and the reason nothing here has sent something it should not have. |

## What was learned the hard way

A job of mine ran sixty-four times, produced nothing, and reported success every time. Nobody noticed,
because a job with nothing to do and a job that has broken look identical from the outside.

That is why this layer ends with a comparison - what should be true against what is - rather than with
another feature. Silence is not evidence that things are fine.
