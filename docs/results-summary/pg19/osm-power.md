---
layout: home
title: OSM Power
permalink: /results-summary/pg19/osm-power/
parent: PostgreSQL 19
nav_order: 2
---

# OSM Power

OSM load throughput vs package power draw on the current Planet (**10.79 billion** nodes). **R9 9950X**, **i5-13600K**, and **NVIDIA Spark** are PostgreSQL 19; **Apple M4 Max Studio** is PG18 (no 19 on Abbey during RC). 18 and 19 are within a small tolerance on this workload. Package watts for the 9950X are turbostat `PkgWatt` from the corrected siren import. Ranking cells for this pin: [OSM Leaderboard]({{ '/results-summary/pg19/osm-leaderboard/' | relative_url }}).

![OSM total throughput vs maximum package power]({{ '/images/pg19-osm-power-total.png' | relative_url }})

Each CPU is positioned by **maximum package watts** during the load. Points are the **~128 GB RAM** class so twilight’s physical **188 Gi** cell does not inflate the i5. **R9 9950X** leads on raw total throughput at **719** kNodes/s and **180 W** peak (PostgreSQL 19, `fsync=off`). **i5-13600K** is next at **599** kNodes/s and **150 W** (125 Gi / mem=128G). **Apple M4 Max Studio** reaches **400** kNodes/s at **35 W**. **NVIDIA P4242** hardware-best 19rc1 is **392** kNodes/s total (**570** OSM score, **7.65h**, `max_wal_size=256GB`) after the fair-tuning pass.

![OSM index throughput vs maximum package power]({{ '/images/pg19-osm-power-index.png' | relative_url }})

Index build only—**i5-13600K** leads raw index throughput at **383** kNodes/s. **NVIDIA Spark** is **263** kNodes/s at **89 W**; **Apple M4 Max Studio** is **171** kNodes/s at **35 W**.

![OSM throughput per watt]({{ '/images/pg19-osm-power-efficiency.png' | relative_url }})

Throughput per peak watt favors Apple Silicon. **Apple M4 Max Studio** leads on both total and index load. Spark’s 19rc1 peak (**89 W**) puts it with the desktop Intel/AMD parts on kNodes/s per watt; the **9950X** still moves the most nodes overall at the highest envelope.

You can potentially triple the OSM score running on the fastest x86 instead of ARM, but it costs 4–5× as much energy to juice up the processors to do it. This workload does not benefit very much from larger core or socket counts. Relation building does not fill a second CCD or a second socket; extra cores mostly add package watts. The 9600X→9950X swap barely moved OSM score.

Regenerate throughput charts: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-power.py --pg 19` (reads the first table below). Query: `reports/osm-power.sql` (mem_gb ≤ 140). The table pins PostgreSQL 19 per CPU; Abbey is the PG18 stand-in. The live query still picks the best score on any major within the ~128 GB class.

Sets: siren 71 (`PG19 beta4`); twilight **120** (`PG19 rc1 OSM mem=128G fast`); court 5 (`PG19 rc1`); abbey 11 (`PG18`).

_Query returned 4 rows._

| cpu | mem_gb | ver | score_kips | overall_kips | index_kips | polygon_kips | line_kips | point_kips | node_kps | rel_ps | pwr_est | max_pkg | avg_pkg | kj | fsync | wal_level | wal | avg_write | max_write | avg_read | max_read | cpu_c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R9 9950X | 124 | 19 | 1480 | 719 | 364 | 3925 | 8225 | 3731 | 20555 | 4529 |  | 180 | 70 | 1046 | off | minimal | 20.4 | 79 | 7772 | 68 | 9748 | #ED1C24 |
| i5-13600K | 125 | 19 | 1213 | 599 | 383 | 3067 | 5827 | 7142 | 14602 | 4146 |  | 150 | 46 | 833 | off | minimal | 52.8 | 58 | 7331 | 41 | 8970 | #0071C5 |
| Apple M4 Max Studio | 128 | 18 | 561 | 400 | 171 | 1662 | 2699 | 2743 | 12519 | 1674 |  | 35 | 9 | 276 | off | minimal | 11.3 | 325 | 6125 | 325 | 6125 | #000000 |
| NVIDIA P4242 | 119 | 19 | 521 | 361 | 263 | 2434 | 3694 | 5674 | 16227 | 1095 |  | 89 | 23 | 701 | off | minimal | 10.3 | 124 | 6351 | 110 | 9627 | #76B900 |

## Relation power efficiency

Relation-build throughput during OSM planet load, normalized by **average** package watts over the full run (not peak).

![OSM relation throughput per average watt]({{ '/images/pg19-osm-relation-power.png' | relative_url }})

**Apple M4 Max Studio** leads at **186** relations per watt (**1674** rel/s at **9 W** average). **i5-13600K** is next among the desktops at **90** rel/W; **R9 9950X** moves the most relations overall (**4529** rel/s) at **70 W** average. Spark is **48** rel/W (**1095** rel/s at **23 W**).

![OSM relation throughput vs average power]({{ '/images/pg19-osm-relation-scatter.png' | relative_url }})

The scatter view shows the same data directly: desktop AMD and Intel sit at **46–70 W** average with the highest relation rates; Apple stays in the lower-left with the best **rel_per_watt**.

![OSM relations/second vs full-run package energy]({{ '/images/pg19-osm-relation-joules.png' | relative_url }})

Same **full-run package energy** as the leaderboard score-vs-kJ chart, against **relations/second** instead of OSM score. Some of those joules went to nodes, ways, and indexes—this is a zoom-in, not a phase-isolated integral. **R9 9950X** leads relation rate (**4529** rel/s) at **1046 kJ**; **i5-13600K** is **4146** rel/s at **833 kJ**. Apple stays cheap (**276 kJ**, **1674** rel/s). Spark is **701 kJ** at **1095** rel/s.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-relation-power.py --pg 19` (reads the relation table below).

| cpu | ver | rel | avg_watts | max_watts | rel_per_watt | kj | cpu_c |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Apple M4 Max Studio | 18 | 1674 | 9 | 35 | 186 | 276 | #000000 |
| i5-13600K | 19 | 4146 | 46 | 150 | 90 | 833 | #0071C5 |
| R9 9950X | 19 | 4529 | 70 | 180 | 65 | 1046 | #ED1C24 |
| NVIDIA P4242 | 19 | 1095 | 23 | 89 | 48 | 701 | #76B900 |
