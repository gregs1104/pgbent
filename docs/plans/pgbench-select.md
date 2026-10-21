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

Match [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench) closely enough to **claim comparability** and **link them** for TPS outside this lab. What this farm adds is **package power** and **transactions per joule** on the same row — energy efficiency as the virtuous side of better performance. Postgres developers care whether a code change moves those up or down. This lab is the public instrumentation; hyperscalers who host PG surely have their own.

Public ranking: [Leaderboards]({{ '/leaderboards/' | relative_url }}). The Phoronix-shaped cell is **prepared**. Keep running **all four faces** (sockets vs localhost TCP, simple vs prepared): that is the PG18 connection study, swept for code exercise so a method change cannot hide. Sockets-versus-TCP is not a third ranking forever, but it stays on the graph. Phoronix switched to `-M prepared` a few years ago (PTS pgbench 1.13) and kind of reset that public history; numbers went up, few noticed.

## Phoronix-shaped cell

| Knob | Value | Notes |
|------|--------|--------|
| Workload | `wl/select-grid` / `SCRIPT=select` | |
| Protocol | `PREPARED=1` (`-M prepared`) | PTS since pgbench 1.13; that switch reset public history. Still sweep simple too. |
| Runtime | `RUNTIME=90` | PTS `-T` 90 |
| Scale | 100 | Their advertised default; ~1.6GB |
| Repeats | `SETTIMES=2` | These CPU runs are tight; a third only if the two diverge. |
| Clients | **1** and full `SETCLIENTS` | Old single-core / multi-core pair |
| Power | `SUDODATA=1`, working `pgbent_powermon` | **Sockets cells only** for the watts ranking — one package, clients+server on the same box, complete accounting. Do not try to sum client and server RAPL across machines (enterprise metering; out of scope). |

Siren 2026-10-18: one batch **`pgbench SELECT`**, both sockets and IP in that set. `tests.conn_method` is saved on every row (`sockets prepared` / `host prepared` with `PREPARED=1`); reports split on `conn`, not on a second `newset`. Flip `SOCKETS` between `runset` passes. Localhost TCP is the on-box mapping study, not a remote DC client.

## Two board faces

**Sockets** — `SOCKETS=1` (no `-h`). Unix domain, clients on the server. Siren **9950X** max is **32 clients**: **2,011,141** then **2,016,484 TPS** (PG18, 90s) once the rear ST120 was in — the missing vent had been leaving that performance on the table. That is still the internals/on-box cell, not how Phoronix’s multi-million DC numbers are made. **TPS vs watts lives here** because one `powermon` sees the whole load.

**Networked** — remote (or LAN) TCP client, server not running pgbench. **The millions on OpenBenchmarking come from this face** once the link is in the DC class (**above ~10Gb/s**): a dedicated client can push the server harder than co-located sockets, because the server is not also burning cores on pgbench workers.

PTS `clients` options are **1, 50, 100, 250, 500, 800, 1000, 5000**. The OpenBenchmarking default widget is often scale 100 / **800** clients / read-only (they chart latency there). The multi-million TPS placeholders in `PGQuickTest-Prepared.csv` are **not** that 800/1000 cell — they are **16–128 clients** (about core count on those SKUs) and `Jobs=4`.

**Sockets ceiling on this lab’s 2S (`super`, 2× EPYC 7702), from logs — not a Phoronix row:**

```text
pgbench -S -T 10 -c 960 -j 128 -M prepared pgbench
# PG 17.9, scale 100, unix/on-box
# Ubuntu **24.04** kernel (this is the number to quote)
# 14.7M xacts in 10s → tps = 1,533,003 (without initial connection time)
# initial connection time = 538 ms
```

At **960 clients / 128 jobs**, sockets looked **capped below what the hardware should do**. That is the on-box client tax (pgbench workers on the server), which is why a dedicated networked client on a >10Gb link is the interesting next step. 10s probe, not the 90s board cell.

**Kernel / death of `super`:** could not beat that 24.04 figure on **26.04** — TPS dropped a lot — then the box stopped powering on. Treat the 26.04 drop as **suspect slow thermal failure**, not a kernel regression, until the iron is back. Same class as early pgbent catching a bad **AIO fan in public**: TPS moved first. Published write-up of that method (memory speed vs TPS, plus the overclocking holiday-crash): [PostgreSQL 13 Benchmark: Memory Speed vs. TPS](https://www.crunchydata.com/blog/postgresql-13-benchmark-memory-speed-vs.-tps). Reproduce on a second 2S before publishing a 24.04-vs-26.04 story. Do not invent this from desktop SETCLIENTS; `super` is down.

Unthrottled networked cells on the leaderboard for **TPS**, not for a combined power score. Localhost TCP is **not** a substitute for a remote client or for the Mbps sweep.

## Today: on-box UNIX vs TCP (overhead only)

Siren `pgbench SELECT`: **unix sockets vs localhost TCP**, same box, same grid, no other change. That is the protocol overhead, not a network client. Flip `SOCKETS` between `runset` passes; `conn_method` splits the rows. Halt each face after **two** `SETTIMES` passes — do not grind a third unless they split.

**Siren set 106 sockets prepared (scale 100, 90s), 2026-10-19.** Peak still **32 clients**. PG18: **2,011,141** / **2,016,484**. An early mixed `latest_set` also had 19beta4 **host prepared** **1,501,101** / **1,500,302** (~25% down) — test-method error, not debug assertions. Not worth chasing; cover the whole connection grid once the RC is ready. Fair version-only: 19rc1 sockets prepared **2.06M** vs 18 **2.01M**; 19rc1 host prepared **1.52M** vs 19beta4 **1.50M**. Scale 100 is ~1.6GB in RAM; a disk swap between pins does not matter. See [Comparing versions]({{ '/workloads/#comparing-versions' | relative_url }}). **2026-10-20 — 19rc1 validated** (as fast as 18, maybe a tiny faster) across three Linux platforms and a Mac. Siren OSM import on 19rc1 is done. The siren `pgbench SELECT` set is the **starter leaderboard** (`conn_method` faces).

## Siren 9950X retirement (full data)

Retire **9950X + SK51** with a complete pack before the chip comes out. Twilight already **leads relations/s** (4590 vs 4529); this OSM is the 9950X archive and a second rc1 pass, not a bid for the relations crown. Court is the slow `OSMRELPROF` peer after SELECT set 6 finishes — do not start another Spark planet load while that grid is in flight.

Hands-on on siren (no agent SSH):

1. Put **PG19 rc1** back on **SK51** if it is not already there (catalog **20261006**, `debug_assertions` off).
2. **Empty `;`** (`wl/empty-grid`, `SCRIPT=nothing`) on the existing scale-100 database (`SKIPINIT=1`). Same cell as SELECT: 90s, `SETTIMES=2`, clients `1 2 4 8 16 32 64`. **Sockets prepared 1 client is 280K TPS**; **8 clients already 1,459,014**. That's web scale. The pause is `pgbench -l` COPY into `timing`, not the run. The interesting test coming next is whether **preparation** impacts `nothing` runs — `;` has no query to plan, so sockets simple vs that prepared cell is the measurement. Then the TCP faces if the box is staying up. Then OSM.
3. One full **OSM** (~4h) with `OSMRELPROF=1` and the 1h Relation stop. That re-tests rc1 and keeps a validated 9950X Relation `perf`.
4. Then **9600X**.

Keep `nothing` off the SELECT ranking graph. The sockets prepared 280K 1-client note and the planning / execution / TCP connection split (rates as 1/latency) live on [1-client latency pieces]({{ '/workloads/#1-client-latency-pieces' | relative_url }}).

## Later: true remote TCP on the new 2S

This is what the **new 2-socket system** is for. A dedicated client should drive a **128-client** load as high as the network will allow (server not running pgbench workers). Separate test — do not fold it into today's on-box pair. The old `super` 960-client sockets ceiling vs >10Gb networked story stays parked until that iron (or this new 2S) is actually the client/server pair.

## Rate sweep (not a ranking)

Same pair and labels as [OSM Network]({{ '/results-summary/pg18/osm-network/' | relative_url }}): **9950X client → 13600K server** (siren → twilight). `conn` in `{100, 1000, 2500, 5000, 10000}` vs host-local.

Cable the pair once. Control rates with **`tc`** (TBF/HTB/CAKE) on the path packets take—not `ethtool` autoneg, not switch port swaps. Record the qdisc in `testset.info`. 9950X is the louder client; 13600K is the quieter server. Do not reverse without a footnote.

## Machines

| Box | Role |
|-----|------|
| twilight (13600K) | Fast looper; SELECT grid; 13600K end of the network pair |
| siren (9950X) | Greg-only / no agent SSH (fragile chassis, hands-on recovery). Rear ST120 is in; OSM probe **finished 4.07h** (2026-10-18; replacement for the wiped cell). Set **106** sockets prepared: PG18 max at **32 clients** **2,011,141** / **2,016,484**. Early 19beta4 **1.50M** cells in that `latest_set` were **host prepared** (method error, not asserts). **19rc1** covered the whole connection grid; sockets prepared **2.06M**. Halt after two; **`SETTIMES=2`**. **19rc1 is the validated pin** (as fast as 18, maybe a tiny faster). Siren OSM import finished 2026-10-20. The SELECT set is the starter leaderboard (`conn_method` faces). **Retirement pack before 9600X:** empty `;` grid + one 4h OSM with `OSMRELPROF=1` (also re-tests rc1). Twilight already leads relations/s. Rear ST120 works hard by the end of each 90s and harder still importing `pgbench -l` latency at this TPS. Prepared, 90s, scale 100, 1-client + full clients, package power; `PREPARED=1` in params, `SUDODATA=1` already in `config`. True remote TCP at 128 clients waits on the **new 2S**. OSM comparison charts are waiting on **9600X** to fill the gap between high-power x86 and ARM; OSM barely moved 9600X→9950X. Greg is looking for the chip. Also 9950X client for the `tc` sweep; data via `download`. |
| abbey | M-series watts; Greg workstation, not public Mac QA |
| court (Spark) | Slowest ARM / Spark appliance. OSM PG19 set 5 is enough; do not start another planet load. **2026-10-20 — set 6 `PG19 rc1 SELECT` running:** four faces, scale 100, 90s, `SETTIMES=2`, same client sweep as siren. Sockets prepared first. |

Do **not** wait on `super` / 2× EPYC 7702 (down) or the planned 14900KS chassis to ship the desktop sockets/networked board and the siren→twilight `tc` sweep. `super` is the box for the **960-client sockets ceiling vs >10Gb networked** follow-up; keep that cell parked until it powers on. Archive `PGQuickTest-Prepared.csv` Phoronix Multi-only rows are **placeholders** (`Jobs=4`, `Single=0`); new cells must not look measured the same way unless they are.

## Public trail (pgbench → OSM)

The switch of gears is already public on [Greg Smith’s Crunchy blog index](https://www.crunchydata.com/blog/author/greg-smith): pgbench grids until they could **saturate SSD** ([PG13, 1.6GB/s random reads](https://www.crunchydata.com/blog/postgresql-13-upgrade-and-performance-check-on-ubuntu-debian)), memory-speed vs TPS and the overclocking saga ([same series](https://www.crunchydata.com/blog/postgresql-13-benchmark-memory-speed-vs.-tps)), then OSM as the bulk-write / checkpoint stress ([Loading the World](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours)). SELECT on this leaderboard is the Phoronix-shaped remnant of that first era, with watts; OSM is what you run when pgbench cannot fill the drive.

## Publication

- **Starter board:** siren PG19 rc1 `pgbench SELECT` set — TPS and txn/J graphs plus the 1/32 table of `conn_method` faces on `/leaderboards/` (`reports/select-leaderboard.py --from-db`). Later: more machines.
- Study batch can be one `newset` (siren: `pgbench SELECT`); faces are `conn_method`, not separate batches.
- Scatter like OSM power: TPS vs max package W on **sockets** cells, two markers per CPU (1 client / full).
- `/leaderboards/` SELECT section + versioned snapshot tables. Streamlit stays a local grid, not the hosted site.

## Out of scope

- Cloning ClickBench UI or a Phoronix Test Suite profile.
- Open dump intake on the leaderboards page.
- Campaign names for talks (keep those off this repo).
