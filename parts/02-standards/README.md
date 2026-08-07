# Part 2 of 4 - Standards

## The problem

The answers were better when there were twenty notes in there than they are now there are two
hundred.

It quoted you a price you stopped using months ago. It told you two different things about the
same client on two different days. You corrected something and the old version came back a
fortnight later. You have started checking its answers, which is most of the time you were saving.

## Why it happens

As the pile grows, more than one thing in it can answer the same question. Your AI uses whichever
it finds first, does not know the other exists, and never mentions there was a choice. The answer
arrives sounding exactly as certain as a correct one.

Underneath that: the rules you wrote about how things should be kept are ordinary sentences.
Sentences are advice. Nothing reads them and refuses a note for breaking them.

Nothing is counting any of it, which is the part that matters - a pile going wrong for months
looks identical from the outside to one that is fine.

## What this does about it

Turns your rules into a short list a program can check, and installs the check.

    python install.py

It finds your folder by itself and stops politely if Part 1 is not there. Nothing in your notes is
changed by installing it.

Then:

    python _engine/doctor.py            what changed
    python _engine/repair.py            what could be fixed automatically
    python _engine/repair.py --apply    fix it

## Why this way and not another

- A rule nothing can fail is not a rule.
- It reports rather than repairs. Anything a tool fixes by guessing at your meaning is a fault the
  tool introduced and you will never find. The repair command only touches things with one correct
  answer, and refuses the rest on purpose - including removing a stray file extension when the name
  it would leave belongs to two different notes.
- It records where you are starting from and only lets the numbers fall. Nothing has to be fixed
  today; today's mess just cannot become next month's larger mess.
- It is not tidying up. Tidying by hand is admin, and admin is what kills these systems.

## What is in here

    sb/_schema/note-types.json    your rules, as data. Yours to edit.
    sb/doctor.py                  the check. Reads and reports; never edits a note.
    sb/repair.py                  fixes only what has one correct answer
    tests/                        proof that it does not report faults that are not there

## About those tests

Six rules inside the check exist because the obvious version got them wrong on a real system of
nearly five thousand notes - and every time, the error said a healthy system was broken. A check
that cries wolf gets switched off, and then nothing is being checked at all. Each is marked WHY in
the source and pinned by a test.

## What it still does not do

Everything in it arrives because you sat down and typed it. That is Part 3.
