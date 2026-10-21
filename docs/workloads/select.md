---
layout: home
title: pgbench SELECT
permalink: /workloads/select
nav_order: 5
parent: Workloads
---

PostgreSQL pgbench running SELECT statements at a grid of client × size examples. You can reach a modest fraction of random I/O SSD speed this way on local runs. 2×–4× RAM is the recommended range to make caching of the whole data set impossible, while allowing indexes to fit easily in memory on tests that use them. A SELECT variation (`select-pages`) uses index range scans instead of single row lookups, and that one is much better at fetching enough blocks at a time to saturate SSD.

Cloud tests running simple SELECTs mainly measure latency between the client and server. Since some queries return cached data very fast, reviewing the minimum latency observed tracks very well with connection latency.

Developers working on PostgreSQL itself are often running benchmarks on the server, often a capable workstation. For queries on the server, all the overhead of standard IP networking can be avoided if clients use the UNIX sockets connection method instead. Those rates can easily clear 1M TPS on modest desktop processors, representing fantasy speeds no regular client will see. That load is useful for people working on the database's internals.

The same SELECT is also run simple and over localhost TCP. Phoronix switched to prepared statements a few years ago and kind of reset the public history; the numbers went up and not many people noticed. Sweeping all four faces (sockets vs localhost TCP, simple vs prepared) is the connection study from PostgreSQL 18, kept as a code exercise so a method change cannot hide. `wl/select-faces` runs that sweep (`SKIPINIT=1` against an existing scale-100 database). A failed `runset` logs the rc and continues; it used to live in `/tmp` with `set -e` and dump the remaining faces. Each client count also gets **transactions per joule** from the 1-second package-power integral — energy efficiency as the other side of that TPS fan. See the [SELECT leaderboard]({{ '/leaderboards/' | relative_url }}).

Fantasy scripts under that SELECT: `SCRIPT=nothing` (`tests/nothing.sql`) is only `;` — protocol and `BEGIN`/`COMMIT`, no query. `SCRIPT=constant` (`tests/constant.sql`) is `SELECT 1;` — a query with no table lookup. The accounts SELECT is the lookup on top of that. Same connection faces. On siren sockets `nothing` hits **280K TPS on a single client** prepared or simple. `constant` is **179,635**. That's web scale. `think` is the other end of that axis (it adds sleep). `wl/empty-grid` writes the nothing params; run against an existing scale-100 database with `SKIPINIT=1`.

## 1-client latency pieces

At one client these rates are just the inverse of the latency times. Planning takes some amount, execution some, and TCP connection adds some. The empty `;` floor plus the four SELECT faces on **siren** 19rc1 split most of that:

| 1-client cell | TPS | 1/TPS |
| --- | ---: | ---: |
| sockets prepared `;` | 280,201 | 3.6 μs |
| sockets `;` | 281,019 | 3.6 μs |
| sockets prepared `SELECT 1` | 179,635 | 5.6 μs |
| sockets prepared SELECT | 132,433 | 7.6 μs |
| localhost TCP prepared | 96,566 | 10.4 μs |
| sockets | 89,241 | 11.2 μs |
| localhost TCP | 68,924 | 14.5 μs |

- **Protocol + `BEGIN`/`COMMIT`:** 3.6 μs from sockets `;`. No query. Prepared **280,201** vs simple **281,019** — same floor; preparation does not move an empty transaction.
- **`SELECT 1`:** +2.0 μs, sockets prepared `constant` minus sockets prepared `;`. A query, no table.
- **Lookup:** +2.0 μs, sockets prepared SELECT minus sockets prepared `constant`. The accounts row. Together those two are the old +4.0 μs execution piece.
- **Planning:** +3.6 μs on **SELECT**, sockets simple minus sockets prepared. Parse/plan every transaction versus skip it. Not present on `;`.
- **TCP Connection:** +2.8 μs, localhost TCP prepared minus sockets prepared. Already-open pgbench session — not `connect()`. Initial connect is a one-time pgbench line, not in these TPS numbers.

Those four add to 14.0 μs against 14.5 μs on localhost TCP simple. Close enough to account for the cell. Multi-client TPS is the same latencies with more pipelines, not a different clock.

Sockets `nothing` (`script=semi`, set 107) on siren 19rc1, 90s, scale 100. Peak is **3.96M** simple at 32 clients — the 16-core/32-thread ceiling. SELECT’s sockets-prepared peak on the same box is **2.06M** at 32; `;` is already past that at 16.

| clients | sockets | sockets prepared |
| ---: | ---: | ---: |
| 1 | 281,019 | 280,201 |
| 2 | 536,616 | 525,849 |
| 4 | 966,910 | 929,901 |
| 8 | 1,577,974 | 1,459,014 |
| 16 | 2,221,108 | 2,138,539 |
| 32 | 3,960,034 | 3,682,164 |
| 64 | 3,921,947 | 3,763,165 |

At one client they are the same 3.6 μs floor: no query to plan, so `-M prepared` does not help. At many clients simple is a few percent ahead (Bind/Execute/Sync vs a simple `Query`). Both go flat past 32. The pause after each run is `pgbench -l` COPY into `timing`. At 32 clients that is ~330–360 million rows — `pgbench.log`, the `sort` spill, and `timing.csv` filled the **31GB free** then on siren (old uncompressed upload archives), so avg/P90/max never landed on those `;` rows. `tests.tps` is stored before that import. Clearing those archives put the boot drive back to **121GB free**. After `constant` finishes, re-run `nothing` at **32 and 64**, sockets simple and prepared, for the latency columns and for package watts on the empty transaction. Breaking the 1-client times into protocol / query / lookup / planning / TCP is a long-term goal; collect all of it while the box can. Accurate power on every platform was what blocked this — the question was how many watts `nothing` burns. `constant` (`SELECT 1`) 1-client is **179,635** (5.6 μs); the rest of that grid is still collecting.

## Comparing versions

Hold `conn_method` constant. An early mixed `latest_set` on **siren** put PG18 sockets next to 19beta4 localhost TCP and looked ~25% down. That was a test-method error, not debug assertions and not a version regression. `SHOW debug_assertions` was off on those beta4 rows anyway. Scale 100 is about **1.6GB**; that SELECT stays in memory, so a disk swap between pins does not matter.

Once 19rc1 was ready, the same box ran the whole connection grid (sockets vs localhost TCP, simple vs prepared). Fair version-only, 90s, 32 clients, mean of two `SETTIMES`:

| pin | conn_method | TPS |
| --- | --- | ---: |
| PostgreSQL 18.3 | sockets prepared | 2,013,812 |
| PostgreSQL 19rc1 | sockets prepared | 2,058,653 |
| PostgreSQL 19beta4 | localhost TCP prepared | 1,500,701 |
| PostgreSQL 19rc1 | localhost TCP prepared | 1,517,063 |

19rc1 is a hair faster than 18 on sockets, and a hair faster than 19beta4 on localhost TCP. The four-face [SELECT leaderboard]({{ '/leaderboards/' | relative_url }}) is that RC grid: sockets prepared **2.06M** vs localhost TCP prepared **1.52M**, a flat ~26% from 1 client through 64. At 1.5M TPS that protocol gap is not really bad.

Beta packages can still ship with `--enable-cassert`; CPU-bound SELECT is the canary, OSM barely moves. That was not this drop, and it was not worth chasing either way. Wiki: [Regression Testing with pgbench](https://wiki.postgresql.org/wiki/Regression_Testing_with_pgbench) (non-debug builds).
