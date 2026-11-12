"""Local, read-only filesystem index for Scout.

No file contents are read. Paths remain on this Mac. The index lives outside the Git
checkout and contains private metadata, so it must never be committed or uploaded.
"""
from __future__ import annotations

import os
import re
import sqlite3
import stat
import subprocess
import threading
import time
from pathlib import Path


HOME = Path.home().resolve()
DATA_DIR = HOME / "Library" / "Application Support" / "Scout"
DB_PATH = DATA_DIR / "scout.sqlite3"
MAX_PAGE = 300
RF2_DIR = Path(__file__).resolve().parent.parent / "rf2" / "bin" / "scout-dir"
_JOB_LOCK = threading.Lock()
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY: Path | None = None
_JOB = {"running": False, "scope": None, "seen": 0, "started": None,
        "ended": None, "error": None, "generation": None}


def safe_path(raw: str) -> Path:
    """Resolve one HOME-relative path without following symlinks or escaping HOME."""
    if not isinstance(raw, str) or len(raw) > 4096 or "\x00" in raw:
        raise ValueError("Invalid path")
    relative = Path(raw or ".")
    if relative.is_absolute() or any(part in ("..", "") for part in relative.parts):
        raise ValueError("Choose a path inside your home folder")
    candidate = HOME / relative
    current = HOME
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Scout does not follow symbolic links")
    try:
        candidate.relative_to(HOME)
    except ValueError as exc:
        raise ValueError("Path is outside your home folder") from exc
    return candidate


def relative(path: Path) -> str:
    value = str(path.relative_to(HOME))
    return "" if value == "." else value


def _entry(path: Path, st: os.stat_result | None = None) -> dict:
    st = st or path.lstat()
    kind = "link" if stat.S_ISLNK(st.st_mode) else "folder" if stat.S_ISDIR(st.st_mode) else "file"
    return {"name": path.name or HOME.name, "path": relative(path),
            "kind": kind, "bytes": st.st_size if kind == "file" else None,
            "allocated": st.st_blocks * 512 if kind == "file" else None,
            "modified": st.st_mtime_ns // 1_000_000,
            "hidden": path.name.startswith(".")}


def list_folder(raw: str = "", offset: int = 0, limit: int = 120,
                sort_by: str = "name", descending: bool = False,
                kind: str = "all", hidden: bool = False) -> dict:
    path = safe_path(raw)
    if not path.is_dir():
        raise ValueError("This location is not a folder")
    limit = min(max(int(limit), 1), MAX_PAGE)
    offset = max(int(offset), 0)
    entries = []
    engine = "python"
    engine_error = None
    names = None
    if RF2_DIR.is_file() and os.access(RF2_DIR, os.X_OK):
        try:
            result = subprocess.run([str(RF2_DIR), str(path)], capture_output=True,
                                    timeout=8, check=True)
            names = [os.fsdecode(name) for name in result.stdout.split(b"\0")
                     if name and name not in (b".", b"..")]
            if any(name in (".", "..") or "/" in name or "\x00" in name for name in names):
                raise ValueError("Invalid native directory entry")
            engine = "rf2-native"
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            engine_error = str(exc)
            names = None
            engine = "python-fallback"
    if names is not None:
        for name in names:
            try:
                entries.append(_entry(path / name))
            except (OSError, PermissionError):
                pass
    else:
        with os.scandir(path) as iterator:
            for item in iterator:
                try:
                    entries.append(_entry(Path(item.path), item.stat(follow_symlinks=False)))
                except (OSError, PermissionError):
                    pass
    if not hidden:
        entries = [item for item in entries if not item["hidden"]]
    if kind in ("file", "folder", "link"):
        entries = [item for item in entries if item["kind"] == kind]
    try:
        db = connect()
        totals = {row["path"]: row["tree_allocated"] for row in
                  db.execute("SELECT path,tree_allocated FROM nodes WHERE parent=? AND kind='folder'", (relative(path),))}
        db.close()
        for item in entries:
            if item["kind"] == "folder" and item["path"] in totals:
                item["allocated"] = totals[item["path"]]
                item["indexedSize"] = totals[item["path"]] is not None
    except sqlite3.Error:
        pass
    if sort_by == "size":
        entries.sort(key=lambda item: item["allocated"] if item["allocated"] is not None else -1,
                     reverse=descending)
    elif sort_by == "modified":
        entries.sort(key=lambda item: item["modified"], reverse=descending)
    else:
        entries.sort(key=lambda item: (item["kind"] != "folder", item["name"].casefold()), reverse=descending)
    return {"path": relative(path), "name": path.name, "total": len(entries),
            "engine": engine, "engineError": engine_error,
            "offset": offset, "limit": limit, "sort": sort_by, "descending": descending,
            "entries": entries[offset:offset + limit]}


def stat_path(raw: str) -> dict:
    path = safe_path(raw)
    item = _entry(path)
    item["parent"] = relative(path.parent) if path != HOME else ""
    item["readable"] = os.access(path, os.R_OK)
    return item


def capacity() -> dict:
    st = os.statvfs(HOME)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return {"total": total, "used": total - free, "free": free,
            "measuredAt": int(time.time() * 1000)}


def connect() -> sqlite3.Connection:
    global _SCHEMA_READY
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    if _SCHEMA_READY == DB_PATH:
        return db
    with _SCHEMA_LOCK:
        if _SCHEMA_READY == DB_PATH:
            return db
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS nodes (
          id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL, parent TEXT NOT NULL, kind TEXT NOT NULL,
          bytes INTEGER, allocated INTEGER, tree_allocated INTEGER, modified INTEGER,
          generation INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS nodes_parent ON nodes(parent);
        CREATE INDEX IF NOT EXISTS nodes_name ON nodes(name COLLATE NOCASE);
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
          name, path, content='nodes', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
          INSERT INTO nodes_fts(rowid,name,path) VALUES(new.id,new.name,new.path);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
          INSERT INTO nodes_fts(nodes_fts,rowid,name,path)
          VALUES('delete',old.id,old.name,old.path);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
          INSERT INTO nodes_fts(nodes_fts,rowid,name,path)
          VALUES('delete',old.id,old.name,old.path);
          INSERT INTO nodes_fts(rowid,name,path) VALUES(new.id,new.name,new.path);
        END;
        """)
        _SCHEMA_READY = DB_PATH
    return db


def _index_worker(scope: str, generation: int) -> None:
    db = None
    try:
        root = safe_path(scope)
        if not root.is_dir():
            raise ValueError("Select a folder to index")
        db = connect()
        stack = [root]
        batch = []
        totals = {}
        root_item = _entry(root)
        db.execute("""INSERT INTO nodes(path,name,parent,kind,bytes,allocated,tree_allocated,modified,generation)
            VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET generation=excluded.generation""",
            (relative(root), root_item["name"], relative(root.parent) if root != HOME else "",
             "folder", None, None, None, root_item["modified"], generation))
        db.commit()
        while stack:
            folder = stack.pop()
            try:
                with os.scandir(folder) as iterator:
                    children = list(iterator)
            except (OSError, PermissionError):
                continue
            for child in children:
                try:
                    st = child.stat(follow_symlinks=False)
                    p = Path(child.path)
                    item = _entry(p, st)
                    batch.append((item["path"], item["name"], relative(folder),
                                  item["kind"], item["bytes"], item["allocated"], None,
                                  item["modified"], generation))
                    if item["kind"] == "folder":
                        stack.append(p)
                    elif item["kind"] == "file":
                        ancestor = folder
                        while ancestor == root or root in ancestor.parents:
                            key = relative(ancestor)
                            totals[key] = totals.get(key, 0) + (item["allocated"] or 0)
                            ancestor = ancestor.parent
                except (OSError, PermissionError, ValueError):
                    continue
            if len(batch) >= 500 or not stack:
                db.executemany("""INSERT INTO nodes(path,name,parent,kind,bytes,allocated,tree_allocated,modified,generation)
                    VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,parent=excluded.parent,kind=excluded.kind,
                    bytes=excluded.bytes,allocated=excluded.allocated,tree_allocated=excluded.tree_allocated,
                    modified=excluded.modified,generation=excluded.generation""", batch)
                db.commit()
                with _JOB_LOCK:
                    _JOB["seen"] += len(batch)
                batch.clear()
        # Prune only the selected subtree after its replacement scan completed.
        db.execute("UPDATE nodes SET tree_allocated=0 WHERE generation=? AND kind='folder'", (generation,))
        db.executemany("UPDATE nodes SET tree_allocated=? WHERE path=? AND kind='folder'",
                       ((value, key) for key, value in totals.items()))
        if scope:
            prefix = scope.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            db.execute("DELETE FROM nodes WHERE (path=? OR path LIKE ? ESCAPE '\\') AND generation<>?",
                       (scope, prefix + "/%", generation))
        else:
            db.execute("DELETE FROM nodes WHERE generation<>?", (generation,))
        db.commit()
    except Exception as exc:
        with _JOB_LOCK:
            _JOB["error"] = str(exc)
    finally:
        if db:
            db.close()
        with _JOB_LOCK:
            _JOB["running"] = False
            _JOB["ended"] = int(time.time() * 1000)


def start_index(scope: str) -> dict:
    global _JOB
    path = safe_path(scope)
    if not path.is_dir():
        raise ValueError("Select a folder to index")
    with _JOB_LOCK:
        if _JOB["running"]:
            return dict(_JOB)
        generation = int(time.time_ns())
        _JOB = {"running": True, "scope": relative(path), "seen": 0,
                "started": int(time.time() * 1000), "ended": None,
                "error": None, "generation": generation}
        worker = threading.Thread(target=_index_worker, args=(relative(path), generation), daemon=True)
        worker.start()
    return index_status()


def index_status() -> dict:
    with _JOB_LOCK:
        job = dict(_JOB)
    try:
        db = connect()
        row = db.execute("SELECT COUNT(*) AS count, COALESCE(SUM(allocated),0) AS bytes FROM nodes").fetchone()
        db.close()
        job.update({"indexed": row["count"], "indexedAllocated": row["bytes"]})
    except sqlite3.Error as exc:
        job["error"] = str(exc)
    return job


def search(query: str, limit: int = 60) -> dict:
    words = re.findall(r"[\w-]+", query, re.UNICODE)
    if not words or len(query) < 2:
        return {"query": query, "results": [], "coverage": index_status()}
    expression = " ".join('"' + word.replace('"', '') + '"*' for word in words[:6])
    db = connect()
    try:
        rows = db.execute("""SELECT n.path,n.name,n.parent,n.kind,n.bytes,n.allocated,n.modified
            FROM nodes_fts f JOIN nodes n ON n.id=f.rowid
            WHERE nodes_fts MATCH ? ORDER BY bm25(nodes_fts) LIMIT ?""",
            (expression, min(max(limit, 1), 100))).fetchall()
        return {"query": query, "results": [dict(row) for row in rows],
                "coverage": index_status()}
    finally:
        db.close()
