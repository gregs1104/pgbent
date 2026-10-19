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

**Siren set 106 sockets (scale 100, 90s), 2026-10-19.** Peak still **32 clients** on both majors. PG18: **2,011,141** / **2,016,484**. 19beta4: **1,501,101** / **1,500,302** (~25% down; the pair agrees). Init `:-i` 503 vs 375. Drop is across the whole client sweep (~23–27%). **Do not publish** as an 18↔19 regression: beta packages often have assertions on (`debug_assertions`), and that trash this CPU-bound SELECT. **When siren is back, in order:** (1) **19rc1** and rerun this sockets SELECT grid until the data is clean (assert-off; not more 19beta4). (2) **OSM on 19rc1** on the 9950X. (3) **switch to 9600X** for the OSM comparison SKU.

## Later: true remote TCP on the new 2S

This is what the **new 2-socket system** is for. A dedicated client should drive a **128-client** load as high as the network will allow (server not running pgbench workers). Separate test — do not fold it into today's on-box pair. The old `super` 960-client sockets ceiling vs >10Gb networked story stays parked until that iron (or this new 2S) is actually the client/server pair.

## Rate sweep (not a ranking)

Same pair and labels as [OSM Network]({{ '/results-summary/pg18/osm-network/' | relative_url }}): **9950X client → 13600K server** (siren → twilight). `conn` in `{100, 1000, 2500, 5000, 10000}` vs host-local.

Cable the pair once. Control rates with **`tc`** (TBF/HTB/CAKE) on the path packets take—not `ethtool` autoneg, not switch port swaps. Record the qdisc in `testset.info`. 9950X is the louder client; 13600K is the quieter server. Do not reverse without a footnote.

## Machines

| Box | Role |
|-----|------|
| twilight (13600K) | Fast looper; SELECT grid; 13600K end of the network pair |
| siren (9950X) | Greg-only / no agent SSH (fragile chassis, hands-on recovery). Rear ST120 is in; OSM probe **finished 4.07h** (2026-10-18; replacement for the wiped cell). Set **106** sockets: PG18 max at **32 clients** **2,011,141** / **2,016,484**; 19beta4 **1,501,101** / **1,500,302** (~25% down, pair agrees). Halt after two; **`SETTIMES=2`**. Do not publish the 19b4 drop (beta assertions trash this test). **When siren is back, in order:** **19rc1 SELECT** until clean, then **OSM on 19rc1**, then **9600X**. `newset` **`pgbench SELECT`**: on-box **UNIX vs localhost TCP** (`conn_method` distinguishes) — overhead only; TCP still to collect. SELECT + OSM is the usual 18↔19 regression pair (small-scale reads, planet-load writes). Rear ST120 works hard by the end of each 90s and harder still importing `pgbench -l` latency at this TPS. Prepared, 90s, scale 100, 1-client + full clients, package power; `PREPARED=1` in params, `SUDODATA=1` already in `config`. Do this **before** the 9600X downgrade. True remote TCP at 128 clients waits on the **new 2S**. OSM comparison charts are waiting on **9600X** to fill the gap between high-power x86 and ARM; OSM barely moved 9600X→9950X. Greg is looking for the chip. Also 9950X client for the `tc` sweep; data via `download`. |
| abbey | M-series watts; Greg workstation, not public Mac QA |
| court (Spark) | ARM/Spark watts; build-animal later; OSM PG19 stretch still first |

Do **not** wait on `super` / 2× EPYC 7702 (down) or the planned 14900KS chassis to ship the desktop sockets/networked board and the siren→twilight `tc` sweep. `super` is the box for the **960-client sockets ceiling vs >10Gb networked** follow-up; keep that cell parked until it powers on. Archive `PGQuickTest-Prepared.csv` Phoronix Multi-only rows are **placeholders** (`Jobs=4`, `Single=0`); new cells must not look measured the same way unless they are.

## Public trail (pgbench → OSM)

The switch of gears is already public on [Greg Smith’s Crunchy blog index](https://www.crunchydata.com/blog/author/greg-smith): pgbench grids until they could **saturate SSD** ([PG13, 1.6GB/s random reads](https://www.crunchydata.com/blog/postgresql-13-upgrade-and-performance-check-on-ubuntu-debian)), memory-speed vs TPS and the overclocking saga ([same series](https://www.crunchydata.com/blog/postgresql-13-benchmark-memory-speed-vs.-tps)), then OSM as the bulk-write / checkpoint stress ([Loading the World](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours)). SELECT on this leaderboard is the Phoronix-shaped remnant of that first era, with watts; OSM is what you run when pgbench cannot fill the drive.

## Publication

- Study batch can be one `newset` (siren: `pgbench SELECT`); faces are `conn_method`, not separate batches.
- Scatter like OSM power: TPS vs max package W on **sockets** cells, two markers per CPU (1 client / full).
- `/leaderboards/` SELECT section + versioned snapshot tables. Streamlit stays a local grid, not the hosted site.

## Out of scope

- Cloning ClickBench UI or a Phoronix Test Suite profile.
- Open dump intake on the leaderboards page.
- Campaign names for talks (keep those off this repo).
