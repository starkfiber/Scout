import http.client
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

from scout import server


class ScoutProtocolTests(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()

    def request(self, method, path, **kwargs):
        client = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=3)
        try:
            client.request(method, path, **kwargs)
            response = client.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            client.close()

    def test_assets_revalidate_and_api_stays_uncached(self):
        status, headers, body = self.request("GET", "/app.js")
        self.assertEqual(status, 200)
        self.assertTrue(body)
        self.assertEqual(headers["Cache-Control"], "private, no-cache")
        status, _, body = self.request("GET", "/app.js", headers={"If-None-Match": headers["ETag"]})
        self.assertEqual((status, body), (304, b""))
        self.assertEqual(self.request("GET", "/api/activity")[1]["Cache-Control"], "no-store")

    def test_invalid_request_shapes_return_json_and_listener_recovers(self):
        status, _, body = self.request("POST", "/api/index", body="[]",
                                       headers={"X-Scout-Session": server.SESSION})
        self.assertEqual(status, 400)
        self.assertIn("object", json.loads(body)["error"])
        status, _, _ = self.request("GET", "/api/list?" + "&".join(f"p{i}=1" for i in range(17)))
        self.assertEqual(status, 400)
        self.assertEqual(self.request("GET", "/api/activity")[0], 200)

    def test_mcp_discards_oversized_frame_and_accepts_next_frame(self):
        invalid = b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":[]}'
        ping = b'{"jsonrpc":"2.0","id":2,"method":"ping"}'
        result = subprocess.run([sys.executable, "-m", "scout.mcp"],
                                input=invalid + b"\n" + b"a" * (1048576 + 100) + b"\n" + ping + b"\n",
                                capture_output=True, timeout=5, check=True, env=os.environ.copy())
        error, success = map(json.loads, result.stdout.splitlines())
        self.assertTrue(error["result"]["isError"])
        self.assertEqual(success["result"], {})
