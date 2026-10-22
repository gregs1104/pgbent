---
layout: home
title: Results summary
permalink: /results-summary/
nav_order: 6
has_children: true
---

# Results summary

Static snapshots of published benchmark studies. The public ranking URL is **[Leaderboards]({{ '/leaderboards/' | relative_url }})** (OSM and pgbench SELECT). This tree keeps the full study tables. Streamlit stays a local grid for comparing loaded versions—not the hosted site.

## By PostgreSQL version

| Version | Contents |
|---------|----------|
| [PostgreSQL 19]({{ '/results-summary/pg19/' | relative_url }}) | 19rc1 starting snapshot: OSM ranking, OSM power, pgbench SELECT |
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
