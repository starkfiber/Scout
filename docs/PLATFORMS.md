# Scout platform contract

Scout is a file intelligence product, not a Mac-only utility. It has three surfaces: local desktop/CLI, a browser interface, and read-only tools for coding agents. An OS adapter supplies filesystem enumeration, metadata, permissions and activity. A website cannot silently inspect a visitor's device.

| Platform | Current state | Required adapter |
| --- | --- | --- |
| macOS Apple Silicon | Working local preview; RF² native directory/metadata service plus C SQLite index bridge; Python HTTP/MCP control plane | FSEvents incremental refresh, signed app, native HTTP/MCP migration |
| Linux server/desktop | Design target | RF² Linux ABI/backend or separately identified native adapter, inotify, volume metrics |
| Windows desktop/server | Design target | RF² Windows backend or separately identified native adapter, USN/ReadDirectoryChangesW, NTFS/ReFS metrics |
| Android | Design target | App-scoped storage adapter under Android permission model; no unrestricted device-wide promise |
| iPhone/iPad | Design target | Files-provider/document-picker access within iOS permission model; no unrestricted device-wide promise |
| Browser | Live public design preview | User-selected folder picker for bounded local mode; no automatic whole-device scan |
| Coding agents | Working local metadata-only MCP server on macOS preview | Platform-neutral protocol over each local adapter, explicit roots and freshness |

The RF² 0.12 compiler currently targets macOS ARM64. Its bounded Core/MCP has no filesystem effects. Scout's trusted RF² systems program performs native enumeration and metadata collection; the index bridge uses C for traversal and SQLite. Neither is a portable RF² runtime. Cross-platform claims require built, tested binaries on each target.
