import tempfile
import time
import unittest
import os
from pathlib import Path

from scout import core, mcp, rf2_native


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

    @unittest.skipUnless((core.RF2_DIR.is_file() and os.access(core.RF2_DIR, os.X_OK)) or
                         (rf2_native.SERVICE.is_file() and os.access(rf2_native.SERVICE, os.X_OK)),
                         "Build the RF2 directory helper first")
    def test_native_listing_matches_python_for_unusual_names(self):
        (self.root / "project" / "line\nbreak.txt").touch()
        (self.root / "project" / "café.txt").touch()
        native = core.list_folder("project", hidden=True)
        self.assertIn(native["engine"], ("rf2-native", "rf2-native-metadata"))
        native_names = [item["name"] for item in native["entries"]]
        previous = core.RF2_DIR
        previous_service = rf2_native.SERVICE
        try:
            core.RF2_DIR = self.root / "missing-native-program"
            rf2_native.SERVICE = self.root / "missing-native-service"
            python = core.list_folder("project", hidden=True)
        finally:
            core.RF2_DIR = previous
            rf2_native.SERVICE = previous_service
        self.assertEqual(native_names, [item["name"] for item in python["entries"]])
        for item in native["entries"]:
            expected = next(row for row in python["entries"] if row["name"] == item["name"])
            self.assertEqual((item["kind"], item["bytes"], item["allocated"]),
                             (expected["kind"], expected["bytes"], expected["allocated"]))
            self.assertEqual(item["modified"], expected["modified"])

    def test_native_failure_uses_visible_fallback(self):
        previous = core.RF2_DIR
        previous_service = rf2_native.SERVICE
        try:
            rf2_native._stop()
            rf2_native.SERVICE = Path("/usr/bin/false")
            result = core.list_folder("project")
        finally:
            core.RF2_DIR = previous
            rf2_native.SERVICE = previous_service
        self.assertEqual(result["engine"], "python-fallback")
        self.assertTrue(result["engineError"])
        self.assertIn("docs", [entry["name"] for entry in result["entries"]])

    @unittest.skipUnless(rf2_native.SERVICE.is_file() and os.access(rf2_native.SERVICE, os.X_OK),
                         "Build the RF2 directory service first")
    def test_native_large_directory_crosses_response_chunks(self):
        large = self.root / "project" / "many"
        large.mkdir()
        for i in range(1200):
            (large / f"file-{i:04}-sample.txt").touch()
        result = core.list_folder("project/many", limit=20)
        self.assertEqual(result["engine"], "rf2-native-metadata")
        self.assertEqual(result["total"], 1200)
        self.assertEqual(len(result["entries"]), 20)


if __name__ == "__main__":
    unittest.main()
