import tempfile
import time
import unittest
from pathlib import Path

from scout import core, mcp


class ScoutCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = (core.HOME, core.DATA_DIR, core.DB_PATH)
        core.HOME = self.root
        core.DATA_DIR = self.root / "private-index"
        core.DB_PATH = core.DATA_DIR / "index.sqlite3"
        (self.root / "project" / "docs").mkdir(parents=True)
        (self.root / "project" / "docs" / "report.txt").write_text("private test content")
        (self.root / "project" / "photo.png").write_bytes(b"\x89PNG\r\n")
        (self.root / "project" / "outside").symlink_to(Path("/etc"))

    def tearDown(self):
        core.HOME, core.DATA_DIR, core.DB_PATH = self.original
        self.temp.cleanup()

    def test_navigation_rejects_escape_and_symlink(self):
        names = [row["name"] for row in core.list_folder("project")["entries"]]
        self.assertIn("docs", names)
        self.assertIn("outside", names)
        for path in ("../etc", "/etc", "project/outside/passwd"):
            with self.assertRaises(ValueError):
                core.safe_path(path)

    def test_index_search_and_folder_size(self):
        core.start_index("project")
        for _ in range(100):
            status = core.index_status()
            if status["ended"] is not None and not status["running"]:
                break
            time.sleep(.02)
        self.assertIsNone(status["error"])
        self.assertGreaterEqual(status["indexed"], 4)
        found = core.search("report")["results"]
        self.assertEqual(found[0]["path"], "project/docs/report.txt")
        docs = next(row for row in core.list_folder("project")["entries"] if row["name"] == "docs")
        self.assertTrue(docs["indexedSize"])
        self.assertGreaterEqual(docs["allocated"], 0)
        self.assertNotIn("private test content", str(found))
        (self.root / "project" / "docs" / "report.txt").unlink()
        previous_generation = status["generation"]
        core.start_index("project")
        for _ in range(100):
            status = core.index_status()
            if status["ended"] is not None and not status["running"] and status["generation"] != previous_generation:
                break
            time.sleep(.02)
        self.assertEqual(core.search("report")["results"], [])

    def test_mcp_metadata_only(self):
        response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "scout_list", "arguments": {"path": "project"}}})
        self.assertFalse(response["result"]["isError"])
        self.assertNotIn("private test content", str(response))
        self.assertEqual(mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"][0]["name"], "scout_list")


if __name__ == "__main__":
    unittest.main()
