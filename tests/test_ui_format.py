import unittest

from src.ui_format import human_bytes, human_duration, progress_details, shorten_middle


class TestUiFormat(unittest.TestCase):
    def test_human_bytes(self):
        self.assertEqual(human_bytes(512), "512 B")
        self.assertEqual(human_bytes(1536), "1,5 KB")
        self.assertEqual(human_bytes(5 * 1024 ** 3), "5,0 GB")
        self.assertEqual(human_bytes(None), "?")

    def test_human_duration(self):
        self.assertEqual(human_duration(5), "0:05")
        self.assertEqual(human_duration(213), "3:33")
        self.assertEqual(human_duration(3725), "1:02:05")
        self.assertEqual(human_duration(None), "")

    def test_progress_details(self):
        text = progress_details(1024 * 1024, 10 * 1024 * 1024, 2 * 1024 * 1024, 4)
        self.assertEqual(text, "1,0 MB de 10,0 MB  ·  2,0 MB/s  ·  0:04 restantes")
        self.assertEqual(progress_details(0, None, None, None), "")

    def test_shorten_middle(self):
        self.assertEqual(shorten_middle("abc", 10), "abc")
        out = shorten_middle("C:/Users/someone/Very/Long/Folder/Name", 15)
        self.assertEqual(len(out), 15)
        self.assertIn("…", out)


if __name__ == "__main__":
    unittest.main()
