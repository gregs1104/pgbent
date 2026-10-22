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
- [ ] **Latency (gnuplot `plots/latency.plot` + 2007 ingest)** — Python plots with per-outlier markers. Do **not** drop the per-row `COPY` as the default just to go faster: siren set 107 test **3252** (`;` sockets prepared, 64 clients, 3.65M TPS) is avg 7 μs / P90 0 / max **1.45 s**. The max looks like a pgbench artifact until the scatter shows 200 ms–1.5 s stalls repeating on a microsecond floor. P90 0 is the 20-bucket `OFFSET` dying at ~328M rows, not a real percentile. Summarize **outside** the DB with pandas/numpy for the buckets; keep full `timing` COPY. Mark Wong’s tools did this in Perl; do not add a Perl path. Existing: `log-to-csv`, `export-latency-metric.sql`. `nothing` sockets simple now peaks at **4.05M at 32 clients**; prepared **3.81M**. First 32/64 pass filled **31GB**; re-run after 121GB free landed TPS and max.
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
