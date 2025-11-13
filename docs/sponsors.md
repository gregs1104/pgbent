---
layout: home
title: Sponsors
permalink: /Sponsors/
nav_order: 9
---

# Sponsor notes

_pgbent_ was supported from 2019-2025 by a generous time allocation from [Crunchy Data](https://www.crunchydata.com/).  The work successfully found performance and integration issues in two successive new PostgreSQL releases.  As of June 2025 Crunchy Data has been acquired by Snowflake.

From project inception on PG8.2/2006 to PG17/2024, all the hardware for the original _pgbench_tools_ development period was personally supplied by Greg Smith, to keep the work independent of employer entangement and vendor influence.  The first sponsored sample is from Crunchy:  one of the M4 Apple Silicon systems with the 128GB of RAM minimum needed to do well on the Open Street Map tests is under evaluation for PG17 and then PG18.

A medium memory sized Apple Silicon vs. Intel vs. AMD showdown is long in the making here.  I've been publishing Intel shootouts [since 1996](https://web.archive.org/web/19980521093812/http://westnet.com/~gsmith/memory.htm) when the competitors were Cyrix and VIA!  In 2020 I did a release day preview of [Apple Silicon's M1](https://www.crunchydata.com/blog/postgresql-benchmarks-apple-arm-m1-macbook-pro-2020).  It's only recently they've released models with enough memory to run more interesting database workloads.

I hope that seeing the best we can do on Apple's popular and standardized hardware platform gives an easy to replicate arm64 result that other core PostgreSQL development can use as a reference.  ARM based cloud servers have been enough of price/performance success for Crunchy's customers we've architected some newer SaaS offerings around them, placing well on benchmarks like [ClickBench](https://benchmark.clickhouse.com/)--where unlike most of the competition,  Crunchy actually [runs the query set correctly](https://github.com/ClickHouse/ClickBench/pull/252).
