import queue
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yt_dlp
from yt_dlp.utils import DownloadCancelled

from src import downloader
from src.downloader import (
    CancelledEvent,
    DoneEvent,
    DownloadJob,
    DownloadRequest,
    ErrorEvent,
    ProgressEvent,
    RetryEvent,
    SuccessEvent,
    VideoInfo,
    WarningEvent,
)

FAKE_BINS = {"ffmpeg": r"C:\fake\bin\ffmpeg.exe", "ffprobe": r"C:\fake\bin\ffprobe.exe", "deno": r"C:\fake\bin\deno.exe"}
URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def drain(q: queue.Queue) -> list:
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    return items


def fake_ydl(results, captured_opts=None):
    """Factory for a fake YoutubeDL whose extract_info pops from `results`."""

    def factory(opts):
        if captured_opts is not None:
            captured_opts.append(opts)

        class DummyYDL:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def _next(self):
                result = results.pop(0)
                if callable(result):
                    result = result(opts)
                if isinstance(result, BaseException):
                    raise result
                return result

            def add_post_processor(self, pp, when="post_process"):
                self.spy = pp

            def extract_info(self, _url, download=True, process=True):
                return self._next()

            def process_ie_result(self, _info, download=True):
                return self._next()

        return DummyYDL()

    return factory


class TestValidateUrl(unittest.TestCase):
    def test_accepts_youtube_variants(self):
        for url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123",
            "youtube.com/watch?v=dQw4w9WgXcQ",
        ):
            self.assertTrue(downloader.validate_url(url), url)

    def test_rejects_others(self):
        for url in (
            "https://vimeo.com/123",
            "not a url",
            "",
            "https://youtube.com.evil.com/watch?v=x",
            "https://www.youtube.com/",
            "ftp://youtube.com/watch?v=x",
        ):
            self.assertFalse(downloader.validate_url(url), url)


class TestClassifyError(unittest.TestCase):
    def test_categories(self):
        cases = {
            "HTTP Error 429: Too Many Requests": (False, "muitas requisições"),
            "Private video": (False, "vídeo privado"),
            "This video is not available in your country": (False, "restrição geográfica"),
            "HTTP Error 503: Service Unavailable": (True, "erro do servidor"),
            "timed out": (True, "falha de rede"),
            "[SSL: CERTIFICATE_VERIFY_FAILED]": (True, "falha de rede"),
            "Sign in to confirm you're not a bot": (False, "verificação anti-robô"),
            "ERROR: Postprocessing: Unable to embed using ffprobe & ffmpeg": (False, "thumbnail"),
            "Requested format is not available": (False, "formato indisponível"),
            "something weird": (False, "erro desconhecido"),
        }
        for text, (retryable, reason) in cases.items():
            _, r, why = downloader.classify_error(text)
            self.assertEqual((r, why), (retryable, reason), text)

    def test_tls_is_not_substring_match(self):
        # "settlement" contains "tl" letters but must not be classified as TLS.
        _, retryable, _ = downloader.classify_error("unexpected settlements error")
        self.assertFalse(retryable)


class TestBuildOptions(unittest.TestCase):
    def test_video_defaults(self):
        req = DownloadRequest(URL, "video", Path("C:/tmp"))
        opts = downloader.build_options(req, bins=FAKE_BINS)
        self.assertTrue(opts["noplaylist"])
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertEqual(opts["format_sort"][0], "res")
        self.assertIn("vcodec:h264", opts["format_sort"])
        self.assertEqual(opts["js_runtimes"], {"deno": {"path": FAKE_BINS["deno"]}})
        self.assertEqual(Path(opts["ffmpeg_location"]), Path(r"C:\fake\bin"))
        keys = [pp["key"] for pp in opts["postprocessors"]]
        self.assertEqual(keys, ["FFmpegMetadata", "EmbedThumbnail"])

    def test_video_quality_cap(self):
        req = DownloadRequest(URL, "video", Path("C:/tmp"), max_height=720)
        opts = downloader.build_options(req, bins=FAKE_BINS)
        self.assertEqual(opts["format_sort"][0], "res:720")

    def test_audio_mp3(self):
        req = DownloadRequest(URL, "audio", Path("C:/tmp"), audio_codec="mp3", audio_bitrate=320)
        opts = downloader.build_options(req, bins=FAKE_BINS)
        pp = opts["postprocessors"]
        self.assertEqual([p["key"] for p in pp], ["FFmpegExtractAudio", "FFmpegMetadata", "EmbedThumbnail"])
        self.assertEqual(pp[0]["preferredcodec"], "mp3")
        self.assertEqual(pp[0]["preferredquality"], "320")

    def test_audio_m4a_no_reencode(self):
        req = DownloadRequest(URL, "audio", Path("C:/tmp"), audio_codec="m4a", audio_bitrate=None)
        opts = downloader.build_options(req, bins=FAKE_BINS)
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "m4a")
        self.assertNotIn("preferredquality", opts["postprocessors"][0])

    def test_without_optional_binaries(self):
        req = DownloadRequest(URL, "video", Path("C:/tmp"))
        opts = downloader.build_options(req, bins={"ffmpeg": None, "ffprobe": None, "deno": None})
        self.assertNotIn("js_runtimes", opts)
        self.assertNotIn("ffmpeg_location", opts)


class TestProgressTracker(unittest.TestCase):
    def _info(self, current):
        return {
            "format_id": current,
            "vcodec": "avc1" if current == "137" else "none",
            "requested_formats": [
                {"format_id": "137", "filesize": 900},
                {"format_id": "140", "filesize": 100},
            ],
        }

    def test_overall_progress_is_monotonic_across_streams(self):
        t = downloader._ProgressTracker("video")
        e1 = t.to_event({"status": "downloading", "downloaded_bytes": 450, "total_bytes": 900,
                         "info_dict": self._info("137")}, force=True)
        e2 = t.to_event({"status": "finished", "info_dict": self._info("137")}, force=True)
        e3 = t.to_event({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100,
                         "info_dict": self._info("140")}, force=True)
        self.assertAlmostEqual(e1.fraction, 0.45)
        self.assertAlmostEqual(e2.fraction, 0.90)
        self.assertAlmostEqual(e3.fraction, 0.95)
        self.assertEqual(e1.stage, "Baixando vídeo (1/2)")
        self.assertEqual(e3.stage, "Baixando áudio (2/2)")

    def test_unknown_total_does_not_crash(self):
        t = downloader._ProgressTracker("audio")
        e = t.to_event({"status": "downloading", "downloaded_bytes": 10, "total_bytes": None,
                        "total_bytes_estimate": None, "info_dict": {}}, force=True)
        self.assertIsNone(e.fraction)

    def test_throttle(self):
        t = downloader._ProgressTracker("audio")
        d = {"status": "downloading", "downloaded_bytes": 1, "total_bytes": 10, "info_dict": {}}
        self.assertIsNotNone(t.to_event(d))
        self.assertIsNone(t.to_event(d))  # within throttle window

    def test_only_files_being_written_are_tracked(self):
        t = downloader._ProgressTracker("audio")
        t.to_event({"status": "finished", "filename": "existing.mp3", "info_dict": {}}, force=True)
        self.assertEqual(t.touched_files, set())
        t.to_event({"status": "downloading", "filename": "new.webm", "tmpfilename": "new.webm.part",
                    "info_dict": {}}, force=True)
        self.assertEqual(t.touched_files, {"new.webm", "new.webm.part"})


class TestDownloadJob(unittest.TestCase):
    def _run(self, results, **kwargs):
        q = queue.Queue()
        req = kwargs.pop("request", DownloadRequest(URL, "audio", Path("C:/tmp")))
        job = DownloadJob(req, q, bins=FAKE_BINS, base_delay=0, **kwargs)
        with mock.patch("src.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl(results)):
            job._run_safe()
        return job, drain(q)

    def test_retries_network_errors_then_succeeds(self):
        _, events = self._run([
            yt_dlp.utils.DownloadError("timed out"),
            yt_dlp.utils.DownloadError("HTTP Error 503"),
            {"title": "ok", "requested_downloads": [{"filepath": "C:/tmp/ok.mp3"}]},
        ])
        self.assertEqual(sum(isinstance(e, RetryEvent) for e in events), 2)
        success = [e for e in events if isinstance(e, SuccessEvent)]
        self.assertEqual(success[0].title, "ok")
        self.assertEqual(success[0].filepath, "C:/tmp/ok.mp3")
        self.assertIsInstance(events[-1], DoneEvent)

    def test_non_retryable_error(self):
        _, events = self._run([yt_dlp.utils.DownloadError("Private video")])
        self.assertFalse(any(isinstance(e, RetryEvent) for e in events))
        self.assertEqual(sum(isinstance(e, ErrorEvent) for e in events), 1)
        self.assertIsInstance(events[-1], DoneEvent)

    def test_retries_exhausted(self):
        _, events = self._run([yt_dlp.utils.DownloadError("timed out")] * 3)
        errors = [e for e in events if isinstance(e, ErrorEvent)]
        self.assertIn("Tentativas esgotadas", errors[0].message)

    def test_thumbnail_failure_is_success_with_warning(self):
        info = VideoInfo(URL, "id", "Meu vídeo", "", None, None, raw={"id": "id"})
        _, events = self._run(
            [yt_dlp.utils.DownloadError("Unable to embed using ffprobe & ffmpeg")], info=info
        )
        self.assertTrue(any(isinstance(e, WarningEvent) for e in events))
        success = [e for e in events if isinstance(e, SuccessEvent)]
        self.assertEqual(success[0].title, "Meu vídeo")

    def test_reuses_fresh_preview(self):
        info = VideoInfo(URL, "id", "t", "", None, None, raw={"id": "id"})
        q = queue.Queue()
        job = DownloadJob(DownloadRequest(URL, "audio", Path("C:/tmp")), q, info=info, bins=FAKE_BINS)
        ydl = mock.MagicMock()
        ydl.__enter__.return_value = ydl
        ydl.process_ie_result.return_value = {"title": "t"}
        with mock.patch("src.downloader.yt_dlp.YoutubeDL", return_value=ydl):
            job._run_safe()
        ydl.process_ie_result.assert_called_once()
        ydl.extract_info.assert_not_called()

    def test_preview_for_other_url_is_ignored(self):
        info = VideoInfo("https://youtu.be/other", "x", "t", "", None, None, raw={})
        job = DownloadJob(DownloadRequest(URL), queue.Queue(), info=info, bins=FAKE_BINS)
        self.assertIsNone(job.info)

    def test_missing_ffmpeg(self):
        q = queue.Queue()
        job = DownloadJob(DownloadRequest(URL), q, bins={"ffmpeg": None, "ffprobe": None, "deno": None})
        job._run_safe()
        events = drain(q)
        self.assertIsInstance(events[0], ErrorEvent)
        self.assertIn("FFmpeg", events[0].message)

    def test_cancel_cleans_partial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            part = Path(tmp) / "video.f137.mp4.part"
            part.write_bytes(b"x")
            frag = Path(tmp) / "video.f137.mp4.part-Frag4.part"
            frag.write_bytes(b"x")
            thumb = Path(tmp) / "video.webp"
            thumb.write_bytes(b"x")
            q = queue.Queue()
            job = DownloadJob(DownloadRequest(URL, "video", Path(tmp)), q, bins=FAKE_BINS)

            def downloading_then_cancel(opts):
                hook = opts["progress_hooks"][0]
                hook({"status": "downloading", "tmpfilename": str(part), "filename": str(part)[:-5],
                      "downloaded_bytes": 1, "total_bytes": 10, "info_dict": {}})
                job.cancel()
                hook({"status": "downloading", "downloaded_bytes": 2, "total_bytes": 10, "info_dict": {}})
                return {"title": "never"}

            with mock.patch("src.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl([downloading_then_cancel])):
                job._run_safe()

            events = drain(q)
            self.assertTrue(any(isinstance(e, CancelledEvent) for e in events))
            self.assertFalse(any(isinstance(e, SuccessEvent) for e in events))
            self.assertFalse(part.exists())
            self.assertFalse(frag.exists())
            self.assertFalse(thumb.exists())

    def test_cancel_during_retry_wait(self):
        q = queue.Queue()
        job = DownloadJob(DownloadRequest(URL), q, bins=FAKE_BINS, base_delay=30)
        job.cancel()
        with mock.patch("src.downloader.yt_dlp.YoutubeDL",
                        side_effect=fake_ydl([yt_dlp.utils.DownloadError("timed out")])):
            job._run_safe()
        events = drain(q)
        self.assertTrue(any(isinstance(e, CancelledEvent) for e in events))

    def test_progress_events_reach_queue(self):
        def with_progress(opts):
            opts["progress_hooks"][0]({"status": "downloading", "downloaded_bytes": 5,
                                       "total_bytes": 10, "info_dict": {}})
            return {"title": "ok"}

        _, events = self._run([with_progress])
        progress = [e for e in events if isinstance(e, ProgressEvent)]
        self.assertAlmostEqual(progress[0].fraction, 0.5)

    def test_hook_raises_cancel_type(self):
        job = DownloadJob(DownloadRequest(URL), queue.Queue(), bins=FAKE_BINS)
        job.cancel()
        with self.assertRaises(DownloadCancelled):
            job._progress_hook({"status": "downloading"})


class TestCleanup(unittest.TestCase):
    def test_base_name(self):
        self.assertEqual(downloader._base_name("My.Title.f625.mp4.part"), "My.Title")
        self.assertEqual(downloader._base_name("My.Title.webm.part"), "My.Title")
        self.assertEqual(downloader._base_name("Song.webm"), "Song")

    def test_keeps_finished_and_unrelated_and_old_files(self):
        import os, time
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            part = d / "Song.webm.part"; part.write_bytes(b"x")
            final = d / "Song.mp3"; final.write_bytes(b"x")          # completed earlier output
            other = d / "Other.webm.part"; other.write_bytes(b"x")  # another download
            old_thumb = d / "Song.jpg"; old_thumb.write_bytes(b"x")
            past = time.time() - 3600
            os.utime(old_thumb, (past, past))
            downloader.cleanup_partial_files([str(part)], since=time.time() - 60, wait=0)
            self.assertFalse(part.exists())
            self.assertTrue(final.exists())
            self.assertTrue(other.exists())
            self.assertTrue(old_thumb.exists())


class TestFormatSpy(unittest.TestCase):
    def test_spy_feeds_tracker(self):
        t = downloader._ProgressTracker("video")
        spy = downloader._FormatSpy(t)
        spy.run({"requested_formats": [{"format_id": "137", "filesize": 900},
                                        {"format_id": "140", "filesize": 100}]})
        e = t.to_event({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100,
                        "info_dict": {"format_id": "140", "vcodec": "none"}}, force=True)
        self.assertEqual(e.stage, "Baixando áudio (2/2)")
        self.assertAlmostEqual(e.fraction, 0.95)


class TestFetchInfo(unittest.TestCase):
    def test_follows_url_redirect_and_builds_info(self):
        results = [
            {"_type": "url", "url": URL},
            {"id": "dQw4w9WgXcQ", "title": "Song", "uploader": "Rick", "duration": 212,
             "extractor": "youtube"},
        ]
        with mock.patch("src.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl(results)):
            info = downloader.fetch_info(URL, bins=FAKE_BINS)
        self.assertEqual(info.title, "Song")
        self.assertEqual(info.thumbnail_url, "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg")

    def test_playlist_rejected(self):
        with mock.patch("src.downloader.yt_dlp.YoutubeDL",
                        side_effect=fake_ydl([{"_type": "playlist", "title": "pl"}])):
            with self.assertRaises(downloader.PlaylistNotSupported):
                downloader.fetch_info(URL, bins=FAKE_BINS)


if __name__ == "__main__":
    unittest.main()
