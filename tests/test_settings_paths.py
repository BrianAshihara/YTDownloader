import json
import tempfile
import unittest
from pathlib import Path

from src import paths
from src.constants import DEFAULT_AUDIO_FORMAT, DEFAULT_VIDEO_QUALITY
from src.settings import Settings, load_settings, save_settings


class TestSettings(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Settings(download_dir=tmp, mode="audio", video_quality="720p",
                         audio_format="M4A · original (sem perda)")
            save_settings(s, Path(tmp))
            loaded = load_settings(Path(tmp))
            self.assertEqual(loaded, s)

    def test_missing_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = load_settings(Path(tmp))
            self.assertEqual(s.mode, "video")
            self.assertEqual(s.video_quality, DEFAULT_VIDEO_QUALITY)

    def test_corrupt_or_invalid_values_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "settings.json").write_text(
                json.dumps({"mode": "banana", "audio_format": "WAV", "download_dir": "Z:/nope/x",
                            "unknown": 1}),
                encoding="utf-8",
            )
            s = load_settings(Path(tmp))
            self.assertEqual(s.mode, "video")
            self.assertEqual(s.audio_format, DEFAULT_AUDIO_FORMAT)
            self.assertTrue(Path(s.download_dir).is_dir())

            (Path(tmp) / "settings.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(load_settings(Path(tmp)).mode, "video")


class TestFindBinary(unittest.TestCase):
    def test_prefers_bundled_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / ("deno.exe" if paths.os.name == "nt" else "deno")
            exe.write_bytes(b"")
            self.assertEqual(paths.find_binary("deno", [Path(tmp)]), str(exe))

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(paths.find_binary("definitely-not-a-real-binary-xyz", [Path(tmp)]))


if __name__ == "__main__":
    unittest.main()
