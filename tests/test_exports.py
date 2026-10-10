import json
import unittest
from io import BytesIO
from zipfile import ZipFile

from utils.exports import build_downloads, export_filename


class ResultDownloadsTests(unittest.TestCase):
    def setUp(self):
        self.result = {
            "title": "Planning / बैठक 🎬",
            "summary": "First line\nSecond line <details> & notes",
            "action_items": "- Priya: send the draft by Friday",
            "key_decisions": "Launch next week.",
            "open_questions": "Who will approve?",
            "transcript": "नमस्ते — welcome!\nFull transcript.",
            "rag_chain": object(),
        }

    def test_zip_round_trip_preserves_all_results_without_runtime_objects(self):
        downloads = build_downloads(self.result, [])
        with ZipFile(BytesIO(downloads["all_results.zip"])) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), set(downloads) - {"all_results.zip"})
            exported = json.loads(archive.read("results.json"))
            self.assertNotIn("rag_chain", exported)
            for key, content in self.result.items():
                if key == "rag_chain":
                    continue
                self.assertEqual(exported[key], content)
                self.assertIn(content, archive.read("report.txt").decode("utf-8"))
                self.assertIn(content, archive.read("report.md").decode("utf-8"))
                if key != "title":
                    self.assertEqual(archive.read(f"{key}.txt").decode("utf-8"), content)

    def test_chat_downloads_follow_current_history_and_clear(self):
        history = [{"role": "user", "content": "कब?"}, {"role": "assistant", "content": "Friday."}]
        downloads = build_downloads(self.result, history)
        self.assertEqual(json.loads(downloads["results.json"])["chat_history"], history)
        self.assertIn("You:\nकब?\n\nAssistant:\nFriday.", downloads["chat.txt"].decode("utf-8"))
        self.assertIn("Friday.", downloads["report.md"].decode("utf-8"))
        cleared = build_downloads(self.result, [])
        self.assertNotIn("chat.txt", cleared)
        self.assertEqual(json.loads(cleared["results.json"])["chat_history"], [])

    def test_windows_safe_bounded_filenames(self):
        for title in ["../../CON", "NUL", 'a<>:"/\\|?*b', "a" * 300, "🎬", ""]:
            with self.subTest(title=title):
                stem = export_filename(title)
                self.assertTrue(stem.startswith("meeting_"))
                self.assertLessEqual(len(stem), 88)
                self.assertNotRegex(stem, r'[<>:"/\\|?*.]')


if __name__ == "__main__":
    unittest.main()
