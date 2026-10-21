---
layout: home
title: Plotting migration (gnuplot → Python)
permalink: /plans/plotting/
parent: Development plans
nav_order: 3
---

# Plotting migration (gnuplot → Python)

Replace legacy gnuplot scripts with database-driven Python graphs. Pandas/Matplotlib is already used for recent slides and social posts; gnuplot remains in `webreport` and `plots/*.plot`.

## Goal

One plotting stack reading from the results database, without time-averaging away peak GB/s behavior the metric collector was built to preserve.

## Milestones

- [x] `metview.py` — graph every metric for one test run ([metview.md](metview.md))
- [x] Multi-line avg/max overlay — first use is the OSM leaderboard disk + power pair (`reports/metric_series.py`, `osm-leaderboard.py --from-db`); same helper is the start of grouped-settings overlays
- [ ] `metview.py` — **priority range** (`metrics_info.visibility` / decode `vis`); default top band; drill-down requests the next band only (e.g. 5-6 after 7-9); see [metview.md](metview.md)
- [ ] `metview.py` — **stacked groups** for CPU (user/system/idle/wait → 100%×cores) and Linux memory (free/cached/dirty/… → MemTotal); see [metview.md](metview.md) § Stacked metric groups
- [ ] **Latency (gnuplot `plots/latency.plot` + 2007 ingest)** — Python plots with per-outlier markers. Side of the same job: stop `COPY`ing every `pgbench -l` row into `timing` just to summarize by second (`tests` avg/max/P90, `latency_1s.csv`). That import is 2007 code, not built for millions of TPS; at ~2M TPS it is a second heat spike. `SCRIPT=nothing` sockets simple peaks at **3.96M at 32 clients** (~360M rows); prepared is **3.68M**. On siren the pipeline filled the **31GB free** then (`pgbench.log` + `sort` + `timing.csv`; old uncompressed upload archives), so the `;` 32/64 latency columns never landed. Boot drive is back to **121GB free** after clearing those. After `constant` finishes, re-run `nothing` at 32 and 64 (sockets simple and prepared) so avg/P90/max and package watts land on the protocol floor. The ingest is still too heavy at this TPS. Summarize **outside** the DB with pandas/numpy; keep full `timing` COPY as opt-in. Mark Wong’s tools did this in Perl; do not add a Perl path. Existing: `log-to-csv`, `export-latency-metric.sql`.
- [ ] Replace `webreport` gnuplot output with Python (test-set comparison grids)
- [ ] **Parameter-space explorer** — pivot UI over the five benchmark dimensions ([goals.md](goals.md)); successor to crosstab gnuplot + manual `GROUP BY` reports
- [ ] Deprecate `plots/*.plot` once parity is reached

## Backlog (older ideas)

- Graphs for buffers/checkpoints throughout a run
- Fix static scale/client lists in `rates_webreport`
- Fix zombie files when a benchmark crash leaves OS stats processes behind

## References

- Legacy: `plots/`, `./webreport`, `./rates_webreport`, `./limited_webreport`
- New: `metview.py`, `reports/metric_series.py`, `reports/compare.py`, `reports/bars.py`, `collectPandas`
