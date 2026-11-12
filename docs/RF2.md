# Scout and RiverFlow RF²

## Native index worker — 12 November 2026

`native/scout_index.c` is a signed macOS ARM64 SQLite persistence bridge. It launches the trusted RF² `scout-dir-service`, requests every directory, validates its bounded binary records, manages the folder stack and writes the existing local SQLite/FTS index inside one transaction. Python starts and monitors the worker, but does not enumerate files or write index rows on this path. The UI reports `RF² native index`. If the worker is missing, Scout explicitly uses its older Python path; if a running native scan fails, the transaction rolls back and the prior index remains available.

Eleven local tests pass. They compare all indexed row fields with the Python implementation for nested, hidden, Unicode and newline names; exercise a response spanning chunks; assert native scanning does not call Python `os.scandir`; and verify that a failed worker cannot publish a new file or erase the last completed scan. The restarted local preview indexed the Scout repository with engine `rf2-native-index-bridge`, no error, and working search. The index and its scan history stay in the local Application Support directory.

On one Apple Silicon Mac, three warm full scans of a temporary 40-folder, 5,000-file tree took **75.65 ms median** through RF² plus the C bridge versus **179.24 ms** through Python. Three warm scans of a temporary 100-folder, 20,000-file tree took **261.13 ms** versus **745.76 ms**. Each pair used the same tree and SQLite schema; the native runs came first, followed by the Python runs. The measurements include process startup, traversal, metadata, FTS updates, folder totals and commit. They do not measure cold disk, very deep trees, battery cost, or Windows/Linux. This is a faster measured indexing path on those fixtures, not a universal speed claim or RF²-only persistence: SQLite calls and traversal orchestration are C.

## Native directory and metadata service — 12 November 2026

`rf2/dir_service.rf2` is a persistent trusted RF² 0.12 macOS ARM64 process. It accepts length-prefixed paths over stdin, calls Darwin `getdirentries64` and `lstat64`, and returns bounded binary records containing names, file mode, logical bytes, allocated blocks and modification time. `scout/rf2_native.py` validates framing and records for interactive folder listing; the Scout API applies filtering, sorting and pagination there. `rf2/build.sh` compiles and signs the helper locally, then atomically replaces the executable. The UI labels native results and Python fallback explicitly. The opt-in index consumes the same RF² service from the C worker described above. Python still serves HTTP/MCP, volume capacity and activity collection.

The service opens a requested directory with Darwin `O_DIRECTORY | O_NOFOLLOW` and stops on a metadata syscall failure. The client then restarts or visibly falls back to Python. This closes final-component symlink traversal in the service, but is not a complete sandbox or a solution to races in earlier path components.

Completed opt-in scans now write a small local `scan_runs` record in the same SQLite transaction as stale-row pruning. It stores scope, time, count and engine, so Scout can show the last completed scan after a process restart. A failed subtree scan does not write a completion record or prune prior indexed paths. The scan history is private local metadata, not part of this repository or a remote service.

At the earlier metadata-only checkpoint, nine tests passed, including Unicode/newline names, a no-follow symlink directory check, process failure fallback, native index parity, denied-subtree retention, and a 1,200-entry directory crossing response chunks. On a temporary 5,000-file fixture rebuilt with RF² 0.12, 12 warm `list_folder` calls measured 33.923 ms median native (max 41.667 ms) versus 39.830 ms median Python (max 41.016 ms). The previous RF² 0.11 build measured 27.629 ms native versus 33.835 ms Python on a separate warm run of the same fixture shape. The run was on one Mac and one filename shape, with warm cache and 120 displayed entries; no universal speed claim follows. A 500-entry fixture had a smaller or variable advantage. Cold scan, energy and deep trees need separate comparison. Before the C worker was added, a 40-folder, 5,000-file warm opt-in index fixture took 170.76 ms median with RF² metadata versus 180.22 ms with Python metadata over three runs each; traversal and SQLite were Python in both cases.

## RF² 0.12 rebuild and historical 0.11 probe checkpoint — 12 November 2026

The earlier installed 0.11 native CLI reports `mcpFilesystemAccess: false`. Its trusted systems compiler rebuilt `rf2/probe.rf2` with `--opt`, signed the executable, and the executable listed the current Scout repository directory with exit code 0. This verifies that the small directory probe still works on 0.11. It does **not** implement Scout's production explorer, metadata index, or MCP file tools. That was the historical state before the persistent service and C index bridge; MCP serving remains in Python.

The first Scout helper emitted NUL-separated directory names, so names containing a newline remained unambiguous. `sh rf2/build.sh` still builds `rf2/bin/scout-dir` as a one-shot fallback. The current preferred `scout-dir-service` also returns native metadata; the earlier helper's timing below is retained as a baseline, not the current engine.

On a temporary 500-entry directory, 12 warm calls of the historical one-shot hybrid had median 5.23 ms versus 2.97 ms for Python; maximums were 10.97 and 3.55 ms. This baseline included repeated process launches and Python metadata calls. It must not be conflated with the current persistent metadata service.

## Historical 0.10 systems probe

RiverFlow 0.10 has two distinct execution profiles. Bounded Core can only read a supplied array. Its existing nine MCP tools do **not** accept file paths or scan a filesystem. The trusted `RF2_SYSTEM_A64_V1` profile can compile native ARM64 programs that use Darwin OS calls, but that source is accepted only by the local compiler, never by the bounded MCP checker.

The minimal [probe](../rf2/probe.rf2) is an executed proof that a trusted RF² program can enumerate one explicitly named directory on this Mac. It calls Darwin `getdirentries64` (system call 344), parses the returned directory records, and emits NUL-separated entry names. It does not follow subdirectories, collect file sizes, write an index, watch changes, or provide MCP tools. It must not be treated as a production scanner or a security boundary.

### Build and verification

On this Mac, at the earlier 0.10 checkpoint:

```sh
RF2_ROOT="${HOME}/.codex/plugins/cache/riverflow-local/rf2/0.10.0"
"$RF2_ROOT/tools/build-program.sh" "$RF2_ROOT/output/native-compiler/rf2c" rf2/probe.rf2 /tmp/scout-rf2-probe-build --opt
/tmp/scout-rf2-probe-build/program /tmp/scout-rf2-fixture
```

The build helper refuses an existing output directory; choose a fresh one for a new build. The compiled executable was ad-hoc signed and `codesign --verify` passed. A local fixture containing `alpha.txt`, `beta.txt`, and `dir-a` returned those names, plus `.` and `..`, with exit code 0. Probe source SHA-256: `3b357154e5d56ace00860f03a8f11c516dbb1e3136b7b8a8d82cb656601f1d37`. Test executable SHA-256: `a250c82f5fc988ac1f4c058388a9aed7f2a946896f626a0ab0632537d31b45a8`.

An exploratory fixture of 2,000 empty files gave a median 3.531 ms over 10 warm RF² probe subprocess runs (range 3.311–4.175 ms, output discarded). Python's in-process `os.scandir` took a median 0.633 ms over 10 warm runs (range 0.592–0.688 ms). The measurements have different process and output costs and neither measures metadata collection or index lookup. They prove functionality, **not** a speed advantage. Run matched cold/warm and incremental benchmarks before making performance claims.

## Scout V2 implementation route

1. **Native scan worker:** Extend the RF² systems program to traverse a user-selected, bounded root, collect path, type, logical/allocated size, mtime, and file identity without reading file contents by default. Guard symlinks, errors, cancellation, resource caps, and paths that macOS privacy controls deny. Do not scan all of `/Users` automatically.
2. **Persistent local index:** Store immutable scan generations and incremental updates in a compact local index. A warm search must use the index; recursively rescanning the filesystem for every query would make the AI and Explorer slow. The current RF² package has no SQLite binding or FSEvents wrapper. Either implement a simple versioned index in RF² with explicit OS calls, or use a small native bridge for SQLite/FSEvents and document that boundary. Do not present the bridge as RF² code.
3. **Scout-specific MCP driver:** Build and register separate, read-only tools such as `scout_roots`, `scout_list`, `scout_search`, `scout_stat`, and `scout_activity`. Return stable path identities, freshness timestamps, and paged results. Resolve within explicitly permitted roots; reject escapes and sensitive paths. File contents should require a separate explicit request and a size cap. The present `rf2 mcp` server does not implement these tools.
4. **Explorer app:** Show indexed paths in a responsive list/tree with keyboard navigation, previews only on demand, and a visual storage map. The visualization can use pre-rendered Blender board assets, but never block file search on 3D rendering. macOS Finder actions should be explicit and reversible.
5. **Truthful live activity:** `iostat` reports overall device traffic. An open file handle is not proof of a read. To show process-attributed reads or writes, implement and validate a separate supported data source and display its actual scope and permissions. Do not animate named files as "being read" based only on `lsof`.

## Gates before calling Scout fast or safe

- Compare cold crawl throughput, warm indexed query p50/p95, incremental update delay, memory footprint, and battery cost against Finder and a straightforward native/Python baseline on the same tree.
- Test Unicode and long paths, package directories, symlinks, hard links, APFS clones, inaccessible folders, external volumes, disconnects, and file mutation during scans.
- Keep search/list/stat read-only. Any move, offload, or removal needs an explicit reviewed operation with destination verification and a restore record; the Scout index is not a backup.

## RF² source references

- `docs/NATIVE-CORE.md`: Core effects and direct compilation route.
- `docs/STANDALONE.md`: installed native binary and MCP scope.
- `docs/PLATFORM-ABI.md`: trusted Darwin syscall ABI.
- `docs/MODULES-TYPES.md`: source composition, records, and limits.
- `docs/COMPACT-MCP.md`: compact responses do not add filesystem effects.
