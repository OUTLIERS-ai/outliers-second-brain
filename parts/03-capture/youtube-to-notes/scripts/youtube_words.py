# -*- coding: utf-8 -*-
"""
youtube_words.py - the words of a YouTube video, as a note in your second brain.

    python youtube_words.py "https://www.youtube.com/watch?v=..."  [more links]
    python youtube_words.py --whole-playlist "https://www.youtube.com/playlist?list=..."
    python youtube_words.py --whole-playlist --limit 20 "https://www.youtube.com/@channel/videos"

Run it from the top of your second brain. The notes go into the folder you run it from, so it
works in any second brain, however it was built.

It takes the words only, from the video's own subtitles, never the video or the sound. Each video
becomes one transcript note in Resources/YouTube/Transcripts/, split by the video's own chapters
where it has them, with a time mark every 30 seconds that links to that moment in the video.

Which subtitles it uses, in order: English typed by a person; then YouTube's automatic English.
A video in another language keeps its words as spoken, in that language, and says so; the AI that
writes the summary writes it in English. YouTube's own translation is not used: it mistranslates
names, and YouTube refuses repeated requests for it far sooner than for ordinary subtitles.

A video already fetched is recognised by its YouTube id and left alone, never overwritten.

A link copied from inside a playlist fetches that one video. To fetch every video in a playlist
or channel, say so with --whole-playlist; --limit caps how many (50 unless you say otherwise).

It needs a free program called yt-dlp. If it is missing, this says how to install it and stops
without changing anything.

Prints one line per video, as JSON, for the AI that runs it:
    result  saved | already here | no subtitles | failed
Exit code 0 when every video was saved or already here.

Needs: Python 3.8 or newer for this file, and yt-dlp, which itself needs Python 3.10 or newer
(or its own standalone install: brew install yt-dlp on a Mac, winget install yt-dlp.yt-dlp on
Windows).
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

OUT_ROOM = Path("Resources") / "YouTube" / "Transcripts"
MARK_EVERY = 30              # seconds between time marks in the note
NAME_LIMIT = 80              # characters in the title part of a file name
PATH_LIMIT = 250             # Windows refuses full paths over 260 characters
PAUSE_BETWEEN = 3            # seconds between videos, so YouTube does not refuse the next one
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# yt-dlp 2026.8.19 states Requires-Python >=3.10 (read from its package details, 2026-09-23).
# This helper runs on 3.8, but installing yt-dlp into an older Python gives a stale copy.
YT_DLP_NEEDS = (3, 10)

# Subtitle formats in the order wanted. json3 lists each caption once. The older vtt format
# repeats every line as automatic captions roll up the screen, so it is cleaned (see vtt_lines).
SUB_FORMATS = "json3/vtt"


# --- running yt-dlp ----------------------------------------------------------------------------

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


def run(cmd, args):
    """Run yt-dlp. One retry after a pause if YouTube says too many requests."""
    for attempt in (1, 2):
        r = subprocess.run(cmd + args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=NO_WINDOW)
        if r.returncode == 0 or "429" not in r.stderr or attempt == 2:
            return r
        time.sleep(20)


def explain(stderr):
    """yt-dlp's last error line, and what the person can do about it, in plain words."""
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    last = next((ln for ln in reversed(lines) if "ERROR" in ln), lines[-1] if lines else "")
    last = last.replace("ERROR: ", "").strip() or "yt-dlp stopped without saying why"
    low = last.lower()
    if "429" in low or "too many requests" in low or "not a bot" in low:
        return last, ("YouTube is refusing requests from this internet connection for now. "
                      "Wait 15 minutes or so and try again.")
    if any(w in low for w in ("getaddrinfo", "timed out", "urlopen error", "network is unreachable",
                              "connection refused", "connection reset", "name resolution",
                              "nodename nor servname", "failed to resolve", "proxy", "tunnel")):
        return last, ("This could not reach the internet. Check the connection. If the AI you "
                      "are using blocks internet access, allow it for this command.")
    if "live event" in low or "premiere" in low or "is upcoming" in low:
        return last, "This video has not been shown yet. Try again once it has finished."
    if (any(w in low for w in ("private video", "video unavailable", "is unavailable",
                               "has been removed", "members-only", "join this channel",
                               "sign in", "age-restricted", "confirm your age"))
            or re.search(r"\bage\b", low)):
        return last, "This video cannot be read without signing in, or no longer exists."
    if "unsupported url" in low or "is not a valid url" in low:
        return last, "That is not a YouTube video link."
    return last, ("If this keeps happening, YouTube may have changed something that yt-dlp has "
                  "since caught up with. Update it with: %s" % update_command())


def install_command():
    """How to install yt-dlp for the Python running this, with a route that works on a Mac too."""
    pip = '"%s" -m pip install yt-dlp' % sys.executable
    if sys.platform == "darwin":
        return pip + "   (if that is refused, use: brew install yt-dlp)"
    return pip


def update_command():
    pip = '"%s" -m pip install -U yt-dlp' % sys.executable
    if sys.platform == "darwin":
        return pip + "   (or, if it was installed with Homebrew: brew upgrade yt-dlp)"
    return pip


# --- choosing the subtitles ----------------------------------------------------------------------

def is_english(code):
    return code == "en" or code.startswith("en-")


def choose_track(info):
    """Return (language code, 'typed' | 'automatic', spoken language) or None.

    English typed by a person first, because automatic subtitles mishear names. Then automatic
    English. For a video in another language: its own words, typed first, then automatic. Never
    YouTube's machine translation (see the note at the top).
    """
    typed = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    spoken = (info.get("language") or "").strip()
    # The automatic list's "<language>-orig" entry is the language YouTube actually heard, which
    # beats the language the uploader set (often blank, sometimes wrong). With it known, plain
    # "en" in the automatic list is a translation unless the video really is in English.
    orig = sorted(c[:-len("-orig")] for c in auto if c.endswith("-orig"))
    if len(orig) == 1 and orig[0].split("-")[0].lower() != spoken.split("-")[0].lower():
        spoken = orig[0]
    elif not spoken:
        other_typed = sorted({c.split("-")[0].lower() for c in typed if not is_english(c)})
        if not any(is_english(c) for c in typed) and other_typed:
            spoken = other_typed[0]
    base = spoken.split("-")[0].lower()

    for code in ("en", "en-GB", "en-US") + tuple(sorted(c for c in typed if is_english(c))):
        if code in typed:
            return code, "typed", spoken
    if not base or base == "en":
        english_heard = "en-orig" in auto or not orig
        for code in ("en-orig", "en", "en-GB", "en-US"):
            if code in auto and english_heard:
                return code, "automatic", spoken
        return None
    # A video in another language: its own words. In the automatic list, "<language>-orig" is
    # the words as heard; plain "en" there would be YouTube's translation, so it is not used.
    for code in (spoken, base) + tuple(sorted(c for c in typed if c.split("-")[0].lower() == base)):
        if code in typed:
            return code, "typed", spoken
    for code in (base + "-orig", spoken, base):
        if code in auto:
            return code, "automatic", spoken
    return None


# --- turning subtitle files into (seconds, words) ------------------------------------------------

def decode(text):
    # &amp; last, so "&amp;gt;" becomes "&gt;" as written rather than ">".
    for a, b in (("&nbsp;", " "), ("&gt;", ">"), ("&lt;", "<"), ("&#39;", "'"),
                 ("&quot;", '"'), ("&amp;", "&")):
        text = text.replace(a, b)
    return text


def json3_lines(raw):
    """json3 lists each caption once, with its start in milliseconds."""
    out = []
    for ev in json.loads(raw).get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = re.sub(r"\s+", " ", "".join(s.get("utf8", "") for s in segs)).strip()
        if text:
            out.append((int(ev.get("tStartMs", 0)) // 1000, text))
    return out


CUE = re.compile(r"^(?:(\d+):)?(\d\d):(\d\d)[.,]\d+\s+-->")
TAG = re.compile(r"<[^>]+>")


def vtt_lines(raw, rolling=True):
    """vtt, cleaned: tags stripped, entities decoded, and the roll-up repeats removed.

    YouTube's automatic captions show two lines at a time. When a caption begins, its first line
    is the line the previous caption ended on, carried up the screen. So only the FIRST line of a
    caption can be a repeat, and it is one only when it matches the last line kept. Comparing any
    other line would throw away real words said twice ("no, no"). Captions a person typed do not
    roll, so with rolling=False nothing is dropped.
    """
    out, last = [], None
    # A vtt file is blocks separated by blank lines. A block with a timing line is a caption;
    # anything above its timing line is the caption's number or name, not words. A block with no
    # timing line (the header, NOTE, STYLE) holds no words at all.
    # Split only on truly empty lines: YouTube's automatic captions contain lines holding a single
    # space, which belong to the caption they sit in.
    for block in re.split(r"\n\n+", raw.replace("\r\n", "\n")):
        rows = [r.strip() for r in block.split("\n")]
        timing = next((i for i, r in enumerate(rows) if CUE.match(r)), None)
        if timing is None:
            continue
        m = CUE.match(rows[timing])
        start = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        first = True
        for row in rows[timing + 1:]:
            text = re.sub(r"\s+", " ", decode(TAG.sub("", row))).strip()
            if not text:
                continue
            carried = rolling and first and text == last
            first = False
            if carried:
                continue
            out.append((start, text))
            last = text
    return out


# --- writing the note ----------------------------------------------------------------------------

def mark(seconds):
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def at(link, seconds):
    return "%s%st=%d" % (link, "&" if "?" in link else "?", int(seconds))


def paragraphs(lines, link):
    """A paragraph every MARK_EVERY seconds, each opening with a linked time mark."""
    paras, words, start = [], [], None
    for sec, text in lines:
        if start is None:
            start = sec
        if sec - start >= MARK_EVERY and words:
            paras.append((start, " ".join(words)))
            words, start = [], sec
        words.append(text)
    if words:
        paras.append((start, " ".join(words)))
    return "\n\n".join("[%s](%s) %s" % (mark(s), at(link, s), w) for s, w in paras)


def body_text(lines, chapters, link):
    """The transcript, under the video's own chapter headings where it has them."""
    usable = sorted((c for c in (chapters or [])
                     if c.get("title") and c.get("start_time") is not None),
                    key=lambda c: c["start_time"])
    if len(usable) < 2:
        return paragraphs(lines, link)
    parts = []
    for i, ch in enumerate(usable):
        begin = ch["start_time"]
        end = usable[i + 1]["start_time"] if i + 1 < len(usable) else float("inf")
        # The first chapter also takes anything said before it starts.
        inside = [(s, t) for s, t in lines if (s < end and (s >= begin or i == 0))]
        if inside:
            parts.append("### [%s](%s) %s\n\n%s" % (mark(begin), at(link, begin),
                                                     ch["title"].strip(),
                                                     paragraphs(inside, link)))
    return "\n\n".join(parts)


WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {"com%d" % i for i in range(1, 10)} \
    | {"lpt%d" % i for i in range(1, 10)}


def shorten(name, chars, max_bytes):
    """Cut to at most `chars` characters and `max_bytes` bytes, at a whole word where possible.
    A Mac counts a file name in bytes (255 at most), and one Japanese character is 3 bytes."""
    if len(name) <= chars and len(name.encode("utf-8")) <= max_bytes:
        return name
    cut = name[:chars]
    while len(cut.encode("utf-8")) > max_bytes:
        cut = cut[:-1]
    at_word = cut.rsplit(" ", 1)[0] if " " in cut else cut
    # Titles without spaces (Chinese, Japanese) are cut where they must be.
    return (at_word if len(at_word) >= len(cut) // 2 else cut).rstrip(" .,;-")


def safe_name(title):
    """A file name Windows, Mac and Obsidian all accept, cut at a whole word."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f#^\[\]]', "", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    name = shorten(name, NAME_LIMIT, 200)
    if name.split(".")[0].strip().lower() in WINDOWS_RESERVED:
        name = "Video - " + name
    return name or "Untitled video"


def yaml_text(s):
    return json.dumps(str(s), ensure_ascii=False)


def already_fetched(folder, video_id):
    if not folder.exists():
        return None
    # The first version of this helper wrote no video_id, only the link, so both are looked for.
    needles = ("video_id: %s" % yaml_text(video_id),
               "source: https://www.youtube.com/watch?v=%s\n" % video_id)
    for f in folder.glob("*.md"):
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:1500]
        except OSError:
            continue
        if any(n in head for n in needles):
            return f
    return None


def free_path(folder, name, video_id):
    """A path that does not exist yet, short enough for Windows."""
    out = folder / ("%s - transcript.md" % name)
    while len(str(out.resolve())) > PATH_LIMIT and len(name) > 20:
        name = shorten(name, len(name) - 10, 200) or name[:len(name) - 10]
        out = folder / ("%s - transcript.md" % name)
    if out.exists():                      # same title, different video
        out = folder / ("%s (%s) - transcript.md" % (name, video_id))
    return out


def write_new(path, text):
    """Write the whole note in one go, so a crash never leaves half a note behind.
    Retries a few times, because a sync program such as OneDrive can hold a file for a moment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        for attempt in range(5):
            try:
                os.replace(tmp, str(path))
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.5)
    finally:
        if os.path.exists(tmp):          # anything went wrong: leave no half-made file behind
            os.remove(tmp)


# --- one video -----------------------------------------------------------------------------------

YOUTUBE_LINK = re.compile(r"^(https?://)?((www|m|music)\.)?(youtube\.com|youtu\.be|"
                          r"youtube-nocookie\.com)(/|$)", re.I)


def fetch(cmd, url, vault):
    folder = vault / OUT_ROOM
    if not YOUTUBE_LINK.match(url.strip()):
        return {"url": url, "result": "failed", "why": "This is not a YouTube link.",
                "what to do": "This assistant only reads YouTube videos."}
    with tempfile.TemporaryDirectory() as tmp:
        info_path = Path(tmp) / "info.json"
        # --flat-playlist: if this turns out to be a playlist or channel link, list it rather than
        # looking up every video in it.
        r = run(cmd, ["--skip-download", "--no-playlist", "--flat-playlist", "--no-warnings",
                      "--dump-single-json", url])
        if r.returncode != 0 or not r.stdout.strip():
            why, fix = explain(r.stderr)
            return {"url": url, "result": "failed", "why": why, "what to do": fix}
        info = json.loads(r.stdout)
        if info.get("_type") in ("playlist", "multi_video") or "entries" in info:
            return {"url": url, "result": "failed",
                    "why": "This is a playlist or channel link, not one video.",
                    "what to do": "To fetch its videos, run again with --whole-playlist before "
                                  "the link (and --limit to cap how many)."}
        if info.get("extractor_key") != "Youtube":
            return {"url": url, "result": "failed",
                    "why": "This is not a YouTube video (it is from %s)."
                           % (info.get("extractor_key") or "another site"),
                    "what to do": "This assistant only reads YouTube videos."}
        vid = info.get("id", "")
        title = info.get("title") or vid
        link = "https://www.youtube.com/watch?v=%s" % vid if vid else url

        existing = already_fetched(folder, vid)
        if existing:
            return {"url": url, "result": "already here", "title": title,
                    "transcript": existing.relative_to(vault).as_posix()}

        track = choose_track(info)
        if track is None:
            return {"url": url, "result": "no subtitles", "title": title,
                    "why": "This video has no subtitles, typed or automatic, that can be used."}
        lang, kind, spoken = track

        info_path.write_text(json.dumps(info), encoding="utf-8")
        r = run(cmd, ["--load-info-json", str(info_path), "--skip-download",
                      "--write-subs" if kind == "typed" else "--write-auto-subs",
                      "--sub-langs", lang, "--sub-format", SUB_FORMATS,
                      "-o", str(Path(tmp) / "sub.%(ext)s")])
        subs = sorted(Path(tmp).glob("sub.*.json3")) or sorted(Path(tmp).glob("sub.*.vtt"))
        if not subs:
            # Warnings are kept on for this step: yt-dlp gives its reason for skipping subtitles
            # as a warning, not an error.
            warned = [ln.replace("WARNING: ", "") for ln in r.stderr.splitlines()
                      if "WARNING" in ln and "subtitle" in ln.lower()]
            if r.returncode != 0:
                why, fix = explain(r.stderr)
            elif warned:
                why, fix = warned[-1].strip(), ("YouTube did not hand the subtitles over. Update "
                                                "yt-dlp and try again: %s" % update_command())
            else:
                why, fix = ("The subtitles were listed but did not download.",
                            "Try again in a few minutes.")
            return {"url": url, "result": "failed", "title": title, "why": why,
                    "what to do": fix}
        raw = subs[0].read_text(encoding="utf-8", errors="replace")
        lines = (json3_lines(raw) if subs[0].suffix == ".json3"
                 else vtt_lines(raw, rolling=(kind != "typed")))

    if not lines:
        return {"url": url, "result": "no subtitles", "title": title,
                "why": "The subtitle file was empty."}

    channel = info.get("channel") or info.get("uploader") or "unknown"
    up = info.get("upload_date") or ""
    published = "%s-%s-%s" % (up[:4], up[4:6], up[6:8]) if len(up) == 8 else "unknown"
    words = sum(len(t.split()) for _, t in lines)
    today = date.today().isoformat()
    in_language = "" if is_english(lang) else " in the video's own language (%s)" % lang
    source_words = ("subtitles typed by a person%s" % in_language if kind == "typed" else
                    "YouTube's automatic subtitles%s, so names and numbers may be misheard"
                    % in_language)

    fields = [("date", today), ("type", "transcript"), ("title", yaml_text(title)),
              ("source", link), ("video_id", yaml_text(vid)), ("channel", yaml_text(channel)),
              ("published", published)]
    # Quoted: some readers take 15:42 as a number of seconds, and the code for Norwegian, no,
    # as the word false.
    if info.get("duration"):
        fields.append(("duration", yaml_text(mark(info["duration"]))))
    fields.append(("language", yaml_text(spoken or lang)))
    fields.append(("subtitles", kind))
    fields.append(("words", words))
    counts = [(k, info[c]) for k, c in (("views", "view_count"), ("likes", "like_count"))
              if isinstance(info.get(c), int)]
    if counts:
        fields += counts + [("counted_on", today)]

    note = ("---\n%s\n---\n\n# %s\n\n"
            "## For future Claude\n\n"
            "The words of the YouTube video \"%s\" by %s, published %s, taken on %s from %s. "
            "Words only: the video itself was never downloaded. Every time mark links to that "
            "moment in the video. Kept for this second brain only; never publish or post it.\n\n"
            "## Transcript\n\n%s\n"
            % ("\n".join("%s: %s" % kv for kv in fields), title, title.replace('"', "'"),
               channel, published, today, source_words,
               body_text(lines, info.get("chapters"), link)))

    out = free_path(folder, safe_name(title), vid)
    write_new(out, note)
    return {"url": url, "result": "saved", "title": title, "channel": channel,
            "published": published, "subtitles": kind, "language": spoken or lang,
            "words": words, "chapters": len(info.get("chapters") or []),
            "transcript": out.relative_to(vault).as_posix()}


CHANNEL_HOME = re.compile(r"^(https?://(?:www\.|m\.)?youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|"
                          r"c/[^/?#]+|user/[^/?#]+))/?(?:[?#].*)?$")


def expand(cmd, url, limit):
    """The watch links of the videos in a playlist or channel, up to the limit.

    A channel's front page lists its tabs (Videos, Shorts, Live), not videos, so it is read as
    its Videos tab. Entries are kept only if they are YouTube videos, and their links are built
    from their ids, so nothing else on the page is mistaken for a video.
    """
    home = CHANNEL_HOME.match(url)
    if home:
        url = home.group(1) + "/videos"
    r = run(cmd, ["--flat-playlist", "--yes-playlist", "--no-warnings", "--print",
                  "%(ie_key)s %(id)s", "--playlist-end", str(limit), url])
    links = []
    for row in r.stdout.splitlines():
        parts = row.split()
        if len(parts) == 2 and parts[0] == "Youtube":
            links.append("https://www.youtube.com/watch?v=%s" % parts[1])
    if links:
        return links, None
    if r.returncode != 0:
        return [], explain(r.stderr)
    return [], ("No videos found at that link.",
                "Check it is a playlist or a channel's videos page.")


def parse_args(argv):
    """(links, whole playlist?, limit) or raise ValueError with a plain message."""
    whole, limit, links, i = False, 50, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--whole-playlist":
            whole = True
        elif a == "--limit" or a.startswith("--limit="):
            value = a.split("=", 1)[1] if "=" in a else (argv[i + 1] if i + 1 < len(argv) else "")
            if "=" not in a:
                i += 1
            if not value.isdigit() or int(value) < 1:
                raise ValueError("--limit needs a whole number, for example --limit 20")
            limit = int(value)
        elif a.startswith("-"):
            raise ValueError("Unknown option %s. The options are --whole-playlist and --limit."
                             % a)
        else:
            links.append(a)
        i += 1
    return links, whole, limit


def main(argv):
    try:
        urls, whole, limit = parse_args(argv)
    except ValueError as exc:
        print(exc)
        return 2
    if not urls:
        print(__doc__)
        return 2

    cmd = yt_dlp_command()
    if cmd is None:
        if tuple(sys.version_info[:2]) < YT_DLP_NEEDS:
            standalone = ("brew install yt-dlp" if sys.platform == "darwin" else
                          "winget install yt-dlp.yt-dlp   (then close and reopen the terminal)")
            print("This needs a free program called yt-dlp, and it is not installed.\n\n"
                  "Current yt-dlp needs Python %d.%d or newer, and this is Python %d.%d, so "
                  "installing it into this Python would give an old copy that YouTube no longer "
                  "works with. Either install a newer Python from python.org, or install yt-dlp "
                  "on its own:\n\n    %s\n\nthen run this again. Nothing has been changed."
                  % (YT_DLP_NEEDS[0], YT_DLP_NEEDS[1], sys.version_info[0], sys.version_info[1],
                     standalone))
            return 3
        print("This needs a free program called yt-dlp, and it is not installed.\n\n"
              "Install it with:\n\n    %s\n\n"
              "then run this again. Nothing has been changed." % install_command())
        return 3

    ok = True
    if whole:
        expanded = []
        for u in urls:
            links, problem = expand(cmd, u, limit)
            if problem:
                ok = False
                print(json.dumps({"url": u, "result": "failed", "why": problem[0],
                                  "what to do": problem[1]}, ensure_ascii=False), flush=True)
            expanded += links
        urls = expanded

    vault = Path.cwd()
    for i, u in enumerate(urls):
        if i:
            time.sleep(PAUSE_BETWEEN)
        try:
            result = fetch(cmd, u, vault)
        except Exception as exc:          # one bad video must not stop the rest
            result = {"url": u, "result": "failed", "why": "%s: %s" % (type(exc).__name__, exc)}
        ok = ok and result["result"] in ("saved", "already here")
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if ok and urls else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
