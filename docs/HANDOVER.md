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
