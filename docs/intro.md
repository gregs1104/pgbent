---
layout: home
title: Introduction
permalink: /introduction/
nav_order: 1
---

# Introduction

pgbent records all the system activity and a package of PostgreSQL metrics while executing some database workload.  It saves enough data to discover and investigate performance regressions in either PostgreSQL or some database oriented workload using it.

The associated toolkit puts all the metrics about the workload runs into a PostgreSQL database.  Summary reporting SQL gives immediate feedback on workload runs.  Basic graphics drawing includes workload summaries, with plotting examples for any test run's metric time series via Python's Pandas graphing.

All the system activity, normal PG internals with `pg_stat_statements` and `pg_buffercache` extensions, all are saved as metrics while running some scripted workload.  Any SQL you want to run periodically can be executed too, making it straightforward to watch any database activity you can query.   The included example records client counts.

If you run _pgbent_ on the database server itself, it identifies the system information and saves it so you can remember the configuration.  It also helps size the workloads for you.

## pgbench workloads

pgbent automates running PostgreSQL's built-in pgbench tool,
running client vs. size grids of several workload types.

It will run some number of database sizes (the database
scale) and various concurrent client count combinations.
Scale/client runs with some common characteristic--perhaps one
configuration of the postgresql.conf--can be organized into a "set"
of runs.  The program graphs transaction rate during each test,
latency, and comparisons between test sets.
