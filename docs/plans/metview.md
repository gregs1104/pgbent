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
- [x] **Avg/max overlay (first consumer)** — public OSM leaderboard traces (`reports/metric_series.py`): two lines on one axes from `test_metrics_data`, minute buckets so the max is a real 1-second sample. `metview.py` itself still plots avg-only.

## Next

- [ ] **Priority filter (not a blunt verbose flag)** — see below; default = top priorities only
- [ ] **Stacked metric groups** — see below; first-class alongside single-series plots
- [ ] **Multi-line groups in metview** — fold `plot_avg_max` into `graph_single` / `graph_group`; legend shows min/avg/max values, not avg three times
- [ ] **Layout** — bottom of graph clipped on rotated x-axis labels
- [ ] **CLI** — database connection via options, not hard-coded DSN
- [ ] **SQL** — parameterized queries instead of string formatting
- [ ] **Aggregation** — choose `dbagg` from test duration, not fixed `'second'`
- [ ] **Latency outliers** — per-point markers like gnuplot cross symbols (`plots/latency.plot`); aggregated min/max/avg is not the same visual

### Priority filter / drill-down

Each decoded metric already carries Greg’s importance ranking:
`metrics_map.csv` column `priority` → `metrics_info.visibility` →
`test_metrics_decode.vis` (odd scale **9 / 7 / 5 / 3 / 1**, higher = more important).

Drive selection from that, not from a hard-coded “TPS / latency / Dirty” list or a
single `--verbose` dump of everything:

- **CLI takes a flexible priority range** (e.g. `--priority 9`, `--priority 7-9`,
  `--priority 5-6`). Only metrics whose `vis` falls **inside that range** are
  generated. Default is the **top band only** (start with `vis = 9`, or whatever
  the current map treats as the highlight set).
- **Drill-down is a new range, not a growing union.** After `7-9` is done, the
  next pass is `--priority 5-6` — it draws only that band. Re-requesting `5-9`
  would redo 7–9; the point of a flexible range is to ask for exactly what is
  still missing.
- **Skip existing PNGs** remains a safety net (and `--force` overwrites), but the
  primary control is the range list, not “run everything above N and hope skip
  works.”
- Stacks follow the same gate: emit a stack when it (or its members) fall in the
  requested priority range.

Hard-coding highlight metric names in Python fights the decoder; keep importance in
`metrics_info` and let metview filter on `vis`.

### Stacked metric groups

`metview.py` today emits **one PNG per metric**. That is wrong for series that only make sense as a **composition of a whole**. Agent work should add stacked views (Matplotlib `stackplot` over the run timeline; discrete stacked bars only if summarizing a whole run into one column).

| Stack | Parts (order bottom→top) | Whole |
|-------|--------------------------|--------|
| **CPU** | user / system / idle / iowait (+ guest / stolen when present) | ~100% × cores (vmstat-style percents: `us`/`sy`/`id` in `metrics_map` category CPU; Linux `wa`/`gu`/`st`) |
| **Linux memory** | free / cached / buffers / dirty / … (pick a partition that sums cleanly) | `MemTotal` (or `server_mem_gb`) |

Design notes:

- **Declare stacks in data, not only in plot code.** A small registry (Python table or rows in/near `metrics_info`) names each stack, member metric keys, stack order, and the expected total (literal 100×NCPU, or another metric / `server` column). Missing members → skip that series or leave a gap; do not silently renorm unless documented.
- **Y-axis is the whole**, not “each series autoscaled.” CPU stack tops out at 100%×cores; memory stack tops out at total RAM. Overshoot (sum ≠ total) should be visible, not clipped away.
- **Default (high priority) runs** should prefer the CPU and memory **stacks** over dumping every low-`vis` meminfo key as its own chart. Widen `--priority` to get the singles.
- **Do not force every metric into a stack.** TPS, Dirty alone, disk MB/s, power watts stay as single series. Only groups that *compose a known total* get the stacked treatment.
- Darwin / other OS: separate stack definitions when the captured names differ (`Mac Mem` free/active/wired/…); same idea, different member list.

Priority filtering + stacks are the natural next metview capabilities after
single-series polish — good agent-sized features once the CLI/DSN cleanup is
tolerable.

## Later (webreport parity)

- [ ] Options to select `graph_single` vs `graph_group` (latency bundle)
- [ ] Python replacement for `webreport` test-set comparison graphs ([plotting.md](plotting.md))

## Out of scope

- Rewriting `benchwarmer` / `runset` shell orchestration
- Sponsor logo overlay (code exists but disabled)

## Usage

```bash
python3 metview.py <server> <test>
# planned:
#   python3 metview.py <server> <test>                # top band only (e.g. 9)
#   python3 metview.py <server> <test> --priority 7-9
#   python3 metview.py <server> <test> --priority 5-6 # drill down: only the new band
#   python3 metview.py <server> <test> --priority 9 --force
```

## Code notes

Implementation TODOs in `metview.py` should stay local to that file. Cross-cutting roadmap items belong in this document.
