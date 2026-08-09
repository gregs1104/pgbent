# Long-term project goals

Directional ambitions for pgbent—not near-term implementation tasks ([plotting.md](plotting.md), [metview.md](metview.md)) and not documentation to write ([documentation.md](documentation.md)). These are ideas that may take years or may never ship; they inform architecture choices but should not drive day-to-day agent work unless explicitly requested.

## How to use this file

- Check off `- [ ]` → `- [x]` only when a goal is substantially achieved.
- **Existing** links point at partial coverage today.
- Cross-reference [documentation.md](documentation.md) when the deliverable is primarily a write-up, not a feature.

---

## Features

Product and tooling directions beyond current gnuplot/SQL reporting.

- [ ] **TPS / metric heat map** — client × scale (or time × metric) grid colored by throughput or a chosen metric; quick visual scan of where a configuration wins or loses
  - Existing: gnuplot crosstabs in `plots/`; `reports/compare.py`, `reports/bars.py` (not heat maps)
- [ ] **Server-side Python for system info** — collect hardware/OS details as part of pgbent instead of shell-only probes (`dmirow`, inline benchwarmer capture)
  - Existing: `dmirow`, `server` table population from shell; `tests.server_cpu`, `server_mem_gb`, etc.
- [ ] **`pgbent config` param changer** — CLI to read/write the workload `params` file instead of hand-editing or shell `echo >> params`
  - Evolve **`pgsysinfo`** into this tool: rename (or wrap) so the **default** subcommand remains today's sysinfo + auto-sizing block (`SETCLIENTS`, `SCALES`, `OSMNODECACHE`)
  - Examples:
    ```text
    pgbent config                    # default: current pgsysinfo output → params
    pgbent config SCRIPT insert
    pgbent config SCALES 100
    pgbent config SCALES auto        # run scale_sweep / hardware-based sizing
    ```
  - Existing: `pgsysinfo` (Python, outputs recommended `SETCLIENTS`/`SCALES`); `params` workspace file sourced by `runset`/`benchwarmer`; `config` for DB connection; workloads append overrides (`wl/osm-import`, `wl/cbc-write`, `runset` temp patches)
- [ ] **`test_stats_pretty`** — human-readable view or report layer on top of `test_stats` (formatted units, friendly column names, ready for export/slides)
  - Existing: `test_stats` view in `init/resultdb.sql`; `write_internals`, `submission` views go further for OSM workloads
- [ ] **Locks and wait tracking** — capture `pg_stat_activity` wait events / lock waits for recent Postgres versions during runs
  - Existing: sample wait-event query appears in archived `explorer/results-bridge.sql` data; not wired into standard collection
- [ ] **Buffer cache visualization** — graph which relations fill `shared_buffers`, dirty vs clean, usage counts; compare PG buffer state to workload phase
  - Existing: end-of-run snapshot into `test_buffercache` via `pg_buffercache` (`benchwarmer`); `reports/bufreport.sql`, `reports/bufsummary.sql`, `reports/bufstats.sql`; `docs/model/shared_buffers.md`
  - [ ] **Can fincore integrate?** — explore OS page-cache residency (`fincore` / similar) alongside PG's view; bridge “what Postgres thinks is cached” vs “what the kernel has in the page cache” for data files. Not in repo today; would need collection hook + results DB storage + viz (e.g. `metview.py` or overlay tool from [documentation.md](documentation.md))
- [ ] **Database-first design essay** — see [documentation.md](documentation.md) § Database-first design (doc backlog, not a code feature)

---

## Queries

Analysis questions and report ideas to add to the results-database toolkit. Many extend `test_stats`, `write_internals`, or metric time series.

- [ ] **Buffer write-out rate (PG view)** — checkpoint + bgwriter + backend flush rate during the same period Postgres saw the workload (`check_bps`, `clean_bps`, `backend_bps` on `test_stats`)
  - Existing: `test_stats` columns; `reports/write_internals.sql` (checkpoint MB/h, clean MB/h)
- [ ] **Average queue depth** — from disk `_await` / util metrics or block-layer stats, aggregated per test
  - Existing: `init/metrics_map.csv` (`r_await`, `w_await`, `d_await`, …); per-second samples in `test_metrics_data`, not summarized in standard views
- [ ] **Max queue depth** — peak queue depth over a run (pair with avg for tail behavior)
- [ ] **Max read rate** — peak read MB/s (PG logical reads and/or disk `rMB/s`) on the workload grid
  - Existing: `max_read_mbps` in `write_internals` / submission views (disk-side); `read_bps` on `test_stats` (PG `blks_read` rate)
- [ ] **Logical-to-physical read ratio** — PG-reported read rate vs disk read rate; confirm and document what exists, then extend
  - Existing: **partial** — `hit_pct` and `read_mbps` from `blks_read`/`blks_hit` in `write_internals`; disk `avg_read_mbps` / `max_read_mbps` from `test_metrics_data`; Streamlit labels `read_mbps` as `miss_mbps`. A explicit **ratio column** (PG reads vs disk reads) is not standardized yet.
- [ ] **Logical-to-physical write ratio** — same idea for writes (PG buffer/checkpoint/WAL vs disk `wMB/s`); “writes are my thing”
  - Existing: `wal_mbps`, `avg_write_mbps`, `max_write_mbps` in `write_internals`; `backend_bps`, `check_bps`, `clean_bps` on `test_stats`. **Ratio not yet first-class.**
- [ ] **Cache hit % over workload grid** — `hit_pct` (or similar) on client × scale crosstabs to show how randomness / scale changes effective caching
  - Existing: `hit_pct` in `test_stats`, `write_internals`, submission explorer; grid visualization not built

---

## Major conceptual goals

Example analyses pgbent should eventually make easy—the “answer these questions from one results DB” tier.

- [ ] **Commit rate vs resources** — map TPS / commits per second to WAL volume, checkpoint rate, dirty memory, disk write MB/s, and CPU
  - Existing: `reports/metric-summary.sql` (`commit_ms` from TPS); `write_internals` WAL/checkpoint columns; OSM tuning studies
- [ ] **Logical-to-physical read ratio at scale** — how `blks_hit` vs `blks_read` (and disk reads) shift as database size and client count change
  - Existing: scale/client dimensions on `test_stats`; partial metrics above
- [ ] **Queue depth vs randomness** — as I/O becomes more random (higher scale, more clients, different workloads), how do `_await` / util and throughput respond?
  - Existing: pgbench grids + disk metrics collection; analysis queries not packaged

These conceptual goals tie together the **Queries** section: the long-term payoff is answering them from SQL/views/grids without ad-hoc spelunking per study.

---

## Confidence UI

Regression and comparison UI that quantifies run-to-run variation on the workload grid—not just average TPS/latency per cell.

- [ ] **Repeated grid runs** — standard workflow already re-runs each (scale × clients) point multiple times; surface that history instead of collapsing to a single number
  - Existing: `SETTIMES=3` in `config`; `runset` loop `for (( t=1; t<=$SETTIMES; t++ ))`; each repetition is a separate row in `tests` for the same set/scale/clients
- [ ] **Confidence bands per grid cell** — expected range for TPS and at least one latency metric (P99 ideal; **P90** is what pgbent stores today as `percentile_90_latency`)
  - Approach: Bollinger-inspired or simple **±1–2 standard deviations** across the *n* repeats at each grid point
  - Plot bands on client × scale charts (extends heat-map / crosstab direction)
- [ ] **Outlier flagging** — when a new run falls outside the band (better *or* worse), mark it for review (regression *or* lucky run)
  - Existing: `webreport` / `limited_webreport` use `avg(tps)` and `avg(percentile_90_latency)` grouped by scale/clients—variation is discarded, not visualized
- [ ] **Variation report** — table or view: per (set, script, scale, clients), show mean, stddev, min, max, count for TPS and latency across repeats
  - Existing: raw material in `tests` + `timing`; `pgbench.log` captures latency stddev per run; no consolidated confidence view yet

---

## Relationship to other plans

| If the work is… | Put it in… |
|-----------------|------------|
| Code to build in the next few months | [plotting.md](plotting.md), [metview.md](metview.md), or a new implementation plan |
| Docs to write when focused | [documentation.md](documentation.md) |
| Multi-year or exploratory direction | this file |

## Out of scope for agents by default

Items here are **not** implicit approval to start large refactors. Confirm with the repo owner before treating a long-term goal as an active task.
