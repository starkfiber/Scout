"""Local client for Scout's trusted RF² macOS directory and metadata service."""
from __future__ import annotations

import atexit
import os
import select
import subprocess
import threading
import time
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "rf2" / "bin" / "scout-dir-service"
_LOCKS = {"interactive": threading.Lock(), "index": threading.Lock()}
_PROCS: dict[str, subprocess.Popen] = {}
_MAX_BYTES = 64 * 1024 * 1024


def _stop_one(purpose: str) -> None:
    proc = _PROCS.pop(purpose, None)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)
    if proc is not None:
        if proc.stdin:
            proc.stdin.close()
        if proc.stdout:
            proc.stdout.close()


def _stop() -> None:
    for purpose in tuple(_PROCS):
        with _LOCKS[purpose]:
            _stop_one(purpose)


atexit.register(_stop)


def _read_exact(fd: int, length: int, deadline: float) -> bytes:
    data = bytearray()
    while len(data) < length:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError("RF² directory service timed out")
        chunk = os.read(fd, length - len(data))
        if not chunk:
            raise OSError("RF² directory service ended unexpectedly")
        data.extend(chunk)
    return bytes(data)


def _write_exact(fd: int, data: bytes) -> None:
    used = 0
    while used < len(data):
        count = os.write(fd, data[used:])
        if count <= 0:
            raise OSError("RF² directory service write failed")
        used += count


def _parse(chunk: bytes) -> list[dict]:
    records = []
    offset = 0
    while offset < len(chunk):
        if len(chunk) - offset < 32:
            raise ValueError("Short RF² directory record")
        length = int.from_bytes(chunk[offset:offset + 2], "little")
        if not length or offset + 32 + length > len(chunk):
            raise ValueError("Invalid RF² directory record")
        name = chunk[offset + 32:offset + 32 + length]
        if name not in (b".", b".."):
            if b"\x00" in name or b"/" in name:
                raise ValueError("Invalid RF² filename")
            records.append({"name": os.fsdecode(name),
                            "mode": int.from_bytes(chunk[offset + 2:offset + 4], "little"),
                            "bytes": int.from_bytes(chunk[offset + 4:offset + 12], "little"),
                            "blocks": int.from_bytes(chunk[offset + 12:offset + 20], "little"),
                            "mtimeSec": int.from_bytes(chunk[offset + 20:offset + 28], "little"),
                            "mtimeNs": int.from_bytes(chunk[offset + 28:offset + 32], "little")})
        offset += 32 + length
    return records


def list_records(path: Path, purpose: str = "interactive") -> list[dict]:
    """Enumerate a directory; UI and background index use separate RF² processes."""
    if purpose not in _LOCKS:
        raise ValueError("Invalid RF² client purpose")
    raw = os.fsencode(path)
    if not raw or len(raw) > 4095 or b"\x00" in raw:
        raise ValueError("Invalid RF² directory path")
    with _LOCKS[purpose]:
        try:
            proc = _PROCS.get(purpose)
            if proc is None or proc.poll() is not None:
                proc = subprocess.Popen([str(SERVICE)], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         bufsize=0, close_fds=True)
                _PROCS[purpose] = proc
            assert proc.stdin and proc.stdout
            _write_exact(proc.stdin.fileno(), len(raw).to_bytes(4, "little") + raw)
            deadline = time.monotonic() + 8
            output = []
            total = 0
            while True:
                size = int.from_bytes(_read_exact(proc.stdout.fileno(), 4, deadline), "little")
                if size == 0:
                    return output
                if size == 0xFFFFFFFF:
                    raise OSError("RF² could not open directory")
                if size > 131072 or total + size > _MAX_BYTES:
                    raise ValueError("RF² directory response exceeds limit")
                output.extend(_parse(_read_exact(proc.stdout.fileno(), size, deadline)))
                total += size
        except Exception:
            _stop_one(purpose)
            raise
