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

| client | server | conn | nodes_kips | index_kips | wal_mbps |
| --- | --- | --- | --- | --- | --- |
| Apple M4 Max  128GB Apple AP2048Z | Apple M4 Max | host | 463.0 | 273.0 | 12.8 |
| R9 9950X  128GB SK51 2TB | Apple M4 Max Studio | 10000 | 614.0 | 303.0 | 16.9 |
| R9 9950X  124GB SK51 2TB | R9 9950X | host | 758.0 | 366.0 | 21.2 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 10000 | 666.0 | 208.0 | 18.4 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 5000 | 625.0 | 245.0 | 17.3 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 2500 | 505.0 | 204.0 | 14.7 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 1000 | 428.0 | 204.0 | 12.4 |
| R9 9950X  128GB SK51 2TB | i5-13600K | 100 | 90.0 | 122.0 | 2.6 |
| i5-13600K  188GB Fury G5 4TB | i5-13600K | host | 646.0 | 274.0 | 17.8 |
