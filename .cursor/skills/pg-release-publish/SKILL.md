---
name: pg-release-publish
description: >-
  Assemble and publish pgbent studies for a PostgreSQL release cycle such as
  PG19: turn newset-flagged test sets collected on several machines into study
  SQL, add the study to the live Streamlit explorer, graph it with
  reports/*.py --pg N, write its getbent.io page, and snapshot the cycle into
  docs/results-summary/pg<N>/ when the release is finished. Use when a study's
  data is in (via upload/download) and needs assembling, or when closing out
  a release cycle.
disable-model-invocation: true
---

# Assembling and publishing release studies

A release starts with no published studies. Each study is opened with `newset`
on some number of machines (see `pg-release-runs`). Once enough of those machines
have uploaded, the study is assembled and published on its own schedule, alongside
others still collecting. When the cycle ends, all published studies are snapshotted
into static pages.

PG18 is the reference. It ended with seven studies: OSM leaderboard, power,
network, checkpoint, and dirty memory, plus pgbench build and SELECT. They were added
one at a time between October 2025 and January 2026. Treat them as **examples
to reuse when a topic recurs**, not as a template every release must fill.

## Assemble one study

```
Study: <slug>
- [ ] 0. ./download on the assembly machine to pull in new uploads
- [ ] 1. Find the study's sets in central submission
- [ ] 2. Write the study SQL
- [ ] 3. Register it in the explorer and snapshot list
- [ ] 4. Graph it
- [ ] 5. Write the page (can wait for cycle close)
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

Add an entry to `STUDIES` in `explorer/submission_studies.py`, with `title`,
`description`, and `sql` ending in `{pg_filter}`. Copy the closest PG18 study:

| Pattern | Example | Selection |
|---------|---------|-----------|
| Best run per configuration | `osm-leaderboard`, `osm-power` | `ROW_NUMBER() OVER (PARTITION BY cpu, ...)`, `r=1` |
| Variable sweep | `osm-checkpoint`, `osm-network` | Partition by the swept column (`timeout`, `conn`) |
| Single-machine set range | `osm-dirty-memory` | `server='siren' AND batch_id BETWEEN 35 AND 41` |
| All runs of a script | `pgbench-build`, `pgbench-select` | `script LIKE ':-i%'` / `script='select'` |

For a multi-machine study, select by `batch` prefix (or explicit server/batch_id
pairs) rather than relying only on `category IS NULL`. The live explorer calls
`study_sql(id)` **without** a version filter, so the SQL itself must exclude other
releases' runs. Check the result with `python3 explorer/archive-results.py --pg <N> --study <slug>`.

### 3. Register

All four of these must agree, and the radio order must match the snapshot list order:

- `STUDIES` in `explorer/submission_studies.py`
- `explorer/submission-explore.py`: a fetch function, plus a label and caption in the `st.radio` list
  and a dispatch branch in `builtin_query()`
- `STUDIES` list in `explorer/snapshot-streamlit.py` (`(id, radio label, description)`)
- (cycle close) the link in `docs/results-summary/pg<N>/index.md`

Run the explorer locally with `explorer/run` (`streamlit run explorer/submission-explore.py`).
The hosted app is https://pgbent.streamlit.app/ (Streamlit Cloud, paused between
releases). Credentials go through `st.connection` and are kept out of git.

### 4. Graph

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

### 5. Study page

Model it on `docs/results-summary/pg18/osm-power.md`:

1. Front matter with `parent: PostgreSQL <N>` and the permalink `/results-summary/pg<N>/<study>/`
2. A one-line statement of the study question
3. Image embed: `![alt]({{ '/images/pg<N>-<name>.png' | relative_url }})`
4. One paragraph per chart naming the leaders with **bold** numbers taken from the table
5. Which machines and sets took part (the `batch` descriptions)
6. A "Regenerate:" line giving the exact `reports/*.py --pg <N>` command
7. The snapshot provenance line, then the table

Where the same topic ran last release, compare like with like (same CPU, same
config). That comparison is the regression result.

## Close out the cycle

```bash
pip install -r explorer/requirements-snapshot.txt && playwright install chromium
python3 explorer/snapshot-streamlit.py --pg <N>          # every study in its STUDIES list
# or, with results DB access:
python3 explorer/archive-results.py --pg <N>
```

**Snapshots overwrite study pages.** If pages already carry hand-written prose,
images, or extra tables (PG18's `osm-power.md` has a hand-added
`## Relation power efficiency` table that `osm-relation-power.py` reads), snapshot
into a scratch directory (`--output <dir>`) and merge the tables by hand.

```
- [ ] Snapshot every published study; re-run graphs with --pg <N> from the snapshot tables
- [ ] pg<N>/index.md lists exactly the studies that ran; renumber nav_order so the newest release sorts first
- [ ] docs/results-summary/index.md: add a row for <N>
- [ ] docs/index.md hero image / results links, README.md results link
- [ ] Tuning-model pages (docs/model/*.md) embed pg<N> charts where a topic was rerun
- [ ] docs/plans/results-snapshot.md: add a "Workflow (PG <N>)" checklist
- [ ] Ask whether to clear the explorer's study list for <N+1> (its studies are now static pages); pause Streamlit hosting
- [ ] Commit "Mark PG<N> results finished."; seed conf/<N+1> from final conf/<N> (pg-release-config)
```

Preview the site locally with `docs/serve` before pushing.
