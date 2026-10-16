---
layout: home
title: Published results snapshots
permalink: /plans/results-snapshot/
parent: Development plans
nav_order: 5
---

# Published results snapshots

Freeze published study tables into static Markdown on getbent.io—one
subdirectory per PostgreSQL major version (starting with **pg18/**).

**PG18** published live on [Streamlit](https://pgbent.streamlit.app/) first,
then snapshotted here. **PG19** skips hosted Streamlit (no sponsor / no paid
hosting): the deliverable is **study SQL** plus static pages and graphs under
`docs/results-summary/pg<N>/`. Explorer code may remain for local use; do not
treat re-enabling Streamlit Cloud as part of this cycle.

## Publication paths

| Path | Role |
|------|------|
| **Leaderboards** (`docs/leaderboards.md` → `/leaderboards/`) | Public OSM + pgbench SELECT ranking URL; refresh when new cells land |
| **Results summary** (`docs/results-summary/pg<N>/`) | Full study tables on getbent.io; **primary archive for PG19** |
| **Study SQL** (`reports/*.sql` and/or `explorer/submission_studies.py`) | Query that defines each study |
| **Streamlit** (`explorer/submission-explore.py`) | PG18 path / optional local; not hosted for PG19 |

## Snapshot from the live site (no database)

The script loads the live app in headless Chromium, selects each study via the radio buttons, and pulls the full table via Streamlit's **Download data as CSV** button (the on-screen dataframe is virtualized and only shows ~12 rows).

```bash
pip install -r explorer/requirements-snapshot.txt
playwright install chromium
python3 explorer/snapshot-streamlit.py --pg 18
```

Writes `docs/results-summary/pg18/<study-id>.md` for all seven sections:

| Study id | Streamlit label |
|----------|-----------------|
| `osm-power` | OSM Power |
| `osm-leaderboard` | OSM Leaderboard |
| `osm-network` | OSM Network |
| `osm-checkpoint` | OSM Checkpoint |
| `osm-dirty-memory` | OSM Dirty Memory |
| `pgbench-build` | pgbench Build Time |
| `pgbench-select` | pgbench SELECT |

Review tables, commit, and link from getbent.io `/results-summary/pg18/`.

## Snapshot from results database (preferred for PG19)

With read access to the `submission` view:

```bash
python3 explorer/archive-results.py --pg 19
```

Same output layout when studies are registered in `submission_studies.py`.
Otherwise export each study’s SQL result into
`docs/results-summary/pg<N>/<study>.md` by hand (or from `reports/*.sql`).

## Workflow (PG 18)

1. [x] Run `snapshot-streamlit.py` (or `archive-results.py` if DB available)
2. [x] Review and commit `docs/results-summary/pg18/*.md`
3. [x] Link from docs index / tuning pages
4. [x] Pause Streamlit Cloud hosting — explorer code kept; **PG19 does not resume hosting**

## Workflow (PG 19)

1. [ ] Per study: write SQL → graph → page under `docs/results-summary/pg19/`
2. [ ] Prefer `archive-results.py` or direct SQL export; do not require Streamlit Cloud
3. [ ] Link from docs index / tuning pages when the cycle closes

## Milestones

- [x] `explorer/submission_studies.py` — SQL for live Streamlit app
- [x] `explorer/snapshot-streamlit.py` — crawl live site → Markdown
- [x] `explorer/archive-results.py` — optional DB export
- [x] `submission-explore.py` uses `study_sql()`
- [x] `docs/results-summary/` hub + `pg18/` index
- [x] PG 18 study `.md` files captured via snapshot script
- [x] PG 18 study `.md` files committed
- [x] Site links updated
