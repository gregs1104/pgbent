---
layout: home
title: Workloads
permalink: /workloads/
nav_order: 6
has_children: true
---

# Workloads

The workloads included so far:

* PostgreSQL pgbench program running SELECT statements at a grid of client X size examples.  You can reach a modest fraction of random I/O SSD speed this way on local runs.  2X-4X RAM is the recommended range to make caching of the whole data set impossible, while allowing indexes to fit easily in memory on tests that use them.  A SELECT variation (`select-pages`) uses index range scans instead of single row lookups, and that one is much better at fetching enough blocks at a time to saturate SSD.  

  * Cloud tests running simple SELECTs mainly measure latency between the client and server.  Since some queries return cached data very fast, reviewing the minimum latency observed tracks very well with connection latency.

  * Developers working on PostgreSQL itself are often running benchmarks on the server, often a capable workstation.  For queries on the server, all the overhead of standard IP networking can be avoided if clients use the UNIX sockets connection method instead.  Those rates can easily clear 1M TPS on modest desktop processors, represeting fantasy speeds no regular client will see.  That load is useful for people working on the database's internals.

* Database population:  the init steps of building one of the pgbench test databases at some size.  That workload is particularly useful for cloud benchmarking work.  With the right command flags all the work to build a pgbench test database can run fully server side, which lets you test things while eliminating client latency from being a factor in the results.

* Fixed per-client rate UPDATE latency analysis.  UPDATE tests without some sort of limit, either a rate limiter or a simple think time, they do more testing of caching filling behavior than anything else.  Effectively using update tests for benchmarks deserves a full paper to do it justice.

