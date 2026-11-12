"""Scout local desktop web service. No network listener, uploads, or file writes."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import core


PORT = int(os.environ.get("SCOUT_PORT", "8766"))
ASSETS = Path(__file__).resolve().parent.parent / "assets"
SESSION = secrets.token_urlsafe(24)
SAMPLES = deque(maxlen=120)
SAMPLE_LOCK = threading.Lock()


def sample_disk() -> None:
    while True:
        try:
            proc = subprocess.run(
                ["/usr/sbin/iostat", "-d", "-w", "1", "-c", "2", "disk0"],
                capture_output=True, text=True, timeout=4, check=True)
            values = [line.split() for line in proc.stdout.splitlines() if line.strip()]
            mbps = float(values[-1][2]) if len(values[-1]) == 3 else None
            sample = {"at": int(time.time() * 1000), "mbps": mbps,
                      "source": "iostat internal disk0; total read + write"}
        except (OSError, ValueError, subprocess.SubprocessError, IndexError) as exc:
            sample = {"at": int(time.time() * 1000), "mbps": None,
                      "error": str(exc), "source": "iostat unavailable"}
        with SAMPLE_LOCK:
            SAMPLES.append(sample)
        time.sleep(2)


def codex_handles() -> dict:
    """On-demand open handles, not evidence of active reads or writes."""
    proc = subprocess.run(["/usr/sbin/lsof", "-nP", "-Fpcfn", "-c", "Codex"],
                          capture_output=True, text=True, timeout=8)
    pid = name = fd = ""
    rows = []
    seen = set()
    for line in proc.stdout.splitlines():
        if not line:
            continue
        key, value = line[0], line[1:]
        if key == "p":
            pid, name, fd = value, "", ""
        elif key == "c":
            name = value
        elif key == "f":
            fd = value
        elif key == "n" and value.startswith(str(core.HOME) + "/") \
                and fd[:1].isdigit() and value not in seen:
            seen.add(value)
            rows.append({"process": name or pid,
                         "path": value[len(str(core.HOME)) + 1:]})
    return {"at": int(time.time() * 1000), "count": len(rows),
            "entries": rows[:80], "meaning": "Open handles only; not confirmed reads"}


class Handler(BaseHTTPRequestHandler):
    server_version = "Scout/0.2"

    def _allowed(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0]
        origin = self.headers.get("Origin")
        return host in ("127.0.0.1", "localhost") and (
            not origin or origin in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"))

    def _send(self, payload: bytes, mime: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, value: dict, status: int = 200) -> None:
        self._send(json.dumps(value, separators=(",", ":")).encode(), "application/json", status)

    def do_GET(self) -> None:
        if not self._allowed():
            return self._json({"error": "Local access only"}, 403)
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/overview":
                return self._json({"capacity": core.capacity(), "home": str(core.HOME),
                                   "index": core.index_status(), "session": SESSION})
            if parsed.path == "/api/list":
                return self._json(core.list_folder(query.get("path", [""])[0],
                                                   int(query.get("offset", [0])[0]),
                                                   int(query.get("limit", [120])[0]),
                                                   query.get("sort", ["name"])[0],
                                                   query.get("desc", ["0"])[0] == "1",
                                                   query.get("kind", ["all"])[0],
                                                   query.get("hidden", ["0"])[0] == "1"))
            if parsed.path == "/api/stat":
                return self._json(core.stat_path(query.get("path", [""])[0]))
            if parsed.path == "/api/search":
                return self._json(core.search(query.get("q", [""])[0]))
            if parsed.path == "/api/activity":
                with SAMPLE_LOCK:
                    return self._json({"samples": list(SAMPLES)})
            if parsed.path == "/api/handles":
                return self._json(codex_handles())
            if parsed.path in ("/", "/index.html"):
                asset, mime = "index.html", "text/html; charset=utf-8"
            elif parsed.path in ("/app.js", "/style.css", "/ssd.webp"):
                asset = parsed.path[1:]
                mime = {"app.js": "text/javascript; charset=utf-8",
                        "style.css": "text/css; charset=utf-8",
                        "ssd.webp": "image/webp"}[asset]
            else:
                return self._json({"error": "Not found"}, 404)
            return self._send((ASSETS / asset).read_bytes(), mime)
        except (ValueError, OSError) as exc:
            return self._json({"error": str(exc)}, 400)

    def do_POST(self) -> None:
        if not self._allowed() or self.headers.get("X-Scout-Session") != SESSION:
            return self._json({"error": "Local session required"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json({"error": "Invalid request length"}, 400)
        if length < 0 or length > 4096:
            return self._json({"error": "Request too large"}, 413)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/index":
                return self._json(core.start_index(body.get("path", "")), 202)
            if self.path == "/api/reveal":
                path = core.safe_path(body.get("path", ""))
                if not path.exists():
                    raise ValueError("File no longer exists")
                subprocess.Popen(["/usr/bin/open", "-R", str(path)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._json({"revealed": core.relative(path)})
            return self._json({"error": "Not found"}, 404)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            return self._json({"error": str(exc)}, 400)

    def log_message(self, *_args) -> None:
        pass


def main() -> None:
    threading.Thread(target=sample_disk, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
