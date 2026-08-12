---
layout: home
title: OSM Power
permalink: /results-summary/pg18/osm-power/
parent: PostgreSQL 18
nav_order: 1
---

# OSM Power

OSM load throughput vs package power draw.

![OSM throughput vs maximum package power]({{ '/images/pg18-osm-power.png' | relative_url }})

Each CPU is positioned by **maximum package watts** during the load. Grey vertical bars connect index and total throughput at the same power envelope. Faster AMD parts (R9 9950X, R5 9600X) lead on raw **kNodes/s**; Apple M4 Max draws far less power (**23 W** peak) while giving up top-end speed.

![OSM throughput per watt]({{ '/images/pg18-osm-power-efficiency.png' | relative_url }})

Throughput per peak watt favors efficiency cores—**Apple M4 Max** leads on both total and index load, while high-TDP desktop chips move more data overall but at lower kNodes/s per watt. Rows marked `est` in the table lacked average-power samples; charts use **max_pkg** because every CPU has it.

Regenerate: `python3 reports/osm-power.py` (reads `docs/results-summary/pg18/osm-power.md`).

_Snapshot of the [Streamlit explorer — down between releases](https://pgbent.streamlit.app/) (OSM Power) on 2026-08-09._
_Captured by `explorer/snapshot-streamlit.py` from the live site._


_Query returned 7 rows._

| cpu | mem_gb | nodes_kips | index_kips | pwr_est | max_pkg | avg_pkg | fsync | wal | avg_write | max_write | avg_read | max_read | cpu_c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R9 9950X | 124 | 758.0 | 366.0 |  | 167.0 | 75.0 | off | 21.2 | 83.0 | 7282.0 | 66.0 | 5763.0 | #ED1C24 |
| R5 9600X | 124 | 733.0 | 295.0 |  | 89.0 | 47.0 | off | 20.2 | 81.0 | 5566.0 | 64.0 | 6642.0 | #ED1C24 |
| i9-14900K | 125 | 685.0 | 256.0 | est | 180.0 |  | off | 20.5 | 83.0 | 7763.0 | 68.0 | 5603.0 | #0071C5 |
| i5-13600K | 188 | 646.0 | 274.0 |  | 129.0 | 47.0 | off | 17.8 | 52.0 | 8230.0 | 41.0 | 5848.0 | #0071C5 |
| i3-13100 | 125 | 536.0 | 193.0 | est | 75.0 |  | on | 43.0 | 67.0 | 4141.0 | 47.0 | 4329.0 | #0071C5 |
| Apple M4 Max | 128 | 463.0 | 273.0 |  | 23.0 | 8.0 | off | 12.8 | 348.0 | 4763.0 | 348.0 | 4763.0 | #555555 |
| NVIDIA P4242 | 119 | 425.0 | 252.0 |  | 64.0 | 25.0 | off | 11.7 | 137.0 | 6597.0 | 112.0 | 6625.0 |  |
