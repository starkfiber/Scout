# Scout V2 handover — 12 November 2026

## Verified now

- Local macOS preview runs at `http://127.0.0.1:8766/` with immediate one-level browsing, filtering, sorting, breadcrumbs and metadata inspection.
- An opt-in SQLite metadata index supports name and path search. Reindexing removes stale paths in the regression test. The index stays outside this repository.
- The logical capacity map uses measured allocated sizes from the current folder and labels incomplete coverage. A tile opens its folder or selects its file.
- APFS capacity and combined internal-drive throughput are live measurements. Codex open handles are an on-demand observation. The Blender M.2 image is illustrative.
- Read-only stdio MCP tools expose bounded path metadata. Filesystem escape and symlink traversal are rejected in tests.
- Nine `unittest` cases pass. The earlier small-fixture HTTP timings and the newer directory/index timings are separate measurements; neither is a whole-disk or cross-product benchmark.

## Evidence

- Implementation: `scout/`, `assets/`, `tests/test_core.py`.
- RF² source, scope and measurements: `rf2/dir_service.rf2`, `rf2/probe.rf2`, `docs/RF2.md`.
- Product and reference review: `docs/PRODUCT.md`.

## Next work

- Build RF²-owned persistent indexing and compare its full workload with the current hybrid path on cold and warm fixtures.
- Add filesystem watching, index freshness and explicit coverage states.
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
