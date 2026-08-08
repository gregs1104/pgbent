---
layout: home
title: How it works
permalink: /introduction/
nav_order: 1
---

# How pgbent works

For project overview, workloads, tuning research, and getting started, see the [home page]({{ '/' | relative_url }}).

This page describes what pgbent collects during a run and how results are organized for comparison.

## Metrics collection

pgbent records all system activity and a package of PostgreSQL metrics while executing a database workload. It saves enough data to discover and investigate performance regressions in PostgreSQL itself or in a workload built on top of it.

All metrics go into a PostgreSQL results database. Summary reporting SQL gives immediate feedback on each run. Graphics include workload summaries, and Python/Pandas scripts can plot any test run's metric time series.

Collected by default:

- **System activity** — CPU, memory, and I/O at one-second resolution
- **PostgreSQL internals** — via `pg_stat_statements` and `pg_buffercache`
- **Custom SQL** — any query you want executed periodically; the bundled example records client counts

If you run pgbent on the database server itself, it identifies and saves system information so you can remember the configuration later. It also helps size workloads appropriately for the hardware.

## Test sets

Runs that share a common characteristic—perhaps one `postgresql.conf`, one PostgreSQL version, or one hardware platform—are organized into a **test set**.

Each test set gets a serial number and a description. You create new sets with `./newset 'description'` or directly in SQL:

```sql
INSERT INTO testset (info) VALUES ('set name');
```

Graphs are generated per test set, plus a master comparison across sets. Each graph pair uses client count and database scale (size) on the X axes, so you can see whether an alternate configuration handles larger data sets or higher concurrency better.

The results database is separate from the test database so you can share one results store across multiple PostgreSQL installations while comparing different builds or configurations.

## pgbench workloads

pgbent automates PostgreSQL's built-in pgbench tool, running client vs. size grids of several workload types.

For each run, pgbent varies:

- **Database scale** — the size of the pgbench database
- **Client count** — concurrent pgbench connections

The program graphs transaction rate and latency during each test, and produces comparisons between test sets. Built-in tests use simple queries—useful for read scaling and write volume, but not for parameters like `work_mem` that affect query planning. See the [Workloads]({{ '/workloads/' | relative_url }}) pages for workloads that stress storage and checkpoint tuning more directly.

## Next steps

1. [Set up]({{ '/setup/' | relative_url }}) the test and results databases
2. [Run tests]({{ '/running/' | relative_url }}) with `./runset`
3. [Review results]({{ '/results/' | relative_url }}) and [reports]({{ '/reports/' | relative_url }})
