---
layout: home
title: Leaderboards
permalink: /leaderboards/
nav_order: 0
has_children: true
---

# Leaderboards

Public OSM planet-load and pgbench SELECT rankings from the pgbent server farm personally run by Greg Smith. This page is updated when there are interesting new cells; it is not a live dashboard.

Initial [PostgreSQL 19rc1 report]({{ '/results-summary/pg19/' | relative_url }}): 19 took the top leaderboard spots with a tiny delta over 18 (rc1 2026-10-15, catalog 20261006).

## OSM

The OSM Score is a composite ranking based on loading the OpenStreetMap Planet GIS workload. The score includes just the hardest CPU phase, Relation building, and the two longest index builds. It ignores aspects of the loading that stress cache effects more so than CPU or disk.

At current sizes near 10 billion nodes, a **Total** of **750** kNodes/s is a 4-hour run. The bars are the score categories used here: OSM score, full-load Total score, and Index score. Total and Index also show hours to the right of the bar—the wall-clock figure people normally quote.

![OSM load leaderboard — best run per server configuration]({{ '/images/osm-leaderboard.png' | relative_url }})

**R9 9950X** leads at **1480** OSM score (**719** Total, **4.17h**). **i5-13600K** follows on the same Planet. Disk traces, package watts, and energy are on [OSM Leaders: Performance vs. Power]({{ '/leaderboards/osm-performance-power/' | relative_url }}).

The OSM table is the current Planet extract (**10.79 billion** nodes), mixed PostgreSQL 16–19, ranked by OSM score. The [PostgreSQL 18]({{ '/results-summary/pg18/' | relative_url }}) snapshot remains the last frozen release cycle. Watts, durability (`fsync` / `wal_level`), and checkpoint columns travel with the OSM rows.

Best OpenStreetMap planet load per **machine × version × durability** cell (host-local client). Only extracts with **at least 10 billion nodes** are eligible. Each row is the **score_kips** winner for that CPU/memory/disk, PostgreSQL major, `fsync`, `wal_level`, and `max_wal_gb`. Ranked by OSM score (`score_kips`): node count divided by relation + polygon + line time, in kNodes/s. **overall_kips** is the full load; **index_kips** is index build. Fast cells (`fsync=off` / `wal_level=minimal`) stay on the board and are labeled, not hidden.

You can potentially triple the OSM score running on the fastest x86 instead of ARM, but it costs 4–5× as much energy to juice up the processors to do it. This workload does not benefit very much from larger core or socket counts. Relation building does not fill a second CCD or a second socket; extra cores mostly add package watts. The past 9600X→9950X swap barely moved OSM score.

<!-- osm-leaderboard-table:begin -->

_Query returned 20 rows._

| cpu | mem_gb | disk | ver | fsync | wal_level | max_wal_gb | conn | hours | score_kips | overall_kips | index_kips | rel_ps | avg_write | max_write | avg_read | max_read | pwr_est | avg_pkg | max_pkg | kj | score_per_watt | overall_per_watt | index_per_watt | wal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R9 9950X | 124 | SK51 2TB | 19 | off | minimal | 100 | host | 4.17 | 1480 | 719 | 364 | 4529 | 79 | 7772 | 68 | 9748 |  | 70 | 180 | 1046 | 8.2 | 4 | 2 | 20.4 |
| i5-13600K | 188 | Fury G5 4TB | 19 | off | minimal | 100 | host | 4.78 | 1407 | 628 | 410 | 4590 | 51 | 9692 | 42 | 9342 |  | 48 | 146 | 824 | 9.6 | 4.3 | 2.8 | 17.8 |
| R9 9950X | 124 | SK51 2TB | 18 | off | minimal | 100 | host | 4.07 | 1393 | 736 | 338 | 4560 | 84 | 7221 | 72 | 9477 |  | 71 | 199 | 1044 | 7 | 3.7 | 1.7 | 20.8 |
| i5-13600K | 188 | Fury G5 4TB | 18 | off | minimal | 256 | host | 4.8 | 1310 | 625 | 319 | 4364 | 52 | 9742 | 43 | 7627 |  | 50 | 151 | 859 | 8.7 | 4.1 | 2.1 | 17.6 |
| i5-13600K | 125 | Fury G5 4TB | 19 | off | minimal | 100 | host | 5.01 | 1213 | 599 | 383 | 4146 | 58 | 7331 | 41 | 8970 |  | 46 | 150 | 833 | 8.1 | 4 | 2.6 | 52.8 |
| R9 9950X | 124 | SK51 2TB | 19 | on | replica | 100 | host | 4.34 | 1203 | 690 | 282 | 4516 | 106 | 6099 | 67 | 9666 |  | 70 | 183 | 1100 | 6.6 | 3.8 | 1.5 | 97.1 |
| R9 9950X | 124 | SK51 2TB | 18 | on | replica | 100 | host | 4.45 | 1149 | 673 | 269 | 4425 | 108 | 5108 | 66 | 9429 |  |  |  |  |  |  |  | 102 |
| i5-13600K | 125 | Fury G5 4TB | 19 | off | replica | 100 | host | 4.93 | 1118 | 608 | 337 | 4132 | 67 | 6299 | 43 | 8878 |  | 48 | 149 | 855 | 7.5 | 4.1 | 2.3 | 85.5 |
| i5-13600K | 188 | Fury G5 4TB | 19 | on | replica | 100 | host | 5.03 | 1099 | 596 | 313 | 4468 | 67 | 9151 | 40 | 9110 |  | 48 | 150 | 866 | 7.3 | 4 | 2.1 | 83.4 |
| R9 9950X | 124 | SK51 2TB | 18 | on | replica | 256 | host | 4.54 | 1088 | 661 | 300 | 4398 | 103 | 6283 | 67 | 9457 |  |  |  |  |  |  |  | 93.2 |
| i5-13600K | 125 | Fury G5 4TB | 19 | on | replica | 100 | host | 5.43 | 1040 | 553 | 296 | 3849 | 62 | 6576 | 39 | 8792 |  | 46 | 149 | 896 | 7 | 3.7 | 2 | 77.3 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 17 | off | minimal | 256 | host | 7.75 | 578 | 387 | 250 | 1358 | 331 | 4159 | 331 | 4159 |  | 8 | 37 | 224 | 15.5 | 10.4 | 6.7 | 10.7 |
| NVIDIA P4242 | 119 | Samsung MZAL | 19 | off | minimal | 256 | host | 7.65 | 570 | 392 | 210 | 1242 | 156 | 9303 | 119 | 9196 |  | 28 | 91 | 778 | 6.3 | 4.3 | 2.3 | 34.6 |
| NVIDIA P4242 | 119 | Samsung MZAL | 18 | off | minimal | 100 | host | 7.81 | 567 | 384 | 236 | 1184 | 133 | 7135 | 117 | 9438 |  | 24 | 87 | 677 | 6.5 | 4.4 | 2.7 | 10.8 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 18 | off | minimal | 100 | host | 7.49 | 561 | 400 | 171 | 1674 | 325 | 6125 | 325 | 6125 |  | 9 | 35 | 276 | 16.1 | 11.5 | 4.9 | 11.3 |
| NVIDIA P4242 | 119 | Samsung MZAL | 16 | off | minimal | 256 | host | 7.62 | 522 | 394 | 202 | 1182 | 131 | 7301 | 110 | 6594 |  | 24 | 71 | 663 | 7.3 | 5.5 | 2.8 | 10.9 |
| NVIDIA P4242 | 119 | Samsung MZAL | 19 | off | minimal | 100 | host | 8.3 | 521 | 361 | 263 | 1095 | 124 | 6351 | 110 | 9627 |  | 23 | 89 | 701 | 5.9 | 4.1 | 3 | 10.3 |
| NVIDIA P4242 | 119 | Samsung MZAL | 19 | on | replica | 100 | host | 8.32 | 476 | 360 | 178 | 1150 | 169 | 7935 | 108 | 10599 |  | 25 | 86 | 756 | 5.5 | 4.2 | 2.1 | 50.7 |
| NVIDIA P4242 | 119 | Samsung MZAL | 18 | on | replica | 100 | host | 8.68 | 454 | 346 | 195 | 1124 | 172 | 5262 | 105 | 9921 |  | 23 | 92 | 729 | 4.9 | 3.8 | 2.1 | 53 |
| Apple M4 Max Studio | 128 | Apple AP2048 | 18 | on | replica | 100 | host | 11.1 | 265 | 270 | 69 | 1396 | 285 | 4578 | 285 | 4578 |  | 7 | 25 | 270 | 10.8 | 11 | 2.8 | 41.6 |

<!-- osm-leaderboard-table:end -->

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-leaderboard.py --from-db` (runs `reports/osm-leaderboard.sql`). Disk and power studies: [OSM Leaders: Performance vs. Power]({{ '/leaderboards/osm-performance-power/' | relative_url }}). 19rc1 cells vs PG18 on the same CPUs: [OSM Leaderboard (PG19)]({{ '/results-summary/pg19/osm-leaderboard/' | relative_url }}). Previous cycle used a smaller Planet (~9.3B nodes): [OSM Leaderboard (PG18 snapshot)]({{ '/results-summary/pg18/osm-leaderboard/' | relative_url }}). Workload notes: [OSM]({{ '/workloads/osm' | relative_url }}).

### History

Best OSM score per **x86** CPU across PostgreSQL majors (Apple and NVIDIA omitted). The score grades how releases run on popular chips; six years of history stay readable even as the Planet extract grew from ~8B to **10.79B** nodes—a growing dataset as counterweight to hardware and software speedups. CPU labels are reconstructed from set names (and carried forward on reused chassis) so siren’s 7700X→9700X→9950X swaps show as separate series.

![OSM score history by CPU across PostgreSQL majors]({{ '/images/osm-history.png' | relative_url }})

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-history.py` (runs `reports/osm-history.sql`).

Best peak disk **R/W** on those same loads — `max(max_write_mbps, max_read_mbps)` per run, then the best per CPU × major. Same x86 series and set-name CPU reconstruction. Storage and software keep pushing the ceiling up even as the Planet extract grows.

![OSM peak disk R/W history by x86 CPU across PostgreSQL majors]({{ '/images/osm-disk-history.png' | relative_url }})

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-disk-history.py` (runs `reports/osm-disk-history.sql`).

## pgbench SELECT

Phoronix-comparable **SELECT** cells: **90s**, scale 100.  The standard Postgres on Linux SELECT lab numbers published are at [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench); these are a comparable TPS collected by pgbent.

Phoronix switched to `-M prepared` a few years ago (PTS pgbench 1.13) and that reset the public face for a lot of viewers. Numbers went up, query planning in Postgres takes time. This lab still runs **all four faces** to SELECT performance — sockets vs localhost TCP, simple vs prepared. The [PG18 connection study]({{ '/results-summary/pg18/pgbench-select/' | relative_url }}) made the method public. Prepared is the Phoronix-shaped ranking cell. OpenBenchmarking’s multi-million TPS numbers involve multi-socket systems on DC network hardware, not localhost and not unix sockets sharing the server with pgbench.

The single socket leader board here is **siren** (R9 9950X) on PostgreSQL **19rc1**. Hold `conn_method` constant when comparing versions — mixing sockets with localhost TCP can look like a 25% hole. See [Comparing versions]({{ '/workloads/select/#comparing-versions' | relative_url }}).

Package power sits on the same row as TPS on the **sockets** face (one machine, complete accounting). Combining client and server watts across boxes is out of scope--that's the harder to observe data center shaped problem. **Transactions per joule** is the energy-efficiency number for each client count — the same 1-second `PkgWatt` integral as OSM kJ. Better performance is also more work per watt-second; the PG community cares about that as a virtuous side effect of code improvements, so this lab publishes it.

<!-- select-leaderboard:begin -->

Starter board from **siren** (R9 9950X), PostgreSQL **19rc1** (rc1 2026-10-15, catalog 20261006), scale 100, 90s. Same box, four faces of the connection sweep (PG18 study, kept as a code exercise): unix sockets vs localhost TCP, simple vs `-M prepared`. Peak is **32 clients**, sockets prepared (**2.06M TPS**). Localhost TCP prepared sits at **1.52M** (~26% below sockets). Package watts: 1-client is ~**62 W**; from 16 clients up the 9950X sits on the **~200 W PPT** rail (RAPL avg **199.6**, not a copied 200).

![pgbench SELECT - Siren 9950X]({{ '/images/select-leaderboard.png' | relative_url }})

**Transactions per joule** uses the same 1-second `PkgWatt` integral as OSM kJ. At 32 clients every face burns ~**17.8 kJ** in 90s — the PPT rail. Sockets prepared does **10,406** txn/J; localhost TCP simple does **5,040**. Same joules, twice the work. Energy efficiency is the other side of the protocol fan: better performance spends the same watt-seconds on more useful work.

![pgbench SELECT - transactions per joule]({{ '/images/select-leaderboard-joules.png' | relative_url }})

Mean across repeats (4 faces). **tps_1** is the old single-core cell; **tps_32** is the max on this chip. **pkg_*** is average package watts; **txn_j_*** is transactions per joule on those same runs.

| conn | tps_1 | pkg_1 | txn_j_1 | tps_32 | pkg_32 | txn_j_32 |
| --- | --- | --- | --- | --- | --- | --- |
| sockets prepared | 132,433 | 60.9 | 2,196 | 2,058,653 | 199.6 | 10,406 |
| localhost TCP prepared | 96,566 | 61.7 | 1,579 | 1,517,063 | 199.6 | 7,669 |
| sockets | 89,241 | 62.7 | 1,438 | 1,354,200 | 199.6 | 6,841 |
| localhost TCP | 68,924 | 65.2 | 1,066 | 997,097 | 199.6 | 5,040 |

<!-- select-leaderboard:end -->

`;` (`SCRIPT=nothing`) hits **280K TPS on a single client** (simple **281,019**, prepared **280,201**) and peaks at **4.05M** simple / **3.81M** prepared at 32 clients — the protocol ceiling. That's web scale. No query to plan, so preparation does not help; at many clients simple is a few percent ahead. Sockets `constant` (`SELECT 1`) at one client is **212,745** prepared (4.7 μs) / **179,635** simple (5.6 μs), and peaks at **2.96M** prepared / **2.48M** simple at 32. Execute of that query is +1.1 μs, planning it +0.9 μs, accounts lookup +2.9 μs on top. Unlike `;`, preparation helps `SELECT 1`. At one client the rates are just the inverse of the latency times. Breakdown: [1-client latency pieces]({{ '/workloads/select/#1-client-latency-pieces' | relative_url }}). Not on this ranking.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/select-leaderboard.py --from-db`. 19rc1 snapshot: [pgbench SELECT (PG19)]({{ '/results-summary/pg19/pgbench-select/' | relative_url }}). Older mixed-protocol grid: [pgbench SELECT (PG18 snapshot)]({{ '/results-summary/pg18/pgbench-select/' | relative_url }}). Workload notes: [pgbench SELECT]({{ '/workloads/select/' | relative_url }}).

### History

Best **sockets prepared** SELECT TPS per **x86** CPU across PostgreSQL majors — the same face as the starter board above. Older archives rarely stored `conn_method`; those points come from set names that said `Sockets Prepared`. The series is thin (rising 5950X, twilight i9, siren 9950X) but enough to anchor a trend. The chart omits the known-bad **5950X PG15**, suspect **14900K PG16**, and orphan **13600K** single-face archive peaks. An early set-112 PG16 cell at **1.84M** was a false valley (`shared_buffers=1GB`); fair 48GB re-runs on the same set peaked at **2.06M**. Modern **9950X** cells on **siren**: PG15 **2.12M**, PG16 **2.06M**, PG17 **2.07M**, PG18 **2.02M**, PG19rc1 **2.06M** (32 clients).

![pgbench SELECT sockets-prepared history by x86 CPU]({{ '/images/select-history.png' | relative_url }})

Long-term analysis here looks just for higher highs over time. That is why the analysis structure is a leaderboard.

PG15’s strong sockets-prepared peak on the 9950X is the fantasy face again: an older, simpler executor wins a pure SELECT microbenchmark. In production the features added since then pay for themselves — this chart is not an argument that newer majors are bloat.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/select-history.py` (runs `reports/select-history.sql`).

### Sockets

Unix-domain connections (`SOCKETS=1`). Clients run on the server. This is the power-ranking cell. **Prepared** is the Phoronix-shaped face.

### Networked

Localhost TCP (`host`) on this starter chart is protocol overhead on the same box, not a dedicated client. Unthrottled remote TCP is the face that can exceed on-box rates once the link is faster than ~10Gb/s.

## Contact

Greg is on Discord or e-mail. This page is the lab ranking, not an open submission program--at least not yet anyway.