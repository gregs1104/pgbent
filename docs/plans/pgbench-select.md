---
layout: home
title: pgbench SELECT leaderboard cells
permalink: /plans/pgbench-select/
parent: Development plans
nav_order: 6
---

# pgbench SELECT leaderboard cells

Near-term study so `/leaderboards/` can show Phoronix-comparable SELECT **plus package power**. Not a live dashboard; refresh the static page when cells land. Do not treat this as an open submission program.

## Goal

Match [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench) closely enough to **claim comparability** and **link them** for TPS outside this lab. What this farm adds is **package power** (and memory) on the same row. Postgres developers care whether a code change moves those up or down.

Public ranking: [Leaderboards]({{ '/leaderboards/' | relative_url }}) — two faces only (**sockets** and **networked**). The sockets-versus-TCP mapping is a **one-time published study**, not a third ranking forever.

## Phoronix-shaped cell

| Knob | Value | Notes |
|------|--------|--------|
| Workload | `wl/select-grid` / `SCRIPT=select` | |
| Protocol | `PREPARED=1` (`-M prepared`) | PTS since pgbench 1.13 |
| Runtime | `RUNTIME=90` | PTS `-T` 90 |
| Scale | 100 | Their advertised default; ~1.6GB |
| Repeats | `SETTIMES=3` | |
| Clients | **1** and full `SETCLIENTS` | Old single-core / multi-core pair |
| Power | `SUDODATA=1`, working `pgbent_powermon` | `avg_package_watts` / `max_package_watts` on `submission` |

Do not mix unix and TCP in one set. `conn` must stay `sockets prepared` or `host prepared`.

## Two board faces

**Sockets** — `SOCKETS=1` (no `-h`). Unix domain, on-box, Phoronix-local shaped. This is the million-TPS cell.

**Networked** — `TESTHOST=localhost` or a LAN client (TCP). Unthrottled only on the leaderboard. Localhost TCP is **not** a substitute for the Mbps sweep.

## One-shot mapping study

Publish unix prepared vs host prepared on the same boxes (1-client and full clients, 90s, power on) so “1M TPS on the server” is not confused with what a client sees. After that page exists, the board stays two unthrottled faces.

## Rate sweep (not a ranking)

Same pair and labels as [OSM Network]({{ '/results-summary/pg18/osm-network/' | relative_url }}): **9950X client → 13600K server** (siren → twilight). `conn` in `{100, 1000, 2500, 5000, 10000}` vs host-local.

Cable the pair once. Control rates with **`tc`** (TBF/HTB/CAKE) on the path packets take—not `ethtool` autoneg, not switch port swaps. Record the qdisc in `testset.info`. 9950X is the louder client; 13600K is the quieter server. Do not reverse without a footnote.

## Machines

| Box | Role |
|-----|------|
| twilight (13600K) | Fast looper; SELECT grid; 13600K end of the network pair |
| siren (9950X) | Greg-only on the box; 9950X client for the sweep; data via `download` |
| abbey | M-series watts; Greg workstation, not public Mac QA |
| court (Spark) | ARM/Spark watts; build-animal later; OSM PG19 stretch still first |

Do **not** wait on the 2× EPYC 7702 (down) or the planned 14900KS chassis. Those can join later as extra single-socket / 2S rows. Archive `PGQuickTest-Prepared.csv` Phoronix Multi-only rows are **placeholders** (`Jobs=4`, `Single=0`); new cells must not look measured the same way unless they are.

## Publication

- Newset name along the lines of `SELECT sockets prepared` / `SELECT host prepared` (PG19 when that major is the test cluster).
- Scatter like OSM power: TPS vs max package W, two markers per CPU (1 client / full).
- `/leaderboards/` SELECT section + versioned snapshot tables. Streamlit stays a local grid, not the hosted site.

## Out of scope

- Cloning ClickBench UI or a Phoronix Test Suite profile.
- Open dump intake on the leaderboards page.
- Campaign names for talks (keep those off this repo).
