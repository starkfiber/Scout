# Scout for Mac

Scout is a private, local storage explorer and observatory. It opens folders immediately, builds a searchable metadata index only when asked, shows current APFS capacity, and samples combined I/O on the internal SSD. It never uploads files or indexes their contents.

## Run

On this Mac, double-click **Run Scout.command**. A fresh GitHub download may need `chmod +x 'Run Scout.command'` first. You can also run from this directory:

```sh
/usr/bin/python3 -m scout
```

Then open <http://127.0.0.1:8766/>. The local service binds to `127.0.0.1`, not the network. Use **Index this folder** in Explorer to enable fast search within a selected subtree. The private SQLite index lives at `~/Library/Application Support/Scout/scout.sqlite3` and is excluded from Git.

## What works in this preview

- Instant one-level folder navigation, pagination, filtering, sorting and keyboard search (`⌘K`)
- On-demand background metadata indexing and full-text path search; coverage is explicitly partial until chosen roots finish
- Current formatted-volume used/free capacity and sampled total internal-disk throughput
- On-demand list of Codex open file handles, explicitly distinct from confirmed read/write events
- File metadata inspector, copy path and reveal in Finder
- Read-only local MCP tools for AI clients: `scout_list`, `scout_find`, `scout_stat`, `scout_capacity`
- Blender-generated M.2 artwork as a visual layer

## Boundaries

This is an early local explorer, not a replacement for Finder yet. It cannot move, rename, delete, or back up files. It does not read file contents. Folder sizes appear after indexing; APFS clone/sharing means sums of logical folder sizes can differ from physical drive usage. The 3D SSD art illustrates a drive but cannot map directories to actual NAND cells. `iostat` provides combined drive traffic, not process/file attribution. Open handles from `lsof` do not prove active reads.

The app may not see folders protected by macOS privacy permissions unless Terminal has access. It reports inaccessible paths rather than bypassing macOS permissions. The current indexer uses Python `os.scandir`; the RF² native probe is in `rf2/` and is under development, with evidence in [docs/RF2.md](docs/RF2.md). No RF² speed win is claimed.

## Local MCP

Launch `python3 -m scout.mcp` from this checkout as a stdio MCP server. It returns paths and metadata, never file contents. The host must launch it locally. Do not put the private index or personal paths in the public repository.

## Product direction

See [docs/PRODUCT.md](docs/PRODUCT.md) for the V2 design and measured performance gates. A public landing page at `starkfiber.my/scout` is separate from the existing `/kit/scout` GitHub discovery product.
