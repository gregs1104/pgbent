---
layout: home
title: "pgbench SELECT Leaders: Performance vs. Power"
permalink: /leaderboards/select-performance-power/
parent: Leaderboards
nav_order: 2
---

# pgbench SELECT Leaders: Performance vs. Power

TPS and package-power detail behind the [SELECT section]({{ '/leaderboards/#history-1' | relative_url }}) of the leaderboards page. 

Phoronix-comparable **SELECT** cells: **90s**, scale 100. The standard Postgres on Linux SELECT lab numbers published are at [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench); these are a comparable TPS collected by pgbent. This lab still runs **all four connection faces**  — sockets vs localhost TCP, simple vs prepared — so protocol overhead stays visible. **Localhost TCP prepared** is the Phoronix-shaped ranking cell. See [Comparing versions]({{ '/workloads/select/#comparing-versions' | relative_url }}).

<!-- select-leaderboard:begin -->

![pgbench SELECT - Siren 9950X]({{ '/images/select-leaderboard.png' | relative_url }})

Starter board from **siren** (R9 9950X), PostgreSQL **19rc1** (rc1 2026-10-15, catalog 20261006), scale 100, 90s. Same box, four faces of the connection sweep: unix sockets vs localhost TCP, simple vs `-M prepared`. Peak is **32 clients**, sockets prepared (**2.06M TPS**). Localhost TCP prepared sits at **1.52M** (~26% below sockets). Package watts: 1-client is ~**62 W**; from 16 clients up the 9950X sits on the **~200 W PPT** rail (RAPL avg **199.6**, not a copied 200).

Package power sits on the same row as TPS on the **sockets** face (one machine, complete accounting). Combining client and server watts across boxes is out of scope—that's the harder to observe data center shaped problem. **Transactions per joule** is the energy-efficiency number for each client count — the same 1-second `PkgWatt` integral as OSM kJ. Better performance is also more work per watt-second; the PG community cares about that as a virtuous side effect of code improvements, so this lab publishes it.

At 32 clients every face burns ~**17.8 kJ** in 90s — the sum of the 200W PPT rail. Sockets prepared does **10,406** txn/J; localhost TCP simple does **5,040**. Same joules, twice the work. Energy efficiency is the other side of the protocol fan. Better performance spends the same watt-seconds on more useful work.

![pgbench SELECT - transactions per joule]({{ '/images/select-leaderboard-joules.png' | relative_url }})

Mean across repeats (4 faces). **tps_1** is the old single-core cell; **tps_32** is the max on this chip. **pkg_*** is average package watts; **txn_j_*** is transactions per joule on those same runs.

| conn | tps_1 | pkg_1 | txn_j_1 | tps_32 | pkg_32 | txn_j_32 |
| --- | --- | --- | --- | --- | --- | --- |
| sockets prepared | 132,433 | 60.9 | 2,196 | 2,058,653 | 199.6 | 10,406 |
| localhost TCP prepared | 96,566 | 61.7 | 1,579 | 1,517,063 | 199.6 | 7,669 |
| sockets | 89,241 | 62.7 | 1,438 | 1,354,200 | 199.6 | 6,841 |
| localhost TCP | 68,924 | 65.2 | 1,066 | 997,097 | 199.6 | 5,040 |

<!-- select-leaderboard:end -->

`;` (`SCRIPT=nothing`) hits **280K TPS on a single client** (simple **281,019**, prepared **280,201**) and peaks at **4.05M** simple / **3.81M** prepared at 32 clients — the protocol ceiling. That's web scale. No query to plan, so preparation does not help; at many clients simple is a few percent ahead. Sockets `constant` (`SELECT 1`) at one client is **212,745** prepared (4.7 μs) / **179,635** simple (5.6 μs), and peaks at **2.96M** prepared / **2.48M** simple at 32. Execute of that query is +1.1 μs, planning it +0.9 μs, accounts lookup +2.9 μs on top. Unlike `;`, preparation helps `SELECT 1`. At one client the rates are just the inverse of the latency times. Breakdown: [1-client latency pieces]({{ '/workloads/select/#1-client-latency-pieces' | relative_url }}). Not on this ranking.

### Sockets

Unix-domain connections (`SOCKETS=1`). Clients run on the server. This is the power-ranking cell. **Localhost TCP prepared** is the Phoronix-shaped face.

### Networked

Localhost TCP (`host`) on this starter chart is protocol overhead on the same box, not a dedicated client. Unthrottled remote TCP is the face that can exceed on-box rates once the link is faster than ~10Gb/s.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/select-leaderboard.py --from-db` (runs `reports/select-leaderboard.sql`). Cross-major sockets-prepared trend: [Leaderboards § History]({{ '/leaderboards/#history-1' | relative_url }}). 19rc1 snapshot: [pgbench SELECT (PG19)]({{ '/results-summary/pg19/pgbench-select/' | relative_url }}). Older mixed-protocol grid: [pgbench SELECT (PG18 snapshot)]({{ '/results-summary/pg18/pgbench-select/' | relative_url }}). Workload notes: [pgbench SELECT]({{ '/workloads/select/' | relative_url }}).
