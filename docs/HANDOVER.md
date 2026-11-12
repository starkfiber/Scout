# Scout V2 handover — 12 November 2026

## Verified now

- Local macOS preview runs at `http://127.0.0.1:8766/` with immediate one-level browsing, filtering, sorting, breadcrumbs and metadata inspection.
- An opt-in SQLite metadata index supports name and path search. Reindexing removes stale paths in the regression test. The index stays outside this repository.
- The logical capacity map uses measured allocated sizes from the current folder and labels incomplete coverage. A tile opens its folder or selects its file.
- APFS capacity and combined internal-drive throughput are live measurements. Codex open handles are an on-demand observation. The Blender M.2 image is illustrative.
- Read-only stdio MCP tools expose bounded path metadata. Filesystem escape and symlink traversal are rejected in tests.
- Three `unittest` cases pass. On a small local fixture, warm folder and search HTTP calls were sub-3 ms at p95; this is not a whole-disk or cross-product benchmark.

## Evidence

- Implementation: `scout/`, `assets/`, `tests/test_core.py`.
- RF² source, scope and measurements: `rf2/probe.rf2`, `docs/RF2.md`.
- Product and reference review: `docs/PRODUCT.md`.

## Next work

- Benchmark a complete RF² enumerator/index against the Python path on the same larger, opted-in fixture before replacing the engine.
- Add filesystem watching, index freshness and explicit coverage states.
- Design reviewed, recoverable file operations before any organizer action. Add a signed Mac app and release download only after permissions and recovery testing.
- Build the public landing page at `starkfiber.my/scout`; keep it distinct from the existing `/kit/scout` product. Link GitHub now and a download only when a release exists.

No personal file inventory, backup image, chat content or index belongs in this repository or the public site.

## 13:26 update — native metadata and platform scope

- Scout is the cross-platform product name. The runnable preview remains macOS ARM64; `docs/PLATFORMS.md` lists the access boundaries for other systems and browsers. The live site at `https://starkfiber.my/scout` now says Scout by SFE and labels the macOS preview; the GitHub About description and README match.
- `rf2/dir_service.rf2` compiles with RF² 0.11 into one persistent trusted systems-profile process. It enumerates directory entries and obtains mode, logical size, allocated blocks and modification time through Darwin syscalls. `scout/rf2_native.py` validates the bounded response, enforces a deadline and restarts after failure. The UI reports native metadata or visible Python fallback.
- Six local tests pass, including unusual filenames, symlink boundaries, a 1,200-entry response, parity, and failure fallback. One warm 5,000-file fixture measured 27.629 ms median native versus 33.835 ms Python across 12 `list_folder` calls. This is limited to one Mac and one workload. API response at `/api/list?path=Documents%2FScout` reported `rf2-native-metadata` with no engine error.
- Python still owns recursive indexing, SQLite, HTTP, MCP, volume capacity and activity sampling. Native index refresh and change tracking, then OS-specific adapters and complete workload benchmarks, are the next engineering gates. No Windows, Linux, Android or iPhone binary is available.
