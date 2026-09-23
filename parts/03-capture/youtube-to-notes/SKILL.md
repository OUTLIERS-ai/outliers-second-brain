---
name: youtube-to-notes
description: Use when someone gives a YouTube link, or asks to get a YouTube video, its transcript or its ideas into their second brain. Pulls the words with yt-dlp, keeps the transcript, and writes a note of what was said with a link to the moment each point was made. Not for downloading or reposting videos.
---

# YouTube video into notes

## The one job

Turn a YouTube link into two notes in this second brain: the words of the video, kept as a
transcript, and a note of what was said that is worth keeping.

The second brain is the folder you were started in. Run everything from there.

## How

1. Run the helper that sits beside this file, with every link you were given:

       python "<this skill's folder>/scripts/youtube_words.py" "LINK" "ANOTHER LINK"

   On a Mac, if `python` is not found, use `python3`.

   A link copied from inside a playlist fetches that one video. Only when the person asks for a
   whole playlist or channel, add `--whole-playlist` before the link. It fetches up to 50 videos;
   add `--limit 10` (or any number) to change that, and tell the person how many it will fetch
   before you start.

   It needs the internet. If you are asked for permission to let it go online, that is why.

2. If it says yt-dlp is not installed, tell the person it is a free program that pulls the
   subtitles out of a YouTube video, then install it with the command the helper printed and run
   step 1 again. On a Mac, if that command is refused with "externally-managed-environment", use
   `brew install yt-dlp` instead. If installing still fails, show the error and stop.

3. It prints one line per video. `saved` or `already here` gives the transcript's path.
   `no subtitles` means the video has none it can use: say so and move on. `failed` gives the
   reason and what to do about it: pass both on plainly and move on. Never write a note for a
   video whose words you do not have. If a video was `already here` and a summary note for it
   already exists in `Resources/`, leave both alone and say so.

4. Read the transcript. Then write the summary as one note in `Resources/`, named after the
   video's title, with this at the top:

       ---
       date: <today, YYYY-MM-DD>
       type: resource
       source: <the video's link>
       channel: "<the channel, in double quotes>"
       ---

   Then these four parts:
   - **Summary**: three to five plain sentences - who made it, what it is about, and the main point
     in the speaker's own terms. Where the video has chapters (headings in the transcript), follow
     its own order.
   - **Key points**: the ideas worth keeping, one line each, each ending with its time mark from
     the transcript as a link, so it can be checked in seconds.
   - **Mentioned**: people, books, tools and companies named in the video. Where this second brain
     already has a note with that name, write it as `[[Name]]` so it links there. Otherwise write
     the name as plain text - a link to a note that does not exist is a broken link.
   - **Transcript**: a link to the transcript note, written as `[[<file name>]]` using the file
     name from the `transcript` path the helper printed, without the folders and without `.md`.
     The file name can differ from the title (some characters are removed), so never type it from
     the title.

   Name the summary note after the video's title, leaving out any of these characters, which
   break file names or links: `< > : " / \ | ? * # ^ [ ]`. Before saving, search the whole second
   brain for a note with that name, in any folder. If one exists - a person, a book, another
   video with the same title - add the video id in brackets, for example
   `Atomic Habits (dQw4w9WgXcQ)`. Two notes with one name break links.

5. Report back in three plain sentences: which notes were made, which videos were skipped and why,
   and whether any subtitles were automatic (automatic ones mishear names and numbers).

## Rules

- Words only. Never download the video or the audio.
- Write the summary in English. If the transcript is in another language (its `language` line says
  so), say in the summary that it was translated from that language by you.
- The summary says only what the video says. If you add anything from your own knowledge, mark it
  "(not from the video)".
- The transcript stays in this second brain. Never publish or post it anywhere.
- Every point says where in the video it was said. If you cannot find the moment, leave the point
  out.
- Automatic subtitles mishear names. Where a name looks wrong, write it as heard and add "(name as
  heard in automatic subtitles)" rather than guessing the right one.
- Capture what the speaker said first. What it means for this person's business is a separate
  pass, done only when asked.
- If this second brain has a rulebook (CLAUDE.md, AGENTS.md or _CLAUDE.md at the top), read it
  first and follow it where it says something different about where notes go or what they carry.
- Write into the folders this second brain already has. Do not invent new ones beyond
  `Resources/YouTube/Transcripts/`, which the helper makes.
