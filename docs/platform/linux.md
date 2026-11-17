---
layout: home
title: Linux standard tuning
permalink: /platform/linux/
parent: Platform guides
nav_order: 1
---

# Linux standard tuning

pgbent’s Linux hosts re-apply a small set of OS settings after every boot via [`util/pgbent_tune`](https://github.com/gregs1104/pgbent/blob/main/util/pgbent_tune), usually from `util/newgis`. None of these persist across reboot on their own (CPU governor and `read_ahead_kb` are runtime; NVMe coalescing is not saved to the drive). That is intentional: the same script is the checklist.

| Setting | What pgbent does | Why |
|---------|------------------|-----|
| CPU frequency governor | `performance` via `cpupower` | Avoid frequency scaling noise in timed runs |
| Block device read-ahead | `blockdev --setra 4096` (→ `read_ahead_kb=2048`) | Buffered Postgres needs OS readahead; zero is a special case that starves miss paths |
| NVMe interrupt coalescing | `nvme set-feature -f 8 -V 0` when `nvme-cli` is present | OEM defaults can hold every low-queue-depth read for 100 µs — see [NVMe coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) |
| TRIM | `fstrim -av` | Keep SSD free space honest between OSM cycles (can take a long time on multi-TB drives) |

Page-cache writeback (`vm.dirty_*`) is separate from this boot script — see [Linux pdflush / writeback]({{ '/platform/linux-pdflush/' | relative_url }}) and the measured [Linux dirty memory]({{ '/platform/linux-dirty-memory/' | relative_url }}) study.

## Read-ahead

Classic Postgres lore ties readahead to **sequential scans**. That case was measured in Greg’s 9.0-era material; public comparative work has been thin since, partly thanks to the DeWitt clause climate. pgbent’s standard `setra 4096` has been the lab default for years.

Newer evidence on a **scattered** index→heap pattern (`select-scatter`, the Relations miniature):

- On **court** (NVIDIA DGX Spark), `read_ahead_kb=0` roughly **halved** select-scatter throughput vs 128/2048, both cold and hot, before and after the coalescing fix. 128 vs 2048 was flat. So “some readahead” matters even when the access pattern does not look like a seqscan; **zero** is the dangerous setting.
- On **twilight** (x86), a public `read_ahead_kb` ladder over select-scatter was largely **flat** from 0 through 16384. Platform-dependent. A contiguous `select-range` ladder and an OSM load with RA=0 are the follow-ups for the classic sequential / load story.

**Practical rule:** do not leave Postgres volumes at array- or desktop-defaults of RA=0 because NTFS or interactive clients preferred that. Prefer on the order of pgbent’s 2048 KB unless you have measured otherwise. Details and tables: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).

## CPU governor

Timed benchmark and power comparisons assume the CPUs stay in `performance`. Mixing governors across a grid is a common false regression.

## How this relates to Direct I/O / AIO

Oracle-oriented storage guides often assume **Direct I/O**, where the database owns prefetch and a dumb array is fine. Stock Postgres is still mostly on the **buffered** path: the OS readahead and completion behavior are part of the database’s miss latency. Until AIO and related work fully own that path on bare metal, these Linux knobs remain first-line checks — not trivia next to block alignment.
