---
layout: home
title: Workloads
permalink: /workloads/
nav_order: 6
---

# Workloads

The workloads included so far:

* PostgreSQL pgbench program running SELECT statements at a grid of client X size examples.  You can reach a modest fraction of random I/O SSD speed this way on local runs.  2X-4X RAM is the recommended range to make caching of the whole data set impossible, while allowing indexes to fit easily in memory on tests that use them.  A SELECT variation (`select-pages`) uses index range scans instead of single row lookups, and that one is much better at fetching enough blocks at a time to saturate SSD.  

  * Cloud tests running simple SELECTs mainly measure latency between the client and server.  Since some queries return cached data very fast, reviewing the minimum latency observed tracks very well with connection latency.

  * Developers working on PostgreSQL itself are often running benchmarks on the server, often a capable workstation.  For queries on the server, all the overhead of standard IP networking can be avoided if clients use the UNIX sockets connection method instead.  Those rates can easily clear 1M TPS on modest desktop processors, represeting fantasy speeds no regular client will see.  That load is useful for people working on the database's internals.

* Database population:  the init steps of building one of the pgbench test databases at some size.  That workload is particularly useful for cloud benchmarking work.  With the right command flags all the work to build a pgbench test database can run fully server side, which lets you test things while eliminating client latency from being a factor in the results.

* Fixed per-client rate UPDATE latency analysis.  UPDATE tests without some sort of limit, either a rate limiter or a simple think time, they do more testing of caching filling behavior than anything else.  Effectively using update tests for benchmarks deserves a full paper to do it justice.

* Complete Block Check:  a very short fully synthetic test workload designed to stress test PostgreSQL's data buffering capabilities.  The design reviewed the fastest parts of all the earlier workloads and picked out the statements that caused the most stress.  Then they were arranged as a data pipeline designed to evade caching.  CBC aims to include all the hardest simple block workloads available, discovered by reviewing the highest I/O statements and sequences in other workloads and then tweaking them to be more difficult or comprehensive.  The database size is the main input.  Just like the pgbench database, 2-4X RAM works well for CBC.

## osm2pgsql Workload

The osm2pgsql loading program populates the entire Open Street Map planet data set.  Based on the options you can get a svelte version suitable for production, or one with fully decoded metadata build options at about 750GB.  Until about 2020 there were multiple heavy CPU bound problems running this loader.  Major improvements in the Open Street Map distribution, loading workflow, and the underlying PostgreSQL on Linux platform turned the loading into a capable SSD challenger.  Particularly useful were its chain of CTAS single core work speeding up and CREATE INDEX becoming multi-process.  

 The main downside of this test is that you can't reach the high speeds unless you have a client available capable of caching the entire `nodes` data file, which is growing steadily toward where the popular 96GB threshold can barely host it.  That size has only recently become feasible on Apple Silicon Mac hardware, and that's limited the practicality this workload to measure OS X fairly so far.  Correspondingly that's made it hard for this one workload to be a fully general PostgreSQL testing platform.

![osm2pgsql workload](/images/twilight-1494-read-write.png)

For a few years now, the most interesting benchmark results have been the Open Street Map tests, published as [blog entries](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours), [talks](https://www.youtube.com/watch?v=BCMnu7xay2Y), or [social media posts](https://x.com/postgresperf/status/1858905975446556876).  That runs via the pgbent's artibrary workload interface script.  It's classic shell scripting work, there's no use of pgbench.


There's also a new storage stress test sample program included, [Complete Block Check](tests/cbc/README.md).  That runs anywhere you want, from a psql session to orchestrated via pgbench generating its workload.   I've even run it on our web based [Postgres Playground](https://www.crunchydata.com/developers/playground) to compare web browser block performance. Seriously!

After the rename and associated code reorg, the follow up tech refresh coming in later 2025 is deprecating use of _gnuplot_ in favor of Python Pandas based graphs.  Right now Pandas is behind my slides and social media graph posts; there's still a few old gnuplot graphs left to replace.
