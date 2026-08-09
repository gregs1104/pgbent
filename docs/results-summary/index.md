---
layout: home
title: Results summary
permalink: /results-summary/
nav_order: 6
has_children: true
---

# Results summary

Static snapshots of published benchmark studies—the same tables as the [Streamlit results explorer](https://pgbent.streamlit.app/).

Streamlit is the **live** explorer for current work (PG 19 will publish there first). Each major release gets a **snapshot** here: captured by clicking through every study on the live site (or from the results database when available).

## By PostgreSQL version

| Version | Contents |
|---------|----------|
| [PostgreSQL 18]({{ '/results-summary/pg18/' | relative_url }}) | OSM leaderboard, power, network, checkpoint, dirty memory; pgbench build and SELECT |

## Capturing a snapshot

From the live Streamlit app (no database required):

```bash
pip install -r explorer/requirements-snapshot.txt
playwright install chromium
python3 explorer/snapshot-streamlit.py --pg 18
```

Optional, if you have the results DB: `python3 explorer/archive-results.py --pg 18`

Details: `docs/plans/results-snapshot.md`.
