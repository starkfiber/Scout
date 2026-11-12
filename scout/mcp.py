"""Scout's local, read-only MCP server over newline-delimited JSON-RPC.

Launch with `python3 -m scout.mcp` from the Scout checkout. The server returns
metadata and paths only; it never returns file contents or mutates files.
"""
from __future__ import annotations

import json
import sys

from . import core


PROTOCOL = "2025-06-18"
TOOLS = [
    {"name": "scout_list", "description": "List immediate entries in one Mac home folder. Metadata only; no file contents.",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "Path relative to the user's home folder; empty for Home"},
         "offset": {"type": "integer", "minimum": 0},
         "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False}},
    {"name": "scout_find", "description": "Search paths already indexed by Scout. Results are partial until the chosen folders finish indexing.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "minLength": 2}}, "required": ["query"], "additionalProperties": False}},
    {"name": "scout_stat", "description": "Get current metadata for one file or folder inside the Mac home folder.",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
    {"name": "scout_capacity", "description": "Get current APFS volume total, used and available bytes.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
]


def dispatch(name: str, args: dict) -> dict:
    if name == "scout_list":
        return core.list_folder(args.get("path", ""), args.get("offset", 0),
                                min(args.get("limit", 100), 100))
    if name == "scout_find":
        return core.search(args.get("query", ""))
    if name == "scout_stat":
        return core.stat_path(args["path"])
    if name == "scout_capacity":
        return core.capacity()
    raise ValueError("Unknown Scout tool")


def handle(message: dict) -> dict | None:
    method = message.get("method")
    ident = message.get("id")
    if ident is None:
        return None
    base = {"jsonrpc": "2.0", "id": ident}
    try:
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL,
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "scout-local", "version": "0.2.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            data = dispatch(name, args)
            result = {"content": [{"type": "text", "text": json.dumps(data, separators=(",", ":"))}],
                      "structuredContent": data, "isError": False}
        else:
            return {**base, "error": {"code": -32601, "message": "Method not found"}}
        return {**base, "result": result}
    except (ValueError, KeyError, OSError, TypeError) as exc:
        if method == "tools/call":
            return {**base, "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True}}
        return {**base, "error": {"code": -32602, "message": str(exc)}}


def main() -> None:
    for raw in sys.stdin.buffer:
        if len(raw) > 1_048_576:
            continue
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                continue
            response = handle(message)
            if response is not None:
                sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (ValueError, UnicodeDecodeError):
            continue


if __name__ == "__main__":
    main()
