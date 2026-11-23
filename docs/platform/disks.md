---
layout: home
title: Farm disks
permalink: /platform/disks/
parent: Platform guides
nav_order: 0
---

# Farm disks

![OSM peak disk R/W with rated sequential ceiling]({{ '/images/osm-disk-history-rated.png' | relative_url }})

One-time history summary (not kept current): OSM peak disk R/W by x86 CPU across PostgreSQL majors, with the dashed line showing the manufacturer-rated sequential read of the drive that owned each major’s **published** cycle. PG17 pins to Crucial T705; Fury G5 arrived late and belongs with SK51 on 18–19. The live [leaderboard disk chart]({{ '/leaderboards/' | relative_url }}) stays retrospective — best peaks even after release write-ups. Built once via `reports/osm-disk-history.py --rated-ceiling`.

That Gen5 handoff was messy. The [PG17 write-up](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours)’s ~11 GB/s spike was the **i9-14900K** on T705 — then the chip’s voltage failure hit just as PCIe 5.0 drives arrived, when those clocks mattered most. The 14900K left the farm mid-evaluation and is omitted from the x86 series. The nearby PG17 peak still drawn here is the **i5-13600K** just under 11 GB/s: close for shape, not the same run, and a weaker host for pushing Gen5.

## Catalog

NVMe (and one RAID) devices that appear in `tests.server_disk` / set names on the pgbent farm. **Rated** speeds are manufacturer sequential claims for the capacity used here — marketing ceilings, not Postgres throughput. Labels in the results DB are short report names; `dmirow` sometimes stamps a longer string that gets trimmed.

`server_disk` is copied from the `server` row at run time (or set intentionally for remote client/server studies). Rising’s blank history was backfilled from set names in `regress/rising-disk-backfill.sql`.

**First / last** are `min` / `max` of `tests.start_time` for that label (aliases folded — e.g. Remote SK41 with SK41, all T705 stamps together).

## Published disk chapters

Predecessor — **PG13 / Inland Gen4** ([Crunchy, Sep 2020](https://www.crunchydata.com/blog/postgresql-13-upgrade-and-performance-check-on-ubuntu)): first farm results on the Inland Performance 2TB (rising, 3950X), ~1.6 GB/s random reads and the drive’s 5 GB/s sequential claim. Also notes a mild PG13-vs-12 SELECT dip above 32 clients as typical noise — often the Linux scheduler fighting `pgbench`, not a core regression to chase.

Later — **PG17 / T705 Gen5** ([Crunchy, Nov 2024](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours)): OSM under four hours and the first published Gen5 disk chapter on the farm.

## Lab NVMe (chronological)

| Farm label | Product | PCIe | Rated seq. read / write | First | Last | Notes |
|------------|---------|------|-------------------------|-------|------|-------|
| **Intel 750p** | Intel SSD 750 Series **AIC** 1.2 TB | **3.0** ×4 | **2,500 / 1,200** MB/s | 2020-08-25 | 2021-03-08 | Early rising card (HHHL AIC, not U.2). Every “Intel” / “Intel 750” set is this drive. |
| **Inland Performance 2TB** | Inland Performance / “Inland 4.0” (Phison E16 + DRAM; dmirow `EGFM11.0`) | **4.0** ×4 | **5,000 / 4,300** MB/s ([Hardware Corner](https://www.hardware-corner.net/ssd-database/Inland-Performance/)) | 2020-09-05 | 2023-06-08 | Rising workhorse; first PCIe **4.0** on the farm (“Inland 4.0” in set names). First published results: [PG13 on Ubuntu](https://www.crunchydata.com/blog/postgresql-13-upgrade-and-performance-check-on-ubuntu). Not the retail **Inland Platinum** Gen3 QLC SKU. |
| **Sabrent Rocket 4 Plus 2TB** | Sabrent Rocket 4 Plus 2 TB | **4.0** ×4 | **7,100 / 6,600** MB/s | 2022-02-24 | 2022-08-25 | Rising. Set names say Rocket / Rocket Plus / Rocket 4 Plus / Rocket 2TB — all this drive, not an original Rocket. |
| **SK41 2TB** | SK hynix Platinum **P41** 2 TB | **4.0** ×4 | **7,000 / 6,500** MB/s | 2022-10-30 | 2025-07-08 | Siren and twilight (and a few friday remote labels). |
| **Crucial T705 2TB** | Crucial T705 2 TB | **5.0** ×4 | **14,500 / 12,700** MB/s | 2024-08-16 | 2025-10-09 | First Gen5; published PG17 disk story ([Crunchy](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours)). See chart note above. |
| **FireCuda 530 4TB** | Seagate FireCuda 530 4 TB | **4.0** ×4 | **~7,300** MB/s read (farm note) | 2025-03-26 | 2025-06-25 | Short siren era (2025). |
| **SK51 2TB** | SK hynix Platinum **P51** 2 TB | **5.0** ×4 | **14,700 / 13,400** MB/s | 2025-06-28 | 2026-11-18 | Current siren disk. |
| **Fury G5 4TB** | Kingston FURY Renegade **G5** 4 TB | **5.0** ×4 | **14,800 / 14,000** MB/s | 2025-10-15 | 2026-11-19 | Current twilight disk. |

## Other farm storage

| Farm label | What it was | PCIe | Rated / note | First | Last |
|------------|-------------|------|--------------|-------|------|
| **IronWolf 510x4** | 4× ~512 GB Seagate IronWolf **510** on a PCIe passthrough RAID controller (**2 TB** total). Single 480 GB IronWolf 510: up to **~2,650 / 600** MB/s; aggregate depends on the RAID card. | **3.0** ×4 per drive | short rising window | 2021-05-13 | 2021-05-17 |
| **Apple AP1024R** | decade internal Apple SSD (dmirow sometimes `APPLE SSD … - AppleAPFSMedia`) | Apple fabric | not a PCIe-generation story in the Linux sense | 2021-10-29 | 2025-12-02 |
| **Apple AP2048Z** | abbey / friday (and occasional remote stamps) | Apple fabric | same | 2025-01-23 | 2026-11-20 |
| **Samsung MZALC4T0HBL1-00B07** | Court / DGX Spark OEM 3.7 TB NVMe — see [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) | OEM (Spark platform) | firmware default coalescing, not Gen rating, was the Relations story | 2026-04-12 | 2026-11-22 |

## Label aliases

| Results / set text | Canonical row above |
|--------------------|---------------------|
| Intel, Intel 750 | Intel 750p |
| Inland, Inland Perf, Inland 4.0, Inland 2TB, `PCIe SSD - EGFM11.0` | Inland Performance 2TB |
| Rocket, Rocket Plus, Rocket 4 Plus, Rocket 2TB | Sabrent Rocket 4 Plus 2TB |
| SK41, Remote SK41 2TB | SK41 2TB (P41) |
| SK51 | SK51 2TB (P51) |
| T705, Crucial T705, T705 2TB | Crucial T705 2TB |
| FireCuda 530 4TB | FireCuda 530 4TB |
| Fury G5 4TB | Fury G5 4TB |

Remote client/server studies can stamp another host’s disk on the results row on purpose (e.g. friday↔siren connection work, rising set 86 two-server guest left blank).
