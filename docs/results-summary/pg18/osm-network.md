---
layout: home
title: OSM Network
permalink: /results-summary/pg18/osm-network/
parent: PostgreSQL 18
nav_order: 3
---

# OSM Network

OSM load speed: server vs remote client.

![OSM load throughput vs client–server link rate]({{ '/images/pg18-osm-network-speed.png' | relative_url }})

The network study uses an R9 9950X client loading onto an i5-13600K server while throttling the link from 100Mb/s through 10Gb/s. Dotted reference lines show the same server with a host-local client (646 kNodes/s total, 274 kNodes/s index). Even at **10Gb/s**, index build on the remote client (**208 kNodes/s**) stays below that i5 host-local baseline; total load reaches **666 kNodes/s**, in line with the on-server client. Below **2.5Gb/s**, both phases degrade—the 100Mb/s case drops to **90 kNodes/s**.

Comparing host-local results across different CPUs (for example R9 vs i5) is not apples-to-apples here; a fair cross-system claim would need matched client/server hardware or bidirectional remote tests in both directions.

Regenerate: `python3 reports/osm-network-speed.py` (reads `docs/results-summary/pg18/osm-network.md`).

_Snapshot of the [Streamlit explorer — down between releases](https://pgbent.streamlit.app/) (OSM Network) on 2026-08-09._
_Captured by `explorer/snapshot-streamlit.py` from the live site._


_Query returned 9 rows._

| client | server | conn | overall_kips | polygon_kips | line_kips | point_kips | node_kps | index_kips | wal_mbps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Apple M4 Max  128GB Apple AP2048Z | Apple M4 Max | host | 463.0 | 2375.0 | 3751.0 | 6849.0 | 12582.0 | 273.0 | 12.8 |
| R9 9950X  128GB SK51 2TB | Apple M4 Max Studio | 10000 | 614.0 | 2612.0 | 4190.0 | 7912.0 | 20839.0 | 303.0 | 16.9 |
| R9 9950X  124GB SK51 2TB | R9 9950X | host | 758.0 | 3440.0 | 7046.0 | 4741.0 | 20885.0 | 366.0 | 21.2 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 10000 | 666.0 | 1857.0 | 3085.0 | 3328.0 | 17225.0 | 208.0 | 18.4 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 5000 | 625.0 | 2247.0 | 4068.0 | 3535.0 | 16208.0 | 245.0 | 17.3 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 2500 | 505.0 | 1942.0 | 3510.0 | 2756.0 | 13530.0 | 204.0 | 14.7 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 1000 | 428.0 | 1941.0 | 3544.0 | 2769.0 | 10148.0 | 204.0 | 12.4 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 100 | 90.0 | 1214.0 | 1808.0 | 1815.0 | 1468.0 | 122.0 | 2.6 |
| i5-13600K  188GB Fury G5 4TB | i5-13600K | host | 646.0 | 2410.0 | 5248.0 | 3778.0 | 11984.0 | 274.0 | 17.8 |
