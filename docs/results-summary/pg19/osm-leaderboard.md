---
layout: home
title: OSM Leaderboard
permalink: /results-summary/pg19/osm-leaderboard/
parent: PostgreSQL 19
nav_order: 1
---

# OSM Leaderboard

Best current-Planet load per CPU for **PostgreSQL 19**, with the matching PG18 cell on the same iron. Live mixed-major ranking (16–19) stays on **[Leaderboards]({{ '/leaderboards/' | relative_url }})**.

![OSM load leaderboard — best run per server configuration]({{ '/images/osm-leaderboard.png' | relative_url }})

**R9 9950X** leads the 19 fast cell at **1480** OSM score (**719** kNodes/s total, **4.17h**). **i5-13600K** is next at **1407** (**628** total, **4.78h**) and still leads relations/s (**4590**). Durable 19 (`fsync` on / `wal_level=replica`) is **1203** / **1099** on those two boxes. **NVIDIA Spark (court)** hardware-best 19rc1 is **570** / **392** / **7.65h** (`max_wal_size=256GB`). **Apple M4 Max Studio (abbey)** has no PG19 cell yet — the PG18 fast **561** / **400** / **7.49h** stands in. 19 took the x86 top spots with a tiny delta over 18 on the same CPUs.

You can potentially triple the OSM score running on the fastest x86 instead of ARM, but it costs 4–5× as much energy to juice up the processors to do it. This workload does not benefit very much from larger core or socket counts. Relation building does not fill a second CCD; extra cores mostly add package watts.

Regenerate the live board: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-leaderboard.py --from-db`. Query: `reports/osm-leaderboard.sql`. Power study: [OSM Power]({{ '/results-summary/pg19/osm-power/' | relative_url }}). Twilight **188** Gi and **125** Gi rows both appear on the [live board]({{ '/leaderboards/' | relative_url }}); this summary keeps twilight’s physical **188** Gi cell.

Sets: siren **71** / **108**; twilight **118**; court **4** / **5** / **9** / **12** (19rc1 wrap, test **148** fast 256 GB WAL); abbey **11** (PG18). Fast = `fsync=off` / `wal_level=minimal`; durable = `fsync=on` / `wal_level=replica`. One best score per CPU × major × durability.

| cpu | ver | fsync | wal_level | max_wal_gb | hours | score_kips | overall_kips | index_kips | rel_ps | avg_pkg | max_pkg | kj |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R9 9950X | 19 | off | minimal | 100 | 4.17 | 1480 | 719 | 364 | 4529 | 70 | 180 | 1046 |
| i5-13600K | 19 | off | minimal | 100 | 4.78 | 1407 | 628 | 410 | 4590 | 48 | 146 | 824 |
| R9 9950X | 18 | off | minimal | 100 | 4.07 | 1393 | 736 | 338 | 4560 | 71 | 199 | 1044 |
| i5-13600K | 18 | off | minimal | 256 | 4.8 | 1310 | 625 | 319 | 4364 | 50 | 151 | 859 |
| R9 9950X | 19 | on | replica | 100 | 4.34 | 1203 | 690 | 282 | 4516 | 70 | 183 | 1100 |
| R9 9950X | 18 | on | replica | 100 | 4.45 | 1149 | 673 | 269 | 4425 | 70 | 181 | 1130 |
| i5-13600K | 19 | on | replica | 100 | 5.03 | 1099 | 596 | 313 | 4468 | 48 | 150 | 866 |
| NVIDIA P4242 | 19 | off | minimal | 256 | 7.65 | 570 | 392 | 210 | 1242 | 28 | 91 | 778 |
| NVIDIA P4242 | 18 | off | minimal | 100 | 7.81 | 567 | 384 | 236 | 1184 | 24 | 87 | 677 |
| Apple M4 Max Studio | 18 | off | minimal | 100 | 7.49 | 561 | 400 | 171 | 1674 | 9 | 35 | 276 |
| NVIDIA P4242 | 19 | on | replica | 100 | 8.32 | 476 | 360 | 178 | 1150 | 25 | 86 | 756 |
| NVIDIA P4242 | 18 | on | replica | 100 | 8.68 | 454 | 346 | 195 | 1124 | 23 | 92 | 729 |
| Apple M4 Max Studio | 18 | on | replica | 100 | 11.1 | 265 | 270 | 69 | 1396 | 7 | 25 | 270 |
