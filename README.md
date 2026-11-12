# Scout by SFE

### See the weight of your files. Follow the pulse of your drive.

Scout is a local-first file intelligence system for computers, servers, browsers and coding agents. The product spans desktop, CLI and MCP; platform agents provide operating-system access. The **working preview is currently macOS**. It combines a folder browser, searchable metadata index, proportional capacity map and live **device-wide** disk traffic.

![Scout observatory, capacity map, explorer and activity panels](docs/images/scout-preview.png)

**[Explore the product site](https://starkfiber.my/scout)** · **[Read the V2 design](docs/PRODUCT.md)** · **[See RF² progress](docs/RF2.md)**

> **Preview, not a release.** The website introduces Scout; it cannot silently inspect a visitor's filesystem. Windows, Linux, Android and iPhone adapters are product targets, not available downloads. The current macOS preview is read-only.

## Run the local preview

On macOS, download this repository and run:

```sh
/usr/bin/python3 -m scout
```

Open **http://127.0.0.1:8766/**. The service listens on your Mac's loopback interface. `Run Scout.command` is an alternative on this Mac; a GitHub ZIP may require `chmod +x 'Run Scout.command'` before double-clicking it.

Scout opens one folder at a time immediately. Choose **Index this folder** to build a searchable metadata index for that subtree. The index lives in your local Application Support folder and is never part of this repository. The optional `?path=Documents/Scout` URL parameter opens a folder under your home directory; the server still enforces its path boundary.

## What you can do today

| Explore | Observe | Connect AI |
| --- | --- | --- |
| Open folders, follow breadcrumbs, sort and filter, inspect metadata, copy a path and reveal it in Finder. | See APFS used/free capacity, a clickable map of **measured** folder sizes, and a graph of combined internal-drive I/O. | Run a local, read-only MCP server that lists, finds and inspects path metadata without sending file contents. |

Press **⌘K** for indexed search. Indexing is opt-in; Scout labels incomplete coverage and unmeasured sizes. The map represents logical folder allocation, **not** physical NAND placement. Open Codex file handles are shown on demand; an open handle does not prove an active read or write.

## Browser and privacy boundary

`starkfiber.my/scout` is a public landing page. A website can access local files only when a user explicitly grants access through a supported browser picker, and that limited view is not equivalent to a Mac-wide explorer. Scout's full capacity, disk traffic, Finder actions and local index run in the local companion. Scout does not upload your files or index, and this repository contains no personal scan data.

## RF² status, honestly

Scout's macOS folder browser now uses a **persistent trusted RF² 0.11 ARM64 service** for directory enumeration and file metadata. Build it with `sh rf2/build.sh`; the UI labels listings **RF² native files + metadata**. When unavailable or failing, Scout shows its Python fallback. Python still maintains the SQLite search index and serves the browser/MCP interfaces. RF² Core/MCP has **no filesystem access**; this Scout-specific program is a separate trusted systems-profile build. On one temporary 5,000-file fixture, 12 warm listings measured 27.6 ms median native versus 33.8 ms Python, including sorting and pagination. This is a local result, not a cross-platform or universal speed claim. See [RF² evidence](docs/RF2.md) and the [platform plan](docs/PLATFORMS.md).

## Build with us

The next gates are native indexing and change tracking, cross-platform OS adapters, recoverable organization actions, and signed desktop/mobile distributions. See the [product plan](docs/PRODUCT.md) and [verified handover](docs/HANDOVER.md). Issues and contributions are welcome, especially measured performance cases and accessibility review. Please keep personal file paths, indexes, credentials and screenshots out of public issues.

MIT licensed. Scout is distinct from Stark Fiber's existing `/kit/scout` GitHub discovery product.
