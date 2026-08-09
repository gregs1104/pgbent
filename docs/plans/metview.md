---
layout: home
title: metview.py roadmap
permalink: /plans/metview/
parent: Development plans
nav_order: 4
---

# metview.py roadmap

Per-run metrics grapher. Successor to `osm-metrics.py`. Reads the results database and writes one time-series PNG per metric under `results/images/`.

## Status

Works-for-me quality: useful for educational material and tuning write-ups. Database-driven generation is slow; image polish still needed.

## Goal

Replace gnuplot per-run metric graphs (`plots/dirty.plot`, etc.) and eventually support the same views `webreport` produces—without requiring gnuplot.

## Done

- [x] Graph every decoded metric for one `(server, test)` pair
- [x] Plain decimal Y-axis labels (no scientific notation)
- [x] Inherit pgbent metrics conversion (`metrics_info` multipliers, units, labels)

## Next

- [ ] **Minimal / verbose split** — default to TPS, latency, dirty memory (traditional pgbent highlights); `--verbose` for all metrics
- [ ] **Legend** — show min/avg/max, not avg three times
- [ ] **Layout** — bottom of graph clipped on rotated x-axis labels
- [ ] **CLI** — database connection via options, not hard-coded DSN
- [ ] **SQL** — parameterized queries instead of string formatting
- [ ] **Aggregation** — choose `dbagg` from test duration, not fixed `'second'`
- [ ] **Latency outliers** — per-point markers like gnuplot cross symbols (`plots/latency.plot`); aggregated min/max/avg is not the same visual

## Later (webreport parity)

- [ ] Options to select `graph_single` vs `graph_group` (latency bundle)
- [ ] Python replacement for `webreport` test-set comparison graphs ([plotting.md](plotting.md))

## Out of scope

- Rewriting `benchwarmer` / `runset` shell orchestration
- Sponsor logo overlay (code exists but disabled)

## Usage

```bash
python3 metview.py <server> <test>
# defaults: server=twilight, test=2576
```

## Code notes

Implementation TODOs in `metview.py` should stay local to that file. Cross-cutting roadmap items belong in this document.
