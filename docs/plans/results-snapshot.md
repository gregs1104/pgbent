# Published results snapshots

Freeze what the [Streamlit results explorer](https://pgbent.streamlit.app/) shows into static Markdown tables on getbent.io—one subdirectory per PostgreSQL major version (starting with **pg18/**).

This is **documentation of published results**, not a replacement for Streamlit. The explorer code stays; PG 19 and later publish live on Streamlit first, then get snapshotted here when a cycle is done.

## Two publication paths

| Path | Role |
|------|------|
| **Streamlit** (`explorer/submission-explore.py`) | Live, interactive explorer |
| **Results summary** (`docs/results-summary/pg<N>/`) | Static snapshot on getbent.io |

Shared SQL for the live app: `explorer/submission_studies.py`.

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

## Optional: snapshot from results database

If you still have read access to the `submission` view:

```bash
python3 explorer/archive-results.py --pg 18
```

Same output layout; uses `submission_studies.py` SQL directly.

## Workflow (PG 18)

1. [ ] Run `snapshot-streamlit.py` (or `archive-results.py` if DB available)
2. [ ] Review and commit `docs/results-summary/pg18/*.md`
3. [ ] Link from docs index / tuning pages
4. [ ] Optionally pause Streamlit Cloud hosting until the next release cycle—**keep all explorer code** for PG 19

## Milestones

- [x] `explorer/submission_studies.py` — SQL for live Streamlit app
- [x] `explorer/snapshot-streamlit.py` — crawl live site → Markdown
- [x] `explorer/archive-results.py` — optional DB export
- [x] `submission-explore.py` uses `study_sql()`
- [x] `docs/results-summary/` hub + `pg18/` index
- [x] PG 18 study `.md` files captured via snapshot script
- [ ] PG 18 study `.md` files committed
- [ ] Site links updated
