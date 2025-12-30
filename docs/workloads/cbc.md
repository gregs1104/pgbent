---
layout: home
title: CBC Workload
permalink: /workloads/cbc
nav_order: 10
parent: Workloads
---

Complete Block Check:  a very short fully synthetic test workload designed to stress test PostgreSQL's data buffering capabilities.  

[Complete Block Check](/tests/cbc/README.md) a new storage stress test sample program that runs anywhere you want, from a psql session to orchestrated via pgbench generating its workload.   I've even run it on Crunchy's web based [Postgres Playground](https://www.crunchydata.com/developers/playground) to compare web browser block performance. Seriously!

The design reviewed the fastest parts of all the earlier workloads and picked out the statements that caused the most stress.  Then they were arranged as a data pipeline designed to evade caching.  CBC aims to include all the hardest simple block workloads available, discovered by reviewing the highest I/O statements and sequences in other workloads and then tweaking them to be more difficult or comprehensive.  The database size is the main input.  Just like the pgbench database, 2-4X RAM works well for CBC.
