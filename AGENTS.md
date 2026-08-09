# Agent guide

Guidance for AI coding agents working in this repository. Human-oriented documentation lives at [getbent.io](https://getbent.io) (`docs/` in this repo).

Keep changes short and actionable. Preserve shell-script-first orchestration and database-first data flow unless the task explicitly asks otherwise.

## Architecture

- **Shell orchestration** — `benchwarmer`, `runset`, `webreport`, `rates_webreport`, and `limited_webreport` call `pgbench`, `psql`, and OS measurement helpers.
- **Results database** — `init/resultdb.sql` defines the schema (`tests`, `testset`, `timing`, `test_metrics_data`, `metrics_info`, …). Reporting and graphing read from here; do not invent columns. Tests are points in a five-dimensional parameter space (client, scale, script, read/write blend, locality); see [documentation.md](docs/plans/documentation.md) § Benchmark parameter space.
- **Reporting** — SQL in `reports/`; legacy graphs via gnuplot in `plots/`. New work uses Python/Matplotlib/Pandas (`metview.py`, `reports/*.py`). See [docs/plans/plotting.md](docs/plans/plotting.md).
- **Workloads** — under `wl/` and `tests/`; executed by `runset` / `benchwarmer`.

## Workflows

```text
createdb results && psql -f init/resultdb.sql -d results   # once
./newset 'description'                                       # new test set
./runset                                                     # run grid
./benchwarmer <clients>                                      # single run
./webreport | ./limited_webreport 1,6,7 | ./rates_webreport 2,8,9
python3 metview.py <server> <test>                           # per-run metric graphs
```

Streamlit explorer: `explorer/submission-explore.py` (`st.connection` example).

## Conventions

- Shell scripts use `$RESULTPSQL` for results-DB access; follow patterns in `benchwarmer`.
- Register new metrics in `metrics_info`; store samples in `test_metrics_data`.
- `tests.script` holds pgbench script names (`select`, …) or workload names (`osm2pgsql%`).
- Many scripts expect GNU coreutils (`nproc`) and optionally gnuplot. Feature-detect where needed (`webreport`, `rates_webreport`).

## Where to look first

| Task | Start here |
|------|------------|
| Schema / data shape | `init/resultdb.sql` |
| Run orchestration | `benchwarmer`, `runset` |
| SQL reports | `reports/*.sql`, views `test_stats`, `test_metrics_decode`, `test_metrics` |
| Metric usage | `test_metrics_data`, `metrics_info`, then `reports/` |
| Programmatic DB access | `explorer/submission-explore.py` |
| Per-run metric graphs | `metview.py`, [docs/plans/metview.md](docs/plans/metview.md) |
| Plotting migration | [docs/plans/plotting.md](docs/plans/plotting.md) |

## Active plans

Plans live under `docs/plans/` in two categories:

**Implementation** — code to build or migrate:

- [plotting.md](docs/plans/plotting.md) — gnuplot → Python (project-wide)
- [metview.md](docs/plans/metview.md) — per-run metrics grapher

**Documentation** — topics to write for getbent.io when time allows:

- [documentation.md](docs/plans/documentation.md) — documentation backlog

**Long-term goals** — directional ambitions; do not treat as active work unless asked:

- [goals.md](docs/plans/goals.md) — multi-year project direction

Prioritize **Python/Matplotlib** for new graphing work unless the task is explicitly fixing legacy gnuplot output.

## Non-goals

- Do not rewrite shell orchestration in Python unless requested.
- Do not guess schema; read `init/resultdb.sql` or query the DB.
- Do not expand `metview.py` to graph every metric by default without checking the metview plan (minimal vs verbose is planned).

## Known issues

- Solaris: `benchwarmer` may need `/usr/xpg4/bin/tail` instead of `tail`.
- Crashed benchmarks can leave zombie OS stats processes (see [plotting.md](docs/plans/plotting.md) backlog).
