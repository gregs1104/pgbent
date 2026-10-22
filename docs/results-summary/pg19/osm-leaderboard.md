---
layout: home
title: OSM Leaderboard
permalink: /results-summary/pg19/osm-leaderboard/
parent: PostgreSQL 19
nav_order: 2
---

# OSM Leaderboard

Best current-Planet load per CPU for **PostgreSQL 19**, with the matching PG18 cell on the same iron. Live mixed-major ranking (16–19) stays on **[Leaderboards]({{ '/leaderboards/' | relative_url }})**.

![OSM load leaderboard — best run per server configuration]({{ '/images/osm-leaderboard.png' | relative_url }})

**R9 9950X** leads the 19rc1 fast cell at **1480** OSM score (**719** kNodes/s total, **4.17h**). **i5-13600K** is next at **1407** (**628** total, **4.78h**) and still leads relations/s (**4590**). Durable 19 (`fsync` on / `wal_level=replica`) is **1203** / **1099** on those two boxes. 19 took those top spots with a tiny delta over 18 on the same CPUs.

This workload does not benefit very much from larger core or socket counts. Relation building does not fill a second CCD; extra cores mostly add package watts.

Regenerate the live board: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-leaderboard.py --from-db`. Query: `reports/osm-leaderboard.sql`. Power study: [OSM Power]({{ '/results-summary/pg19/osm-power/' | relative_url }}).

Sets: siren **71** and twilight **118**. Fast = `fsync=off` / `wal_level=minimal`; durable = `fsync=on` / `wal_level=replica`. `max_wal_gb=100` on these 19 cells.

| cpu | ver | fsync | wal_level | hours | score_kips | overall_kips | index_kips | rel_ps | avg_pkg | max_pkg | kj |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R9 9950X | 19 | off | minimal | 4.17 | 1480 | 719 | 364 | 4529 | 70 | 180 | 1046 |
| i5-13600K | 19 | off | minimal | 4.78 | 1407 | 628 | 410 | 4590 | 48 | 146 | 824 |
| R9 9950X | 19 | on | replica | 4.34 | 1203 | 690 | 282 | 4516 | 70 | 183 | 1100 |
| i5-13600K | 19 | on | replica | 5.03 | 1099 | 596 | 313 | 4468 | 48 | 150 | 866 |
| i5-13600K | 18 | off | minimal | 4.8 | 1310 | 625 | 319 | 4364 | 50 | 151 | 859 |
| R9 9950X | 18 | on | replica | 4.45 | 1149 | 673 | 269 | 4425 | 70 | 181 | 1130 |

Apple Studio and NVIDIA Spark on this Planet are PG17/16/18 rows on the [live board]({{ '/leaderboards/' | relative_url }}); they are not 19rc1. Court Spark PG19 OSM set 5 is enough to start and is not on this ranking table.
