---
layout: home
title: OSM Dirty Memory
permalink: /results-summary/pg18/osm-dirty-memory/
parent: PostgreSQL 18
nav_order: 5
---

# OSM Dirty Memory

Linux dirty memory limits during OSM load.

![OSM load throughput vs peak dirty memory]({{ '/images/pg18-osm-dirty-memory.png' | relative_url }})

Each point is a host-local OSM load on **siren** (128GB RAM, fast SSD) at a different Linux dirty-memory cap. Throughput stays near **700** kNodes/s from the **default ~13.4GB** dirty cache down to a **95MB** byte limit—only a mild drop below 1GB. On this SSD, a large Dirty cache is not buying much; a few GB is enough to keep the drive fed.

Regenerate: `python3 reports/osm-dirty-memory.py` (reads `docs/results-summary/pg18/osm-dirty-memory.md`).

_Snapshot of the [Streamlit explorer — down between releases](https://pgbent.streamlit.app/) (OSM Dirty Memory) on 2026-08-09._
_Captured by `explorer/snapshot-streamlit.py` from the live site._


_Query returned 9 rows._

| batch | hours | nodes | nodes_kips | index_kips | max_dirty | wal_mbps | avg_write_mbps | max_write_mbps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sk41 disk | 3.16 | 8039181739.0 | 706.0 | 298.0 | 12659957760 | 19.5 | 113.0 | 3626.0 |
| sk41 disk | 3.15 | 8039181739.0 | 709.0 | 309.0 | 14284529664 | 19.6 | 115.0 | 3955.0 |
| sk41 disk | 3.14 | 8039181739.0 | 710.0 | 310.0 | 14405595136 | 19.6 | 115.0 | 2516.0 |
| Dirty ratios 5/10 | 3.19 | 8039181739.0 | 700.0 | 306.0 | 7828504576 | 19.3 | 114.0 | 3312.0 |
| Dirty ratios 1/2 | 3.16 | 8039181739.0 | 707.0 | 306.0 | 1414533120 | 19.5 | 115.0 | 3287.0 |
| Dirty ratios 2/4 | 3.16 | 8039181739.0 | 707.0 | 304.0 | 2750353408 | 19.5 | 115.0 | 3654.0 |
| Dirty bytes 1000MB/500MB | 3.2 | 8039181739.0 | 699.0 | 295.0 | 992743424 | 19.3 | 114.0 | 3595.0 |
| Dirty bytes 500MB/250M | 3.17 | 8039181739.0 | 705.0 | 300.0 | 481751040 | 19.5 | 113.0 | 3387.0 |
| Dirty bytes 100MB/50MB | 3.2 | 8039181739.0 | 699.0 | 294.0 | 99667968 | 19.3 | 114.0 | 2288.0 |
