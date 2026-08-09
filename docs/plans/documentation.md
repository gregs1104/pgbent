# Documentation backlog

Topics worth writing for [getbent.io](https://getbent.io) when there is time and focus. These are **documentation plans**, not code tasks—unlike [plotting.md](plotting.md) and [metview.md](metview.md).

## How to use this file

- Check off `- [ ]` → `- [x]` when a page or substantial section ships on the docs site.
- **Existing** links point at partial coverage in repo or docs today.
- Nested bullets mirror the original outline; sub-items can ship independently.

## Already documented (reference)

| Area | Location |
|------|----------|
| Overview, workloads, getting started | `docs/index.md`, `docs/intro.md` |
| Setup, running, results, reports | `docs/setup.md`, `docs/running.md`, `docs/results.md`, `docs/reports.md` |
| Workloads (pgbench, OSM, CBC) | `docs/workloads/` |
| Tuning studies | `docs/model/` |
| Troubleshooting, versions | `docs/troubleshooting.md`, `docs/versions.md` |

---

## Backlog

### Database-first design

Explain how pgbent's feature set and implementation reflect a **database-first** application style: the results DB as the system of record, shell scripts as thin orchestration, SQL views and reports as the primary analysis interface, and graphing/streamlit as consumers—not separate silos of state.

- [ ] **Design essay** — why separate test vs results databases; `$RESULTPSQL`; views over raw tables; auditable workloads vs opaque pipelines
  - Existing: `docs/index.md` § Design philosophy (brief); `docs/intro.md` § Metrics; [AGENTS.md](../../AGENTS.md) § Architecture
  - Tie to: schema hierarchy, query cookbook, set comparisons, replication (this backlog)

### Sample schema

Document the results-database hierarchy: how **server → test set → script → scale → clients → test run** fit together, and what each table holds.

- [ ] **Server / set / script / scale / clients hierarchy**
  - Existing: `init/resultdb.sql` (`server`, `testset`, `tests`); `docs/intro.md` § Test sets; `docs/results.md` § Test sets comparison
  - Include: serial numbers, `testset.info`, multi-server `server` column, relationship to `test_wrap` / summary views

### Basic log format

Document what pgbent writes during a run and how it lands in the results DB.

- [ ] **Queries** — pgbench log lines, latency samples, custom SQL capture format
  - Existing: `timing` table (CSV staging), `tests` summary columns; `export-latency-metric.sql` as OHLC export sketch
- [ ] **Capture automation and process pruning** — how collectors start/stop, zombie cleanup on crash
  - Existing: `benchwarmer`, `metrics2csv`, `util/pgbent_powermon`; known issue in [plotting.md](plotting.md) backlog

### Metric import ideas

- [ ] Patterns for bringing external metrics into `test_metrics_data` (formats, naming, registration in `metrics_info`)
  - Existing: `init/metrics_map.csv`, `metrics_info` prefix/multiplier model, `metview.py` query as consumer example

### Database metrics suggestions

End-to-end guide for Postgres-side metrics collection.

- [ ] **Capture scripts** — periodic SQL attached to a run (`pg_stat_*`, `pg_buffercache`, custom)
- [ ] **Parsing scripts** — shell/Python that normalizes collector output
  - Existing: `metrics2csv`, `util/pgbench-init-parse`, `util/power-sensors-parse`
- [ ] **Intermediate storage**
  - [ ] Multi-column vs single-value metric formats (`test_stat_database` wide rows vs `test_metrics_data` name/value pairs)
  - Existing: `init/resultdb.sql` (`test_stat_database`, `test_statio`, `test_bgwriter`, `test_metrics_data`)

### Sample processing queries

Worked examples readers can run against the results DB.

- [ ] **Latency as a metric** — OHLC and similar time-bucket aggregations over `timing`
  - Existing: `export-latency-metric.sql`; per-second min/avg/max in `metview.py` / `test_metric_summary`
- [ ] **Buffer stats** — reads from `test_bgwriter`, buffer-cache views, checkpoint pressure
  - Existing: `reports/bufreport.sql`, `reports/bufsummary.sql`, `reports/write_internals.sql`
- [ ] **MB/s comparison table** — throughput columns on `test_stats` / submission views
  - Existing: `test_stats` (`hit_bps`, `read_bps`, `check_bps`, …); Streamlit explorer
- [ ] **Views**
  - [ ] Combining test and DB metrics in one query (`test_metrics_decode`, joins to `tests`)
  - [ ] Latency and metrics overlays on a shared time axis
  - [ ] **Overlay builder app** — choose fields to overlay (fun standalone tool; document spec even if unbuilt)
  - Existing: `test_metrics`, `test_metrics_decode`, `test_metric_summary` in `init/resultdb.sql`; `metview.py` (single-metric time series)

### Query aggregation

Patterns for heavy or rolling analysis over large result sets.

- [ ] **Materialized queries** — when to pre-aggregate vs live views
- [ ] **Streaming window** — rolling windows over `test_metrics_data` / `timing` without loading full runs into memory
  - Existing: `date_trunc` grouping in `metview.py`, `reports/` SQL examples

### Set comparisons

- [ ] How test sets are defined, compared, and graphed across configuration changes
  - Existing: `docs/results.md`, `docs/reports.md`; `./webreport`, `./limited_webreport`, `./rates_webreport`; `reports/compromise_params.sql`

### Replication to central node

- [ ] Architecture for consolidating results from multiple benchmark hosts into one results database
  - Existing: multi-`server` schema in `init/resultdb.sql`; `explorer/submission-explore.py`, `explorer/results-bridge.sql` (partial)

### Use

Operator-facing workflows once data is in the results DB.

- [ ] **Web report** — `./webreport` output layout, regeneration, HTML under `results/`
  - Existing: `docs/results.md`; implementation plan in [plotting.md](plotting.md) (gnuplot → Python)
- [ ] **Crosstab comparison charts** — client × scale grids, set-over-set overlays
  - Existing: gnuplot scripts in `plots/`; `reports/compare.py`, `reports/bars.py`
- [ ] **Test CRUD** — insert/update/delete tests and sets, cleanup bad runs
  - Existing: `docs/reports.md` § cleanups; `latest_set`, `list_orderbyset` helpers mentioned in reports doc

---

## Suggested doc structure (when writing)

These topics likely become one or more pages under a new **Results internals** or **Metrics guide** section rather than scattered edits:

0. Database-first design (framing essay)
1. Schema and hierarchy (Sample schema)
2. Capture pipeline (Basic log format + Database metrics suggestions)
3. Storage formats (Intermediate storage)
4. Query cookbook (Sample processing queries + Query aggregation)
5. Comparison and publishing (Set comparisons + Use)
6. Multi-host (Replication)

## Out of scope here

- Agent/developer workflow → [AGENTS.md](../../AGENTS.md)
- Code roadmaps → [plotting.md](plotting.md), [metview.md](metview.md)
- Inline `# TODO` in source → stay near the code

## Writing conventions

- Match tone of `docs/intro.md` and `docs/results.md` for operational guides; `docs/model/*.md` for measured tuning write-ups.
- Link to Streamlit results or `reports/*.sql` when citing examples.
- Images live under `docs/images/` for the Jekyll site.
