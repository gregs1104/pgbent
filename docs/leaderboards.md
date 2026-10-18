---
layout: home
title: Leaderboards
permalink: /leaderboards/
nav_order: 0
---

# Leaderboards

Public OSM planet-load and pgbench SELECT rankings from the pgbent farm personally run by Greg Smith. This page is updated when there are new cells; it is not a live dashboard.

The OSM table is the current Planet extract (**10.79 billion** nodes), mixed PostgreSQL 16–19, ranked by OSM score. The [PostgreSQL 18]({{ '/results-summary/pg18/' | relative_url }}) snapshot remains the last frozen release cycle. Watts, durability (`fsync` / `wal_level`), and checkpoint columns travel with the OSM rows.

## OSM

Best OpenStreetMap planet load per **machine × version × durability** cell (host-local client). Only extracts with **at least 10 billion nodes** are eligible. Each row is the **score_kips** winner for that CPU/memory/disk, PostgreSQL major, `fsync`, `wal_level`, and `max_wal_gb`, with average and peak **disk MB/s** and **package watts** from the same run — the grid the power-efficiency study will use. Ranked by OSM score (`score_kips`): node count divided by relation + polygon + line time, in kNodes/s. **overall_kips** is the full load; **index_kips** is index build. Fast cells (`fsync=off` / `wal_level=minimal`) stay on the board and are labeled, not hidden. Per-watt columns use peak package power; `pwr_est` means only the peak was sampled.

![OSM load leaderboard — best run per server configuration]({{ '/images/osm-leaderboard.png' | relative_url }})

The chart still keeps one bar pair per machine (best **score** on that box). **R9 9950X** leads at **1480** OSM score (**719** overall kNodes/s, PostgreSQL 19, `fsync=off`, **70 W** average / **180 W** peak). **i5-13600K** follows on the same Planet.

<!-- osm-leaderboard-table:begin -->

_Query returned 11 rows._

| cpu | mem_gb | disk | ver | fsync | wal_level | max_wal_gb | conn | hours | score_kips | overall_kips | index_kips | rel_ps | avg_write | max_write | avg_read | max_read | pwr_est | avg_pkg | max_pkg | score_per_watt | overall_per_watt | index_per_watt | wal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R9 9950X | 124 | SK51 2TB | 19 | off | minimal | 100 | host | 4.17 | 1480 | 719 | 364 | 4529 | 79 | 7772 | 68 | 9748 |  | 70 | 180 | 8.2 | 4 | 2 | 20.4 |
| i5-13600K | 188 | Fury G5 4TB | 19 | off | minimal | 100 | host | 4.78 | 1407 | 628 | 410 | 4590 | 51 | 9692 | 42 | 9342 |  | 48 | 146 | 9.6 | 4.3 | 2.8 | 17.8 |
| i5-13600K | 188 | Fury G5 4TB | 18 | off | minimal | 256 | host | 4.8 | 1310 | 625 | 319 | 4364 | 52 | 9742 | 43 | 7627 |  | 50 | 151 | 8.7 | 4.1 | 2.1 | 17.6 |
| R9 9950X | 124 | SK51 2TB | 19 | on | replica | 100 | host | 4.34 | 1203 | 690 | 282 | 4516 | 106 | 6099 | 67 | 9666 |  | 70 | 183 | 6.6 | 3.8 | 1.5 | 97.1 |
| R9 9950X | 124 | SK51 2TB | 18 | on | replica | 100 | host | 4.45 | 1149 | 673 | 269 | 4425 | 108 | 5108 | 66 | 9429 |  | 70 | 181 | 6.4 | 3.7 | 1.5 | 102 |
| i5-13600K | 188 | Fury G5 4TB | 19 | on | replica | 100 | host | 5.03 | 1099 | 596 | 313 | 4468 | 67 | 9151 | 40 | 9110 |  | 48 | 150 | 7.3 | 4 | 2.1 | 83.4 |
| R9 9950X | 124 | SK51 2TB | 18 | on | replica | 256 | host | 4.54 | 1088 | 661 | 300 | 4398 | 103 | 6283 | 67 | 9457 |  | 70 | 174 | 6.2 | 3.8 | 1.7 | 93.2 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 17 | off | minimal | 256 | host | 7.75 | 578 | 387 | 250 | 1358 | 331 | 4159 | 331 | 4159 |  | 8 | 37 | 15.5 | 10.4 | 6.7 | 10.7 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 18 | off | minimal | 100 | host | 7.49 | 561 | 400 | 171 | 1674 | 325 | 6125 | 325 | 6125 |  | 9 | 35 | 16.1 | 11.5 | 4.9 | 11.3 |
| NVIDIA P4242 | 119 | Samsung MZAL | 16 | off | minimal | 256 | host | 7.75 | 504 | 387 | 197 | 1156 | 130 | 6115 | 111 | 6216 |  | 24 | 63 | 8 | 6.1 | 3.1 | 10.7 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 18 | on | replica | 100 | host | 11.1 | 265 | 270 | 69 | 1396 | 285 | 4578 | 285 | 4578 |  | 7 | 25 | 10.8 | 11 | 2.8 | 41.6 |

<!-- osm-leaderboard-table:end -->

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-leaderboard.py --from-db` (runs `reports/osm-leaderboard.sql`). Previous cycle used a smaller Planet (~9.3B nodes): [OSM Leaderboard (PG18 snapshot)]({{ '/results-summary/pg18/osm-leaderboard/' | relative_url }}). Workload notes: [OSM]({{ '/workloads/osm' | relative_url }}).

## pgbench SELECT

Phoronix-comparable **SELECT** cells: `-M prepared`, **90s**, scale 100, single-client and full-client. Package power and memory sit on the same row as TPS on the **sockets** face (one machine, complete accounting). Combining client and server watts across boxes is out of scope. Postgres developers care whether a code change moves power and memory up or down. For hardware outside this lab, use [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench) as the comparable TPS set.

The board has two faces: on-box unix sockets, and a network client. OpenBenchmarking’s multi-million TPS numbers are the networked face on DC hardware, not unix sockets sharing the server with pgbench. A sockets-versus-network mapping study will be published once. The remote rate sweep (same Mbps labels as [OSM Network]({{ '/results-summary/pg18/osm-network/' | relative_url }})) sits with that study, not as a third ranking.

Current published SELECT grid (older mix of protocols): [pgbench SELECT (PG18 snapshot)]({{ '/results-summary/pg18/pgbench-select/' | relative_url }}). Workload notes: [pgbench grids]({{ '/workloads/' | relative_url }}).

### Sockets

Unix-domain connections (`SOCKETS=1`), prepared statements. Clients run on the server. This is the power-ranking cell.

### Networked

TCP to a dedicated client (`host`), prepared statements. Unthrottled only on this board. This is the face that can exceed on-box rates once the link is faster than ~10Gb/s.

## Contact

Greg is on Discord or e-mail. This page is the lab ranking, not an open submission program.
