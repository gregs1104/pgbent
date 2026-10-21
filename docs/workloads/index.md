---
layout: home
title: Workloads
permalink: /workloads/
nav_order: 6
has_children: true
---

# Workloads

pgbent includes fixed-size and scaling workloads. Each run records one-second metrics into the results database for comparison across test sets.

| Workload | What it exercises |
|----------|-------------------|
| **pgbench grids** (below) | SELECT, UPDATE, nothing (`;`), constant (`SELECT 1`), and `:-i` init across client × database-size grids |
| [OpenStreetMap import]({{ '/workloads/osm' \| relative_url }}) | Planet load via osm2pgsql—COPY, index builds, checkpoint and buffer-cache pressure |
| [Complete Block Check (CBC)]({{ '/workloads/cbc' \| relative_url }}) | Short synthetic storage stress test (CTAS, VACUUM, CLUSTER, index scans); see also the [CBC Tutorial]({{ '/workloads/cbc/tutorial/' \| relative_url }}) |

## pgbench grids and tests

* PostgreSQL pgbench program running SELECT statements at a grid of client X size examples.  You can reach a modest fraction of random I/O SSD speed this way on local runs.  2X-4X RAM is the recommended range to make caching of the whole data set impossible, while allowing indexes to fit easily in memory on tests that use them.  A SELECT variation (`select-pages`) uses index range scans instead of single row lookups, and that one is much better at fetching enough blocks at a time to saturate SSD.  

  * Cloud tests running simple SELECTs mainly measure latency between the client and server.  Since some queries return cached data very fast, reviewing the minimum latency observed tracks very well with connection latency.

  * Developers working on PostgreSQL itself are often running benchmarks on the server, often a capable workstation.  For queries on the server, all the overhead of standard IP networking can be avoided if clients use the UNIX sockets connection method instead.  Those rates can easily clear 1M TPS on modest desktop processors, represeting fantasy speeds no regular client will see.  That load is useful for people working on the database's internals.

  * The same SELECT is also run simple and over localhost TCP.  Phoronix switched to prepared statements a few years ago and kind of reset the public history; the numbers went up and not many people noticed.  Sweeping all four faces (sockets vs localhost TCP, simple vs prepared) is the connection study from PostgreSQL 18, kept as a code exercise so a method change cannot hide.  Each client count also gets **transactions per joule** from the 1-second package-power integral — energy efficiency as the other side of that TPS fan.  See the [SELECT leaderboard]({{ '/leaderboards/' | relative_url }}).

  * Fantasy scripts under that SELECT: `SCRIPT=nothing` (`tests/nothing.sql`) is only `;` — protocol and `BEGIN`/`COMMIT`, no query.  `SCRIPT=constant` (`tests/constant.sql`) is `SELECT 1;` — a query with no table lookup.  The accounts SELECT is the lookup on top of that.  Same connection faces.  On siren **sockets prepared** `nothing` already hits **280K TPS on a single client**.  That's web scale.  `think` is the other end of that axis (it adds sleep).  `wl/empty-grid` writes the nothing params; run against an existing scale-100 database with `SKIPINIT=1`.

### 1-client latency pieces

At one client these rates are just the inverse of the latency times. Planning takes some amount, execution some, and TCP connection adds some. The empty `;` floor plus the four SELECT faces on **siren** 19rc1 split most of that:

| 1-client cell | TPS | 1/TPS |
| --- | ---: | ---: |
| sockets prepared `;` | 280K | 3.6 μs |
| sockets prepared SELECT | 132,433 | 7.6 μs |
| localhost TCP prepared | 96,566 | 10.4 μs |
| sockets | 89,241 | 11.2 μs |
| localhost TCP | 68,924 | 14.5 μs |

- **Protocol + `BEGIN`/`COMMIT`:** 3.6 μs from sockets prepared `;`. No query.
- **Execution:** +4.0 μs, sockets prepared SELECT minus sockets prepared `;`. The lookup itself. `SCRIPT=constant` (`SELECT 1`) sits in between: a query with no accounts lookup. No 1-client number yet.
- **Planning:** +3.6 μs, sockets simple minus sockets prepared. Parse/plan every transaction versus skip it.
- **TCP Connection:** +2.8 μs, localhost TCP prepared minus sockets prepared. Already-open pgbench session — not `connect()`. Initial connect is a one-time pgbench line, not in these TPS numbers.

Those four add to 14.0 μs against 14.5 μs on localhost TCP simple. Close enough to account for the cell. Multi-client TPS is the same latencies with more pipelines, not a different clock.

Sockets prepared `nothing` at **8 clients** is already **1,459,014** TPS. The pause after each run is `pgbench -l` COPY into `timing` (~131 million rows in 90s) — 2007 ingest, not built for this rate. SELECT hit that heat spike near 2M / 32 clients; `;` hits it at 8. `tests.tps` is stored before that import.

The interesting test coming next is whether **preparation** impacts `nothing` runs. SELECT simple vs prepared is the 3.6 μs planning piece; `;` has no query to plan. The 280K 1-client cell is **sockets prepared**; the measurement is sockets simple `nothing` against that.

* Database population:  the init steps of building one of the pgbench test databases at some size.  That workload is particularly useful for cloud benchmarking work.  With the right command flags all the work to build a pgbench test database can run fully server side, which lets you test things while eliminating client latency from being a factor in the results.

* Fixed per-client rate UPDATE latency analysis.  UPDATE tests without some sort of limit, either a rate limiter or a simple think time, they do more testing of caching filling behavior than anything else.  Effectively using update tests for benchmarks deserves a full paper to do it justice.

### Comparing versions

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
