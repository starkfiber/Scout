# Scout

### See the weight of your files. Follow the pulse of your drive.

Scout is an experimental, local-first storage explorer for macOS. It combines a fast folder browser, an opt-in searchable metadata index, a proportional capacity map, and live **device-wide** disk traffic in one view.

![Scout observatory, capacity map, explorer and activity panels](docs/images/scout-preview.png)

**[Explore the product site](https://starkfiber.my/scout)** · **[Read the V2 design](docs/PRODUCT.md)** · **[See RF² progress](docs/RF2.md)**

> **Preview, not a release.** The website introduces Scout; it cannot silently inspect a visitor's filesystem. This local preview is read-only and has no signed Mac download yet.

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

RiverFlow **0.11** can compile a trusted native ARM64 directory-enumeration probe in [`rf2/probe.rf2`](rf2/probe.rf2). Its bounded MCP/Core profile has **no filesystem access**. Scout's current working explorer and SQLite index use Python `os.scandir`; there is no production RF² filesystem engine or proven speed gain yet. The [RF² engineering record](docs/RF2.md) explains the exact boundary and the benchmark needed before replacing the engine.

## Build with us

The next gates are filesystem change tracking, large-tree latency and memory benchmarks, a complete native scanner, recoverable organization actions, and a signed Mac app. See the [product plan](docs/PRODUCT.md) and [verified handover](docs/HANDOVER.md). Issues and contributions are welcome, especially measured performance cases and accessibility review. Please keep personal file paths, indexes, credentials and screenshots out of public issues.

MIT licensed. Scout is distinct from Stark Fiber's existing `/kit/scout` GitHub discovery product.
