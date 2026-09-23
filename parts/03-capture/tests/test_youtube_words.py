# -*- coding: utf-8 -*-
"""
Tests for youtube-to-notes/scripts/youtube_words.py. No internet needed.

    python -m unittest discover tests

The subtitle files here are written by us, laid out the way YouTube lays out its automatic
captions: every line shown twice as it rolls up the screen, the new words carrying timing tags.
The central promise is that cleaning removes those repeats and never a word that was said.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "youtube-to-notes" / "scripts"))
import youtube_words as yw  # noqa: E402

# One talk, as said. "no" is said twice in a row on purpose: a cleaner that drops anything seen
# recently would lose the second one.
SAID = ["so the first thing to know", "is that nobody reads the manual", "no", "no",
        "and that is fine", "because the manual is wrong"]

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000 align:start position:0%
so<00:00:00.300><c> the</c><00:00:00.600><c> first</c><00:00:00.900><c> thing</c><00:00:01.200><c> to</c><00:00:01.500><c> know</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
so the first thing to know


00:00:02.010 --> 00:00:04.000 align:start position:0%
so the first thing to know
is<00:00:02.300><c> that</c><00:00:02.600><c> nobody</c><00:00:02.900><c> reads</c><00:00:03.200><c> the</c><00:00:03.500><c> manual</c>

00:00:04.000 --> 00:00:04.010 align:start position:0%
is that nobody reads the manual


00:00:04.010 --> 00:00:05.000 align:start position:0%
is that nobody reads the manual
no

00:00:05.000 --> 00:00:06.000 align:start position:0%
no
no

00:00:36.000 --> 00:00:38.000 align:start position:0%
no
and<00:00:36.300><c> that</c><00:00:36.600><c> is</c><00:00:36.900><c> fine</c>

00:00:38.000 --> 00:00:38.010 align:start position:0%
and that is fine


00:00:38.010 --> 00:00:40.000 align:start position:0%
and that is fine
because<00:00:38.300><c> the</c><00:00:38.600><c> manual</c><00:00:38.900><c> is</c><00:00:39.200><c> wrong</c>
"""

JSON3 = json.dumps({"events": [
    {"tStartMs": 0, "segs": [{"utf8": "so"}, {"utf8": " the first thing to know"}]},
    {"tStartMs": 2000, "aAppend": 1, "segs": [{"utf8": "\n"}]},
    {"tStartMs": 2010, "segs": [{"utf8": "is that nobody reads the manual"}]},
    {"tStartMs": 4010, "segs": [{"utf8": "no"}]},
    {"tStartMs": 5000, "segs": [{"utf8": "no"}]},
    {"tStartMs": 36000, "segs": [{"utf8": "and that is fine"}]},
    {"tStartMs": 36500},
    {"tStartMs": 38010, "segs": [{"utf8": "because the manual is wrong"}]},
]})


def words(lines):
    return " ".join(t for _, t in lines).split()


class Cleaning(unittest.TestCase):
    def test_rolling_vtt_keeps_every_word_said_and_no_repeat(self):
        self.assertEqual(words(yw.vtt_lines(ROLLING_VTT)), " ".join(SAID).split())

    def test_json3_gives_the_same_words_as_vtt(self):
        self.assertEqual(words(yw.json3_lines(JSON3)), words(yw.vtt_lines(ROLLING_VTT)))

    def test_times_are_kept(self):
        lines = yw.vtt_lines(ROLLING_VTT)
        self.assertEqual(lines[0][0], 0)
        self.assertEqual(lines[-1], (38, "because the manual is wrong"))

    def test_entities_decoded_with_amp_last(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nrock &amp; roll &gt; jazz &amp;gt;\n"
        self.assertEqual(yw.vtt_lines(vtt), [(1, "rock & roll > jazz &gt;")])

    def test_cue_numbers_and_note_blocks_are_not_words(self):
        vtt = ("WEBVTT\n\nNOTE a comment\nmore of it\n\nSTYLE\n::cue { color: red }\n\n"
               "1\n00:00:01.000 --> 00:00:02.000\nhello there\n\n"
               "2\n00:00:02.000 --> 00:00:03.000\n10 people came\n")
        self.assertEqual(yw.vtt_lines(vtt, rolling=False), [(1, "hello there"), (2, "10 people came")])

    def test_typed_captions_keep_a_line_said_twice(self):
        vtt = ("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nNo.\n\n"
               "00:00:02.000 --> 00:00:03.000\nNo.\n")
        self.assertEqual(len(yw.vtt_lines(vtt, rolling=False)), 2)

    def test_windows_line_endings(self):
        vtt = "WEBVTT\r\n\r\n00:00:01.000 --> 00:00:02.000\r\nhello\r\n"
        self.assertEqual(yw.vtt_lines(vtt), [(1, "hello")])

    def test_hour_long_timestamps(self):
        vtt = "WEBVTT\n\n01:02:03.000 --> 01:02:04.000\nlate on\n"
        self.assertEqual(yw.vtt_lines(vtt), [(3723, "late on")])


class Layout(unittest.TestCase):
    LINK = "https://www.youtube.com/watch?v=abc"

    def test_time_marks_link_to_the_moment(self):
        text = yw.paragraphs(yw.vtt_lines(ROLLING_VTT), self.LINK)
        self.assertIn("[0:00](https://www.youtube.com/watch?v=abc&t=0) so the first", text)
        self.assertIn("[0:36](https://www.youtube.com/watch?v=abc&t=36) and that is fine", text)

    def test_chapters_become_headings_and_lose_no_words(self):
        chapters = [{"start_time": 0, "title": "Opening"}, {"start_time": 30, "title": "Close"}]
        text = yw.body_text(yw.vtt_lines(ROLLING_VTT), chapters, self.LINK)
        self.assertIn("### [0:00](https://www.youtube.com/watch?v=abc&t=0) Opening", text)
        self.assertIn("### [0:30](https://www.youtube.com/watch?v=abc&t=30) Close", text)
        body = " ".join(ln for ln in text.splitlines() if not ln.startswith("###"))
        for w in SAID:
            self.assertIn(w, body)

    def test_words_before_the_first_chapter_are_kept(self):
        chapters = [{"start_time": 3, "title": "A"}, {"start_time": 30, "title": "B"}]
        text = yw.body_text(yw.vtt_lines(ROLLING_VTT), chapters, self.LINK)
        self.assertIn("so the first thing to know", text)

    def test_chapters_out_of_order_duplicate_nothing(self):
        chapters = [{"start_time": 0, "title": "A"}, {"start_time": 30, "title": "C"},
                    {"start_time": 3, "title": "B"}]
        text = yw.body_text(yw.vtt_lines(ROLLING_VTT), chapters, self.LINK)
        body = " ".join(ln for ln in text.splitlines() if not ln.startswith("###"))
        self.assertEqual(body.count("because the manual is wrong"), 1)
        self.assertEqual(body.count("so the first thing to know"), 1)

    def test_one_chapter_is_treated_as_none(self):
        text = yw.body_text(yw.vtt_lines(ROLLING_VTT), [{"start_time": 0, "title": "All"}],
                            self.LINK)
        self.assertNotIn("###", text)


class Names(unittest.TestCase):
    def test_illegal_characters_removed(self):
        self.assertEqual(yw.safe_name('What? A "Plan": #1 [2026] / part|2'),
                         "What A Plan 1 2026 part2")

    def test_long_title_cut_at_a_whole_word(self):
        title = "The Fastest Way To Build A One-Person Business Without Losing Your Mind Or Your Weekend"
        name = yw.safe_name(title)
        self.assertLessEqual(len(name), yw.NAME_LIMIT)
        self.assertTrue(title.startswith(name))
        self.assertEqual(title[len(name)], " ")

    def test_empty_title(self):
        self.assertEqual(yw.safe_name("???"), "Untitled video")

    def test_japanese_title_fits_a_mac_file_name(self):
        name = yw.safe_name("日本語のタイトル" * 20)
        self.assertLessEqual(len((name + " - transcript.md").encode("utf-8")), 255)
        self.assertTrue(name)

    def test_emoji_title_fits(self):
        name = yw.safe_name("🔥 " * 100 + "How I did it")
        self.assertLessEqual(len((name + " - transcript.md").encode("utf-8")), 255)

    def test_windows_reserved_name(self):
        self.assertEqual(yw.safe_name("CON"), "Video - CON")
        self.assertEqual(yw.safe_name("nul.txt"), "Video - nul.txt")


class Errors(unittest.TestCase):
    def test_offline_is_not_reported_as_private(self):
        _, fix = yw.explain("ERROR: [youtube] abc: Unable to download webpage: "
                            "<urlopen error [Errno 11001] getaddrinfo failed>")
        self.assertIn("internet", fix)
        self.assertNotIn("signing in", fix)

    def test_server_error_page_is_not_reported_as_private(self):
        _, fix = yw.explain("ERROR: [youtube] abc: Unable to download API page: HTTP Error 500")
        self.assertNotIn("signing in", fix)

    def test_age_restricted_is_reported_as_such(self):
        _, fix = yw.explain("ERROR: [youtube] abc: Sign in to confirm your age.")
        self.assertIn("signing in", fix)

    def test_blocked_by_a_proxy_is_a_network_problem(self):
        _, fix = yw.explain("ERROR: Unable to download webpage: Tunnel connection failed: "
                            "403 Forbidden (caused by ProxyError)")
        self.assertIn("internet", fix)

    def test_live_event_not_started(self):
        _, fix = yw.explain("ERROR: [youtube] abc: This live event will begin in 3 hours.")
        self.assertIn("not been shown yet", fix)

    def test_too_many_requests(self):
        for msg in ("ERROR: Unable to download video subtitles: HTTP Error 429",
                    "ERROR: [youtube] abc: Sign in to confirm you're not a bot."):
            _, fix = yw.explain(msg)
            self.assertIn("Wait", fix, msg)


class Arguments(unittest.TestCase):
    def test_limit_both_ways(self):
        self.assertEqual(yw.parse_args(["--limit", "5", "L"]), (["L"], False, 5))
        self.assertEqual(yw.parse_args(["--limit=7", "--whole-playlist", "L"]), (["L"], True, 7))

    def test_bad_limit_and_unknown_option(self):
        for bad in (["--limit", "x", "L"], ["--limit"], ["--limit=0", "L"], ["--oops", "L"]):
            with self.assertRaises(ValueError):
                yw.parse_args(bad)

    def test_only_youtube_links_are_accepted(self):
        for u in ("https://www.youtube.com/watch?v=abc", "https://youtu.be/abc",
                  "youtube.com/watch?v=abc", "https://m.youtube.com/watch?v=abc",
                  "https://music.youtube.com/watch?v=abc", "https://www.youtube.com/shorts/abc"):
            self.assertTrue(yw.YOUTUBE_LINK.match(u), u)
        for u in ("https://vimeo.com/1", "https://notyoutube.com/watch?v=abc",
                  "https://youtube.com.evil.example/watch", "https://www.tiktok.com/@a/video/1"):
            self.assertFalse(yw.YOUTUBE_LINK.match(u), u)
        result = yw.fetch(None, "https://vimeo.com/1", Path("."))
        self.assertEqual(result["why"], "This is not a YouTube link.")

    def test_channel_front_page_is_read_as_its_videos_tab(self):
        for u in ("https://www.youtube.com/@DanKoeTalks", "https://youtube.com/@DanKoeTalks/",
                  "https://www.youtube.com/channel/UC123"):
            self.assertTrue(yw.CHANNEL_HOME.match(u), u)
        for u in ("https://www.youtube.com/@DanKoeTalks/videos",
                  "https://www.youtube.com/playlist?list=PL1"):
            self.assertFalse(yw.CHANNEL_HOME.match(u), u)


class Choosing(unittest.TestCase):
    def test_typed_beats_automatic(self):
        info = {"language": "en", "subtitles": {"en-US": []},
                "automatic_captions": {"en": [], "en-orig": []}}
        self.assertEqual(yw.choose_track(info), ("en-US", "typed", "en"))

    def test_automatic_english_prefers_the_original_words(self):
        info = {"language": "en", "automatic_captions": {"en": [], "en-orig": [], "de": []}}
        self.assertEqual(yw.choose_track(info), ("en-orig", "automatic", "en"))

    def test_other_language_keeps_its_own_words_never_the_translation(self):
        info = {"language": "de", "automatic_captions": {"de-orig": [], "de": [], "en": []}}
        self.assertEqual(yw.choose_track(info), ("de-orig", "automatic", "de"))

    def test_other_language_typed_beats_automatic(self):
        info = {"language": "de-DE", "subtitles": {"de": []},
                "automatic_captions": {"de-orig": [], "en": []}}
        self.assertEqual(yw.choose_track(info), ("de", "typed", "de-DE"))

    def test_typed_english_on_a_foreign_video_is_used(self):
        info = {"language": "fr", "subtitles": {"en": []}, "automatic_captions": {"en": []}}
        self.assertEqual(yw.choose_track(info), ("en", "typed", "fr"))

    def test_foreign_video_with_only_a_translation_is_refused(self):
        info = {"language": "fr", "automatic_captions": {"en": []}}
        self.assertIsNone(yw.choose_track(info))

    def test_blank_language_is_read_from_the_orig_entry_not_translated(self):
        info = {"language": None, "automatic_captions": {"de-orig": [], "de": [], "en": []}}
        self.assertEqual(yw.choose_track(info), ("de-orig", "automatic", "de"))

    def test_blank_language_with_only_foreign_typed_subtitles(self):
        info = {"subtitles": {"fr": []}, "automatic_captions": {"en": [], "fr": []}}
        self.assertEqual(yw.choose_track(info), ("fr", "typed", "fr"))

    def test_video_wrongly_marked_english_does_not_get_the_translation(self):
        info = {"language": "en", "automatic_captions": {"es-orig": [], "es": [], "en": []}}
        self.assertEqual(yw.choose_track(info), ("es-orig", "automatic", "es"))

    def test_unknown_language_with_two_foreign_typed_tracks_uses_one(self):
        info = {"subtitles": {"fr": [], "es": []}}
        self.assertEqual(yw.choose_track(info), ("es", "typed", "es"))

    def test_english_with_no_orig_entry_uses_plain_en(self):
        info = {"language": "en", "automatic_captions": {"en": []}}
        self.assertEqual(yw.choose_track(info), ("en", "automatic", "en"))

    def test_nothing_usable(self):
        self.assertIsNone(yw.choose_track({"language": "en", "automatic_captions": {"fr": []}}))


class Files(unittest.TestCase):
    def test_a_video_already_fetched_is_found_by_its_id(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "Renamed by hand.md").write_text(
                '---\ndate: 2026-09-23\nvideo_id: "abc123"\n---\n', encoding="utf-8")
            self.assertEqual(yw.already_fetched(folder, "abc123").name, "Renamed by hand.md")
            self.assertIsNone(yw.already_fetched(folder, "zzz999"))

    def test_first_version_notes_are_found_by_their_link(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "Old.md").write_text(
                "---\nsource: https://www.youtube.com/watch?v=abc123\n---\n", encoding="utf-8")
            self.assertIsNotNone(yw.already_fetched(folder, "abc123"))
            self.assertIsNone(yw.already_fetched(folder, "abc12"))

    def test_same_title_different_video_gets_its_own_file(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "Same - transcript.md").write_text("x", encoding="utf-8")
            self.assertEqual(yw.free_path(folder, "Same", "vid2").name,
                             "Same (vid2) - transcript.md")

    def test_failed_write_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "note.md"
            original = yw.os.replace

            def refuse(a, b):
                raise FileNotFoundError("path too long")
            yw.os.replace = refuse
            try:
                with self.assertRaises(FileNotFoundError):
                    yw.write_new(target, "hello")
            finally:
                yw.os.replace = original
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_write_new_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "a" / "note.md"
            yw.write_new(target, "hello")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")
            self.assertEqual([p.name for p in target.parent.iterdir()], ["note.md"])


if __name__ == "__main__":
    unittest.main()
