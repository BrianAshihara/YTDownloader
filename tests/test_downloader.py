import unittest
from pathlib import Path
from unittest import mock

import yt_dlp
from src import downloader


class TestDownloaderOptions(unittest.TestCase):
    def test_classify_error_specific(self):
        msg, retryable, reason = downloader.classify_error("HTTP Error 429: Too Many Requests")
        self.assertTrue(retryable)
        self.assertIn("429", msg)
        self.assertEqual(reason, "muitas requisições")

        msg, retryable, reason = downloader.classify_error("Private video")
        self.assertFalse(retryable)
        self.assertEqual(reason, "vídeo privado")

        msg, retryable, reason = downloader.classify_error("This video is not available in your country")
        self.assertFalse(retryable)
        self.assertEqual(reason, "restrição geográfica")

        msg, retryable, reason = downloader.classify_error("HTTP Error 503: Service Unavailable")
        self.assertTrue(retryable)
        self.assertEqual(reason, "erro do servidor")

        msg, retryable, reason = downloader.classify_error("timed out")
        self.assertTrue(retryable)
        self.assertEqual(reason, "falha de rede")

    def test_validate_url(self):
        self.assertTrue(downloader.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(downloader.validate_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(downloader.validate_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(downloader.validate_url("https://vimeo.com/123"))
        self.assertFalse(downloader.validate_url("not a url"))

    def test_build_options_video_embeds_metadata_and_thumbnail(self):
        opts = downloader.build_options("video", download_dir=Path("C:/tmp"))
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertIn("vcodec^=avc1", opts["format"])
        self.assertTrue(opts.get("writethumbnail"))

        postprocessors = opts.get("postprocessors", [])
        keys = [pp.get("key") for pp in postprocessors]
        self.assertEqual(keys[0], "FFmpegMetadata")
        self.assertEqual(keys[1], "EmbedThumbnail")

    def test_build_options_audio_embeds_metadata_and_thumbnail(self):
        opts = downloader.build_options("audio", download_dir=Path("C:/tmp"))
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertTrue(opts.get("writethumbnail"))

        postprocessors = opts.get("postprocessors", [])
        keys = [pp.get("key") for pp in postprocessors]
        self.assertEqual(keys[0], "FFmpegExtractAudio")
        self.assertEqual(keys[1], "FFmpegMetadata")
        self.assertEqual(keys[2], "EmbedThumbnail")

    def test_download_retries_and_succeeds(self):
        calls = {"retry": 0, "success": 0, "error": 0}
        errors = [
            yt_dlp.utils.DownloadError("HTTP Error 429: Too Many Requests"),
            yt_dlp.utils.DownloadError("HTTP Error 429: Too Many Requests"),
            {"title": "ok"},
        ]

        def ydl_factory(_opts):
            class DummyYDL:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def extract_info(self, _url, download=True):
                    result = errors.pop(0)
                    if isinstance(result, Exception):
                        raise result
                    return result

            return DummyYDL()

        def on_retry(_attempt, _max_attempts, _delay, _reason):
            calls["retry"] += 1

        def on_success(_title):
            calls["success"] += 1

        def on_error(_msg):
            calls["error"] += 1

        with mock.patch("src.downloader.yt_dlp.YoutubeDL", side_effect=ydl_factory):
            with mock.patch("src.downloader.time.sleep", return_value=None):
                downloader._download_with_retries(
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    download_type="audio",
                    on_success=on_success,
                    on_error=on_error,
                    on_retry=on_retry,
                    max_attempts=3,
                    base_delay=2,
                )

        self.assertEqual(calls["retry"], 2)
        self.assertEqual(calls["success"], 1)
        self.assertEqual(calls["error"], 0)

    def test_download_non_retryable_error(self):
        calls = {"retry": 0, "success": 0, "error": 0}
        errors = [yt_dlp.utils.DownloadError("Private video")]

        def ydl_factory(_opts):
            class DummyYDL:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def extract_info(self, _url, download=True):
                    result = errors.pop(0)
                    if isinstance(result, Exception):
                        raise result
                    return result

            return DummyYDL()

        def on_retry(_attempt, _max_attempts, _delay, _reason):
            calls["retry"] += 1

        def on_success(_title):
            calls["success"] += 1

        def on_error(_msg):
            calls["error"] += 1

        with mock.patch("src.downloader.yt_dlp.YoutubeDL", side_effect=ydl_factory):
            with mock.patch("src.downloader.time.sleep", return_value=None):
                downloader._download_with_retries(
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    download_type="audio",
                    on_success=on_success,
                    on_error=on_error,
                    on_retry=on_retry,
                    max_attempts=3,
                    base_delay=2,
                )

        self.assertEqual(calls["retry"], 0)
        self.assertEqual(calls["success"], 0)
        self.assertEqual(calls["error"], 1)


if __name__ == "__main__":
    unittest.main()
