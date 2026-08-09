# Plotting migration (gnuplot → Python)

Replace legacy gnuplot scripts with database-driven Python graphs. Pandas/Matplotlib is already used for recent slides and social posts; gnuplot remains in `webreport` and `plots/*.plot`.

## Goal

One plotting stack reading from the results database, without time-averaging away peak GB/s behavior the metric collector was built to preserve.

## Milestones

- [x] `metview.py` — graph every metric for one test run ([metview.md](metview.md))
- [ ] `metview.py` — default minimal metric set (TPS, latency, dirty memory); `--verbose` for all
- [ ] Latency plots with per-outlier markers (gnuplot cross-symbol equivalent in `plots/latency.plot`)
- [ ] Replace `webreport` gnuplot output with Python (test-set comparison grids)
- [ ] **Parameter-space explorer** — pivot UI over the five benchmark dimensions ([goals.md](goals.md)); successor to crosstab gnuplot + manual `GROUP BY` reports
- [ ] Deprecate `plots/*.plot` once parity is reached

## Backlog (older ideas)

- Graphs for buffers/checkpoints throughout a run
- Fix static scale/client lists in `rates_webreport`
- Fix zombie files when a benchmark crash leaves OS stats processes behind

## References

- Legacy: `plots/`, `./webreport`, `./rates_webreport`, `./limited_webreport`
- New: `metview.py`, `reports/compare.py`, `reports/bars.py`, `collectPandas`
