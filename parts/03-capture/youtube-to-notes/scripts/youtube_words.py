# -*- coding: utf-8 -*-
"""
youtube_words.py - the words of a YouTube video, as a note in your second brain.

    python youtube_words.py "https://www.youtube.com/watch?v=..."  [more links]

Run it from the top of your second brain. The notes go into the folder you run it from, so it
works in any second brain, however it was built.

It takes the words only, from the video's own subtitles, never the video itself. The words land in
Resources/YouTube/Transcripts/ as a transcript note, with a time mark every minute or so, so every
point taken from it can say where in the video it was said.

YouTube's automatic subtitles repeat each line two or three times as they roll up the screen. This
removes the repeats, so what you keep reads like one person talking rather than an echo.

It needs a free program called yt-dlp. If it is missing, this says how to install it and stops
without changing anything.

It never overwrites a note that is already there. If a video has been fetched before, it says so and
leaves the old note alone.

Needs: Python 3.8 or newer, and yt-dlp.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

OUT_ROOM = Path("Resources") / "YouTube" / "Transcripts"
MARK_EVERY = 60          # seconds between time marks in the note
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Subtitle languages in the order they are wanted. Subtitles a person wrote beat automatic ones,
# because automatic ones mishear names, which is the part of a video most worth keeping right.
# Named exactly: a pattern such as "en.*" also matches YouTube's machine translations into English
# ("en-de" and dozens more), which asks for every one of them and gets refused as too many requests.
LANG_PREFERENCE = ("en", "en-GB", "en-US", "en-orig")


def yt_dlp_command():
    """The way to run yt-dlp on this machine, or None if it is not installed."""
    for cmd in ([sys.executable, "-m", "yt_dlp"], ["yt-dlp"]):
        try:
            r = subprocess.run(cmd + ["--version"], capture_output=True, text=True,
                               creationflags=NO_WINDOW)
        except OSError:
            continue
        if r.returncode == 0:
            return cmd
    return None


# --- turning YouTube's subtitle file into plain words ----------------------------------------

CUE_TIME = re.compile(r"^(\d+):(\d\d):(\d\d)[.,]\d+\s+-->")
CUE_TIME_SHORT = re.compile(r"^(\d\d):(\d\d)[.,]\d+\s+-->")
TAG = re.compile(r"<[^>]+>")


def vtt_to_lines(vtt_text):
    """Return [(seconds, line)] with every repeated line removed, in the order spoken."""
    out = []
    recent = []            # the last few lines kept, because a rolled-up line can come back
    start = None
    for raw in vtt_text.splitlines():
        line = raw.strip()
        m = CUE_TIME.match(line)
        if m:
            start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        m = CUE_TIME_SHORT.match(line)
        if m:
            start = int(m.group(1)) * 60 + int(m.group(2))
            continue
        if (not line or start is None or line == "WEBVTT" or line.startswith(("Kind:", "Language:",
                                                                              "NOTE", "STYLE"))
                or line.isdigit()):
            continue
        text = TAG.sub("", line)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&gt;", ">") \
                   .replace("&lt;", "<").replace("&#39;", "'").replace("&quot;", '"')
        text = re.sub(r"\s+", " ", text).strip()
        if not text or text in recent:
            continue
        out.append((start, text))
        recent = (recent + [text])[-3:]
    return out


def mark(seconds):
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def lines_to_paragraphs(lines, link):
    """One paragraph per minute or so, each opening with a time mark that links to that moment."""
    paras, words, para_start = [], [], None
    for sec, text in lines:
        if para_start is None:
            para_start = sec
        if sec - para_start >= MARK_EVERY and words:
            paras.append((para_start, " ".join(words)))
            words, para_start = [], sec
        words.append(text)
    if words:
        paras.append((para_start, " ".join(words)))
    sep = "&" if "?" in link else "?"
    return "\n\n".join("[%s](%s%st=%d) %s" % (mark(s), link, sep, s, w) for s, w in paras)


# --- fetching --------------------------------------------------------------------------------

def pick_subtitle(folder, video_id, typed_langs):
    """The best subtitle file fetched: one a person typed if there is one, automatic if not."""
    found = {}
    for f in Path(folder).glob("%s.*.vtt" % video_id):
        found[f.name[len(video_id) + 1:-len(".vtt")]] = f
    for wanted_typed in (True, False):
        for lang in LANG_PREFERENCE:
            if lang in found and (lang in typed_langs) == wanted_typed:
                return lang, found[lang]
    return None, None


def safe_name(title):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f#^\[\]]', "", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:70].rstrip(" .") or "Untitled video"


def write_new(path, text):
    """Write a new file in one go, so a crash never leaves half a note behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, str(path))


def fetch(cmd, url, vault):
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            cmd + ["--skip-download", "--write-subs", "--write-auto-subs",
                   "--sub-langs", ",".join(LANG_PREFERENCE), "--sub-format", "vtt", "--write-info-json",
                   "--no-playlist", "--no-progress", "-o", os.path.join(tmp, "%(id)s.%(ext)s"),
                   url],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW)
        infos = list(Path(tmp).glob("*.info.json"))
        if r.returncode != 0 and not infos:
            last = (r.stderr.strip().splitlines() or ["no reason given"])[-1]
            return {"url": url, "result": "failed", "why": last}
        info = json.loads(infos[0].read_text(encoding="utf-8"))
        vid = info.get("id", "")
        typed_langs = set(info.get("subtitles") or {})
        lang, sub = pick_subtitle(tmp, vid, typed_langs)
        if sub is None:
            return {"url": url, "result": "no subtitles", "title": info.get("title", ""),
                    "why": "This video has no English subtitles, typed or automatic."}
        lines = vtt_to_lines(sub.read_text(encoding="utf-8", errors="replace"))

    title = info.get("title") or vid
    link = info.get("webpage_url") or url
    up = info.get("upload_date") or ""
    published = "%s-%s-%s" % (up[:4], up[4:6], up[6:8]) if len(up) == 8 else "unknown"
    manual = lang in typed_langs
    kind = ("subtitles a person typed" if manual else
            "YouTube's automatic subtitles, so names and numbers may be misheard")

    name = safe_name(title)
    out = vault / OUT_ROOM / ("%s - transcript.md" % name)
    # Windows refuses a full path over 260 characters. Shorten the title part until it fits.
    while len(str(out.resolve())) > 250 and len(name) > 20:
        name = name[:-10].rstrip(" .")
        out = vault / OUT_ROOM / ("%s - transcript.md" % name)
    if out.exists():
        return {"url": url, "result": "already here", "title": title,
                "transcript": str(out.relative_to(vault)).replace("\\", "/")}

    body = (
        "---\n"
        "date: %s\n"
        "type: transcript\n"
        "source: %s\n"
        "channel: %s\n"
        "published: %s\n"
        "subtitles: %s\n"
        "---\n\n"
        "## For future Claude\n\n"
        "The words of the YouTube video \"%s\" by %s, published %s, taken from %s "
        "on %s. Words only - the video itself was never downloaded. Every time mark links to that "
        "moment in the video. Kept here for this second brain only; never republish it.\n\n"
        "## Transcript\n\n%s\n"
        % (date.today().isoformat(), link, json.dumps(info.get("channel") or info.get("uploader")
                                                     or "unknown"),
           published, "typed" if manual else "automatic",
           title.replace('"', "'"), info.get("channel") or info.get("uploader") or "an unknown channel",
           published, kind, date.today().isoformat(), lines_to_paragraphs(lines, link)))
    write_new(out, body)
    return {"url": url, "result": "saved", "title": title, "channel": info.get("channel"),
            "published": published, "subtitles": "typed" if manual else "automatic",
            "transcript": str(out.relative_to(vault)).replace("\\", "/")}


def main(argv):
    urls = [a for a in argv if not a.startswith("-")]
    if not urls:
        print(__doc__)
        return 2
    vault = Path.cwd()
    cmd = yt_dlp_command()
    if cmd is None:
        print("This needs a free program called yt-dlp, and it is not installed.\n\n"
              "Install it with:\n\n    %s -m pip install yt-dlp\n\n"
              "then run this again. Nothing has been changed." % Path(sys.executable).name)
        return 3
    results = [fetch(cmd, u, vault) for u in urls]
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    return 0 if all(r["result"] in ("saved", "already here") for r in results) else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
