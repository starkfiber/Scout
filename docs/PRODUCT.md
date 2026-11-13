# Scout V2 product direction

## Product contract

Scout combines a file explorer, storage observatory and bounded AI path driver across local desktop/CLI, browser and coding-agent surfaces. OS adapters supply platform-specific access. The existing M.2 scene is a visual identity for the macOS preview; it never represents literal file placement. See [platform contract](PLATFORMS.md).

1. **Navigate now.** Open an immediate folder listing without a full-disk scan. Keep scrolling, sorting and keyboard navigation responsive while background work runs.
2. **Search indexed metadata.** Scan only user-selected roots, show coverage, make warm name/path queries fast, and refresh the index after filesystem changes. Do not index file contents by default.
3. **Observe accurately.** APFS capacity is volume-level. Activity is physical-drive I/O. Folder sizes are an indexed sum. The Blender board is a design layer, not a physical NAND map.
4. **Organize safely.** Future move/rename/archive actions require preview, collision handling, atomicity where possible, undo journal, backups and verification. This preview has no destructive actions.
5. **AI references.** MCP tools return local paths and metadata. A later opt-in read tool must enforce path scopes, text-only limits and secret exclusions. Never upload a user's index or file contents to the public landing page.

## Reference review (12 November 2026)

| Project | Verified approach | Scout decision |
| --- | --- | --- |
| [FileExplorer](https://github.com/conaticus/FileExplorer) at `22b69f5` (GPL-3.0) | Rust/Tauri/React, ART prefix search, fuzzy fallback, LRU cache, SFTP and file operations. [Search source](https://github.com/conaticus/FileExplorer/blob/22b69f5a677f23ec96f0578acdcf6ce76a2db60b/src-tauri/src/search_engine/search_core.rs#L795-L965). Its README still lists live watching as forthcoming. | Measure an index and cache locally. Do not copy GPL code into Scout's MIT tree. |
| [Nexus Explorer](https://github.com/Augani/nexus-explorer) at `3fea2ac` (MIT) | Rust/GPUI; [parallel traversal](https://github.com/Augani/nexus-explorer/blob/3fea2ac12ae87f851347140047f1a4e495db8adf/src/io/traversal.rs#L98-L116), fuzzy search, filesystem watching and [virtualized rows](https://github.com/Augani/nexus-explorer/blob/3fea2ac12ae87f851347140047f1a4e495db8adf/src/views/file_list.rs#L1730-L1777). | Make native indexing persistent and render only visible rows at scale. |
| [CoDriver](https://github.com/RickyDane/CoDriver) at `6a937cd` (BSD-2-Clause) | Rust/Tauri, dual panes, preview, archives, FTP/SFTP. Its README says it has no path cache. [FTP source](https://github.com/RickyDane/CoDriver/blob/6a937cda8bce004ba1c3e6aedb5158b91b690f00/src-tauri/src/remote/ftp.rs). | Explore dual-pane and remote browsing after local latency and recovery are proven. |

These repos' performance headlines are author claims; Scout has not independently benchmarked them. This review compares features and code paths, not runtime superiority.

## Design system

Light instrument surface by default, with a dark theme picker; cyan live signal, blue allocated space, teal available space, amber caution. The Blender M.2 artwork has a fixed 1600×720 transparent source and compressed WebP delivery. UI text, file rows and activity graphs remain native browser elements for accessibility and responsiveness. The board should never carry real path labels tied to NAND locations. Prefer meaningful, subtle animation and honor reduced-motion settings.

## Performance gates before a public download

Run on fixture trees and an opted-in real directory, recording hardware, item count, cold scan time, warm search p50/p95, directory-open p50/p95, index database size, idle CPU and memory. Compare RF² scanner against `os.scandir` on the same metadata and persistence workload, not a smaller toy probe. Test changes during a scan, deleted paths, symlink escape, denied folders, and a cold relaunch. Set a target of under 100 ms warm directory response for ordinary folders and under 50 ms indexed search, then report actual measurements. A throughput/IOPS/latency panel must show only metrics this OS exposes without privileged instrumentation.

## Product milestones

- **V2 local preview (current):** on-demand explorer, metadata index, search, proportional measured-folder map, capacity, combined I/O, Codex open handles, Blender artwork, metadata-only MCP.
- **Native engine:** persistent RF² directory and metadata service plus a C SQLite index bridge are working on macOS ARM64; change tracking, incremental refresh and broader workload measurements are the next gates.
- **Organizer:** verified copy/move/rename with undo, duplicate and clone awareness, archive/restore previews.
- **Platform apps:** signed macOS, Windows and Linux builds, then mobile adapters within Android/iOS file-permission boundaries.
- **Public site:** `starkfiber.my/scout` with actual screenshots, download, GitHub and contribution links once artifacts exist. The separate Kit Radar discovery product uses `/kit/radar`; `/kit/scout` remains a compatibility link.
