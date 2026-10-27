---
layout: home
title: "OSM Leaders: Performance vs. Power"
permalink: /leaderboards/osm-performance-power/
parent: Leaderboards
nav_order: 1
---

# OSM Leaders: Performance vs. Power

Disk and package-power detail behind the [OSM leaderboard]({{ '/leaderboards/' | relative_url }}).

<!-- osm-leaderboard-compare:begin -->

One chart for the same best-score run on each machine, sorted by OSM score. Bar length is relative to the lead system, on that metric (**100%** = that system's value). Labels are the raw values. A longer **kJ** bar means more energy used, not more efficiency.

![osm2pgsql Load Time - System Comparison]({{ '/images/osm-leaderboard-compare.png' | relative_url }})

<!-- osm-leaderboard-compare:end -->

<!-- osm-leaderboard-joules:begin -->

![OSM score vs package energy]({{ '/images/osm-leaderboard-joules.png' | relative_url }})

Speed vs energy for the best run on each machine at ~128GB RAM. **Score** is OSM kNodes/s; **kJ** is total package energy (joules, shown as kilojoules) from the 1-second power integral over the test window. NVIDIA DGX Spark package watts come from the open [spark_hwmon](https://github.com/antheas/spark_hwmon) module, not an NVIDIA-shipped sensor path.

You can potentially triple the score running on the fastest x86 instead of ARM, but it costs 4–5× as much energy to juice up the processors to do it. **R9 9950X** scores **1480** at **1046 kJ**; **Apple M4 Max Studio** scores **578** at **224 kJ** (**2.6×** score, **4.7×** joules). Versus NVIDIA Grace the score ratio is **2.6×** (1480 vs 570).

<!-- osm-leaderboard-joules:end -->

<!-- osm-leaderboard-traces:begin -->

The board leader is **R9 9950X** (PostgreSQL 19, `fsync=off`, OSM score **1480**). Both traces are minute buckets of the owned **1-second** collectors on that run: Average is what a minute-grained sample would report; Maximum is the peak 1-second reading in that minute — the cliffs a delegated 60-second poll never stored. Disk is combined read+write on data volume `nvme2n1`.

![OSM leader disk average vs 1-second maximum]({{ '/images/osm-leaderboard-disk.png' | relative_url }})

![OSM leader package power average vs 1-second maximum]({{ '/images/osm-leaderboard-power.png' | relative_url }})

The power-efficiency leader is **Apple M4 Max Studio** (PostgreSQL 18, `fsync=off`, **16.1** score/W, OSM score **561**). Disk is Darwin combined throughput (`disk0_MB/s`); there is no read/write split.

![OSM efficiency-leader disk average vs 1-second maximum]({{ '/images/osm-leaderboard-efficiency-disk.png' | relative_url }})

![OSM efficiency-leader package power average vs 1-second maximum]({{ '/images/osm-leaderboard-efficiency-power.png' | relative_url }})

<!-- osm-leaderboard-traces:end -->

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-leaderboard.py --from-db` (runs `reports/osm-leaderboard.sql`; table on `/leaderboards/`, disk and power here).
