# Scout and RiverFlow RF²

## 0.11 check — 12 November 2026

The installed 0.11 native CLI reports `mcpFilesystemAccess: false`. Its trusted systems compiler rebuilt `rf2/probe.rf2` with `--opt`, signed the executable, and the executable listed the current Scout repository directory with exit code 0. This verifies that the small directory probe still works on 0.11. It does **not** implement Scout's production explorer, metadata index, or MCP file tools. Those remain in Python until a complete RF² scanner is built and measured on the same workload.

## What works today

RiverFlow 0.10 has two distinct execution profiles. Bounded Core can only read a supplied array. Its existing nine MCP tools do **not** accept file paths or scan a filesystem. The trusted `RF2_SYSTEM_A64_V1` profile can compile native ARM64 programs that use Darwin OS calls, but that source is accepted only by the local compiler, never by the bounded MCP checker.

The minimal [probe](../rf2/probe.rf2) is an executed proof that a trusted RF² program can enumerate one explicitly named directory on this Mac. It calls Darwin `getdirentries64` (system call 344), parses the returned directory records, and prints entry names. It does not follow subdirectories, collect file sizes, write an index, watch changes, or provide MCP tools. It must not be treated as a production scanner or a security boundary.

### Build and verification

On this Mac, with the installed 0.10 package:

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
