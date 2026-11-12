# Scout V2 handover — 12 November 2026

## Verified now

- Local macOS preview runs at `http://127.0.0.1:8766/` with immediate one-level browsing, filtering, sorting, breadcrumbs and metadata inspection.
- An opt-in SQLite metadata index supports name and path search. Reindexing removes stale paths in the regression test. The index stays outside this repository.
- The logical capacity map uses measured allocated sizes from the current folder and labels incomplete coverage. A tile opens its folder or selects its file.
- APFS capacity and combined internal-drive throughput are live measurements. Codex open handles are an on-demand observation. The Blender M.2 image is illustrative.
- Read-only stdio MCP tools expose bounded path metadata. Filesystem escape and symlink traversal are rejected in tests.
- Eleven `unittest` cases pass. The earlier small-fixture HTTP timings and the newer directory/index timings are separate measurements; neither is a whole-disk or cross-product benchmark.

## Evidence

- Implementation: `scout/`, `assets/`, `tests/test_core.py`.
- RF² source, scope and measurements: `rf2/dir_service.rf2`, `rf2/probe.rf2`, `docs/RF2.md`.
- Product and reference review: `docs/PRODUCT.md`.

## Next work

- Add filesystem watching, incremental native index updates, freshness and explicit coverage states.
- Compare cold disk, deep trees, memory and energy across the RF²/C index worker and Python fallback.
- Design reviewed, recoverable file operations before any organizer action. Build signed platform distributions only after permissions and recovery testing.
- Keep the live `starkfiber.my/scout` page distinct from `/kit/scout`; offer a download only when a release artifact exists.

No personal file inventory, backup image, chat content or index belongs in this repository or the public site.

## 13:26 update — native metadata and platform scope

- Scout is the cross-platform product name. The runnable preview remains macOS ARM64; `docs/PLATFORMS.md` lists the access boundaries for other systems and browsers. The live site at `https://starkfiber.my/scout` now says Scout by SFE and labels the macOS preview; the GitHub About description and README match.
- `rf2/dir_service.rf2` compiles with RF² 0.12 into one persistent trusted systems-profile process. It enumerates directory entries and obtains mode, logical size, allocated blocks and modification time through Darwin syscalls. `scout/rf2_native.py` validates the bounded response, enforces a deadline and restarts after failure. The UI reports native metadata or visible Python fallback.
- Six local tests pass, including unusual filenames, symlink boundaries, a 1,200-entry response, parity, and failure fallback. One warm 5,000-file fixture rebuilt on RF² 0.12 measured 33.923 ms median native versus 39.830 ms Python across 12 `list_folder` calls. This is limited to one Mac and one workload. API response at `/api/list?path=Documents%2FScout` reported `rf2-native-metadata` with no engine error.
- Python still owns recursive indexing, SQLite, HTTP, MCP, volume capacity and activity sampling. Native index refresh and change tracking, then OS-specific adapters and complete workload benchmarks, are the next engineering gates. No Windows, Linux, Android or iPhone binary is available.
- The RF² plugin advanced to 0.12 during this work. Rebuilding the service with `--opt` produced a signed executable that terminated with signal 9 on launch; a non-optimized build ran. Copying a rebuilt executable over the old path also caused signal 9 on this Mac despite matching bytes and signature, while the same bytes at a new path ran. `rf2/build.sh` now uses the installed 0.12 compiler, builds the service without `--opt`, and atomically replaces both signed executables. Rebuild and all six tests passed after that change. Do not restore the old in-place copy path or add `--opt` to this service without reproducing the launch tests.

## 14:07 update — native metadata in the index

- The opted-in recursive index now obtains per-directory entries and metadata from a separate persistent RF² service process. Python still walks the tree and writes SQLite. Browser and index processes are independent, so scans do not queue directory opens behind one service lock.
- The index status exposes its engine and fallback error. A native process failure falls back to Python and completes. A denied subtree stops the scan before stale rows are pruned; the last indexed entries remain searchable. Nine tests pass, including both paths.
- A temporary 40-folder, 5,000-file warm index fixture took 170.76 ms median with native metadata and 180.22 ms with Python metadata across three runs each. The fixture does not measure cold disk, very deep trees or battery use. The restarted local preview indexed the Scout repository through `rf2-native-metadata` with no engine error. Its private index remains outside Git.
- Next: RF²-owned persistent index format and incremental watcher updates, with matching cold/warm measurements and recovery tests. Keep user indexes and path inventories out of Git and the public site.

## 14:17 update — completed scan continuity

- Completed scans now write a small `scan_runs` record in the local SQLite index transaction. It records scope, time, count and engine; no file contents are stored. A failed subtree scan leaves the previous completed record intact.
- The preview was restarted after a native scan. Its API reported no active engine and the last completed engine as `rf2-native-metadata`; the browser rendered that last scan and its time. The nine tests pass, including a simulated process-status reset. The refreshed README screenshot shows native index status.

## 14:48 update — native full-scan index

- `native/scout_index.c` is a signed C bridge for SQLite persistence. It drives the trusted RF² directory/metadata service through bounded pipes, traverses the selected tree, writes SQLite/FTS and folder totals in one transaction, and records completion. Python only starts and monitors this worker on the native path; it does not enumerate or write index rows. Missing binaries trigger an explicit Python fallback. A failed native scan rolls back and retains the last index.
- Eleven tests pass, including field-by-field native/Python index parity, a 1,200-file directory, a worker failure rollback, and an assertion that normal native indexing never calls Python `os.scandir`. The live local preview reported `rf2-native-index-bridge` with no error and returned indexed search results.
- Three warm scans of a 40-folder, 5,000-file temporary fixture measured 75.65 ms median native versus 179.24 ms Python. Three warm scans of a 100-folder, 20,000-file fixture measured 261.13 ms versus 745.76 ms. Native runs came first in each matched pair, then Python. These are one-Mac, warm-fixture measurements; no cold-disk, energy, deep-tree or other-platform result follows.
- Next: native incremental updates from supported OS events, cold/warm benchmarks on opted-in real trees, and cross-platform adapters. Python still serves HTTP/MCP and has the explicit fallback path. RF² itself supplies native metadata; traversal and SQLite persistence are C, not RF² language code.
