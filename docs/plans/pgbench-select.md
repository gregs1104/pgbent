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
| Power | `SUDODATA=1`, working `pgbent_powermon` | **Sockets cells only** for the watts ranking — one package, clients+server on the same box, complete accounting. Do not try to sum client and server RAPL across machines (enterprise metering; out of scope). |

Do not mix unix and TCP in one set. `conn` must stay `sockets prepared` or `host prepared`.

## Two board faces

**Sockets** — `SOCKETS=1` (no `-h`). Unix domain, clients on the server. Modest desktops still clear ~1M TPS here; that is the internals/on-box cell, not how Phoronix’s multi-million DC numbers are made. **TPS vs watts lives here** because one `powermon` sees the whole load.

**Networked** — remote (or LAN) TCP client, server not running pgbench. **The millions on OpenBenchmarking come from this face** once the link is in the DC class (**above ~10Gb/s**): a dedicated client can push the server harder than co-located sockets, because the server is not also burning cores on pgbench workers.

PTS `clients` options are **1, 50, 100, 250, 500, 800, 1000, 5000**. The OpenBenchmarking default widget is often scale 100 / **800** clients / read-only (they chart latency there). The multi-million TPS placeholders in `PGQuickTest-Prepared.csv` are **not** that 800/1000 cell — they are **16–128 clients** (about core count on those SKUs) and `Jobs=4`.

**Sockets ceiling on this lab’s 2S (`super`, 2× EPYC 7702), from logs — not a Phoronix row:**

```text
pgbench -S -T 10 -c 960 -j 128 -M prepared pgbench
# PG 17.9, scale 100, unix/on-box
# 14.7M xacts in 10s → tps = 1,533,003 (without initial connection time)
# initial connection time = 538 ms
```

At **960 clients / 128 jobs**, sockets looked **capped below what the hardware should do**. That is the on-box client tax (pgbench workers on the server), which is why a dedicated networked client on a >10Gb link is the interesting next step. 10s probe, not the 90s board cell. Do not invent this from desktop SETCLIENTS; `super` is down.

Unthrottled networked cells on the leaderboard for **TPS**, not for a combined power score. Localhost TCP is **not** a substitute for a remote client or for the Mbps sweep.

## One-shot mapping study

Publish unix prepared vs host/remote prepared on the same boxes (1-client and full clients, 90s, power on) so on-box TPS is not confused with a network client. After that page exists, the board stays two unthrottled faces. Repeating the **960-client sockets cap vs networked** comparison waits on `super` (or equivalent 2S) — not on twilight/siren desktops.

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

Do **not** wait on `super` / 2× EPYC 7702 (down) or the planned 14900KS chassis to ship the desktop sockets/networked board and the siren→twilight `tc` sweep. `super` is the box for the **960-client sockets ceiling vs >10Gb networked** follow-up; keep that cell parked until it powers on. Archive `PGQuickTest-Prepared.csv` Phoronix Multi-only rows are **placeholders** (`Jobs=4`, `Single=0`); new cells must not look measured the same way unless they are.

## Publication

- Newset name along the lines of `SELECT sockets prepared` / `SELECT host prepared` (PG19 when that major is the test cluster).
- Scatter like OSM power: TPS vs max package W on **sockets** cells, two markers per CPU (1 client / full).
- `/leaderboards/` SELECT section + versioned snapshot tables. Streamlit stays a local grid, not the hosted site.

## Out of scope

- Cloning ClickBench UI or a Phoronix Test Suite profile.
- Open dump intake on the leaderboards page.
- Campaign names for talks (keep those off this repo).
