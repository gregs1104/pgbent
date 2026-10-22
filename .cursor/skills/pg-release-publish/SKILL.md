---
name: pg-release-publish
description: >-
  Assemble and publish pgbent studies for a PostgreSQL release cycle such as
  PG19: turn newset-flagged test sets into study SQL, graph with reports/*.py
  --pg N, write getbent.io pages under docs/results-summary/pg<N>/, and close
  the cycle with static snapshots. Use when a study's data is in (via
  upload/download) and needs assembling, or when closing out a release cycle.
  PG19 does not use hosted Streamlit.
disable-model-invocation: true
---

# Assembling and publishing release studies

A release starts with no published studies. Each study is opened with `newset`
on some number of machines (see `pg-release-runs`). Once enough of those machines
have uploaded, the study is assembled and published on its own schedule, alongside
others still collecting. When the cycle ends, published studies live as static
pages on getbent.io.

**Last step of every study:** write a **query** that shows the result grid
(means across the 3–5 repeats, axes the study mapped). That SQL is the analysis
artifact. Graphs and Markdown pages consume it; there is no separate product
layer required.

**PG19 publication path:** study SQL → `reports/*.py` / Markdown under
`docs/results-summary/pg<N>/` → getbent.io. **Do not** stand up or pay for
Streamlit Cloud hosting this cycle (no sponsor). Explorer code
(`explorer/submission-explore.py`, `submission_studies.py`) may stay for
optional local runs or PG18 reuse; registering a study in the live app and
re-enabling https://pgbent.streamlit.app/ is **out of scope** unless Greg
explicitly asks.

**PG19 starting snapshot** (19rc1, catalog 20261006) is already under
`docs/results-summary/pg19/`: OSM leaderboard, OSM power, pgbench SELECT.
That is not cycle close. Remaining docs work is **OSM Power** once court
finishes: put a **PG19** NVIDIA P4242 cell on kernel **7.0** into that
table (the live row is still PG16). The other hardware already has
concurrent GIS on 19; leaving Spark on 16 is not a fair mix. The page
can stay public; do not share it as the finished Grace/power story until
that refresh. Network,
checkpoint, dirty-memory, and pgbench-build are not in this snapshot
unless they run. After the 19rc1 results and experiments wrap: OS
upgrades on **siren** and **twilight**, then re-test main SELECT faces
and OSM on the same pin (newset by OS vintage). Do not start that
cutover from docs work.

PG18 is the reference for *what a study looks like*. It ended with seven
studies (OSM leaderboard, power, network, checkpoint, dirty memory, plus
pgbench build and SELECT), published via Streamlit then snapshotted. Treat
those as **examples to reuse when a topic recurs**, not as a checklist every
release must fill, and not as a requirement to host Streamlit again.

## Assemble one study

```
Study: <slug>
- [ ] 0. ./download on the assembly machine to pull in new uploads
- [ ] 1. Find the study's sets in central submission
- [ ] 2. Write the study SQL (required — this is the deliverable)
- [ ] 3. Graph it from that query / a Markdown table export
- [ ] 4. Write the getbent.io page (can wait for cycle close)
- [ ] (optional, local only) Register in explorer/submission_studies.py if useful for ad-hoc browsing
```

### 0. Pull new data

The central results DB is built by `./download`. It imports every archive that
participating machines have `./upload`ed since the last download, and each one fully
replaces that server's data (details in `pg-release-runs`). The `submission`
view is then computed over all servers. If a machine's runs are missing, check
that it uploaded and that its archive filename starts with the right `SERVERNAME`.
Fix wrong set descriptions or categories on the source machine and re-upload.
Don't patch them centrally.

### 1. Find the sets

Studies are keyed by `batch` (the newset description), because `batch_id` is a
per-server serial:

```sql
SELECT server, batch_id, batch, category, count(*) AS runs,
       min(run) AS first_run, max(run) AS last_run,
       string_agg(DISTINCT substring(server_ver FROM 'PostgreSQL ([0-9.]+)'), ',') AS ver
FROM submission
WHERE batch ILIKE '<description prefix>%'
GROUP BY server, batch_id, batch, category ORDER BY server, batch_id;
```

Check with the user that every expected machine is present. Also check that no
set mixes variants and that stray sets don't match the prefix. If two machines used
different descriptions, select those sets explicitly by `(server, batch_id)` pairs.

### 2. Study SQL

This is the **required** finish for the study. Prefer a file under `reports/`
(e.g. `reports/osm-<topic>.sql`) or a `STUDIES` entry in
`explorer/submission_studies.py` if you already use that harness — either way
the query must be runnable against the central `submission` / results views and
stable enough to feed graphs and a Markdown table.

Copy the closest PG18 pattern:

| Pattern | Example | Selection |
|---------|---------|-----------|
| Best run per configuration | `osm-leaderboard`, `osm-power` | `ROW_NUMBER() OVER (PARTITION BY cpu, ...)`, `r=1` |
| Variable sweep | `osm-checkpoint`, `osm-network` | Partition by the swept column (`timeout`, `conn`) |
| Single-machine set range | `osm-dirty-memory` | `server='siren' AND batch_id BETWEEN 35 AND 41` |
| All runs of a script | `pgbench-build`, `pgbench-select` | `script LIKE ':-i%'` / `script='select'` |

For a multi-machine study, select by `batch` prefix (or explicit server/batch_id
pairs) rather than relying only on `category IS NULL`. Exclude other majors in
the SQL (or via `--pg` / a filter fragment) so PG18 rows do not pollute PG19
tables. Export a Markdown/CSV table for the page (`archive-results.py` if the
study is registered locally; otherwise `$RESULTPSQL -c` / `\copy` from the
query file).

### 3. Graph

**A recurring topic** reuses the existing script with `--pg`. That picks
`docs/results-summary/pg<N>/<study>.md`, writes `docs/images/pg<N>-<name>.png`,
and sets release-cycle titles:

| Study | Script |
|-------|--------|
| osm-power | `reports/osm-power.py` (+ `reports/osm-relation-power.py`) |
| osm-leaderboard | `reports/osm-leaderboard.py` |
| osm-network | `reports/osm-network-speed.py` |
| osm-checkpoint | `reports/osm-checkpoint.py` |
| osm-dirty-memory | `reports/osm-dirty-memory.py` |

```bash
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/<script>.py --pg <N>
```

Before the cycle snapshot exists, use `--snapshot <file>` with a CSV-to-Markdown
export of the study query.

**A new topic** gets a new `reports/<study>.py` following the same skeleton:
`release_paths.add_pg_argument` / `snapshot_path` / `image_path`,
`snapshot_table.load_snapshot_table`, `pg18_style.use_pg18_style`, and
`label_layout.place_point_labels` for scatter labels. Follow the `scatter-label-layout` skill.

Review points when reusing PG18 scripts:

- Data-version titles stay hardcoded on purpose: `osm-relation-power.py` ("16-17", "16-18")
  and `osm-dirty-memory.py` ("PostgreSQL 17"). Update them to match the data's `ver`.
- Per-CPU label overrides, `DROP_CPUS`, and NVIDIA P4242 placement are keyed to PG18 hardware.
- `osm-network-speed.py` hardcodes the R9 9950X → i5-13600K pair. `osm-checkpoint.py`'s
  subtitle hardcodes "256GB WAL / 60 min".
- Regression check: running without `--pg` must reproduce the committed `docs/images/pg18-*.png`
  byte for byte (`git status docs/images` stays clean).

### 4. Study page

Model it on `docs/results-summary/pg18/osm-power.md`:

1. Front matter with `parent: PostgreSQL <N>` and the permalink `/results-summary/pg<N>/<study>/`
2. A one-line statement of the study question
3. Image embed: `![alt]({{ '/images/pg<N>-<name>.png' | relative_url }})`
4. One paragraph per chart naming the leaders with **bold** numbers taken from the table
5. Which machines and sets took part (the `batch` descriptions)
6. A "Regenerate:" line giving the exact query / `reports/*.py --pg <N>` command
7. Provenance, then the table from the study SQL

Where the same topic ran last release, compare like with like (same CPU, same
config). That comparison is the regression result.

## Close out the cycle

Prefer DB → Markdown (no hosted Streamlit):

```bash
# With results DB access — preferred for PG19:
python3 explorer/archive-results.py --pg <N>   # if studies are in submission_studies.py
# else: export each reports/*.sql result into docs/results-summary/pg<N>/<study>.md by hand

# Legacy PG18 path only (requires a live Streamlit app — not planned for PG19):
# pip install -r explorer/requirements-snapshot.txt && playwright install chromium
# python3 explorer/snapshot-streamlit.py --pg <N>
```

**Snapshots overwrite study pages.** If pages already carry hand-written prose,
images, or extra tables (PG18's `osm-power.md` has a hand-added
`## Relation power efficiency` table that `osm-relation-power.py` reads), snapshot
into a scratch directory (`--output <dir>`) and merge the tables by hand.

```
- [ ] Every study has runnable SQL and a static page/table under docs/results-summary/pg<N>/
- [ ] Re-run graphs with --pg <N> from those tables
- [ ] pg<N>/index.md lists exactly the studies that ran; renumber nav_order so the newest release sorts first
- [ ] docs/results-summary/index.md: add a row for <N>
- [ ] docs/index.md hero image / results links, README.md results link
- [ ] Tuning-model pages (docs/model/*.md) embed pg<N> charts where a topic was rerun
- [ ] docs/plans/results-snapshot.md: add a "Workflow (PG <N>)" checklist
- [ ] Do not resume Streamlit Cloud unless Greg asks; explorer code can remain unused
- [ ] Commit "Mark PG<N> results finished."; seed conf/<N+1> from final conf/<N> (pg-release-config)
```

Preview the site locally with `docs/serve` before pushing.
