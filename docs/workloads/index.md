---
layout: home
title: Workloads
permalink: /workloads/
nav_order: 7
has_children: true
---

# Workloads

pgbent includes fixed-size and scaling workloads. Each run records one-second metrics into the results database for comparison across test sets.

| Workload | What it exercises |
|----------|-------------------|
| [pgbench SELECT]({{ '/workloads/select/' \| relative_url }}) | SELECT, nothing (`;`), and constant (`SELECT 1`) across client × size grids; sockets vs TCP, simple vs prepared |
| [OpenStreetMap import]({{ '/workloads/osm' \| relative_url }}) | Planet load via osm2pgsql—COPY, index builds, checkpoint and buffer-cache pressure |
| [Complete Block Check (CBC)]({{ '/workloads/cbc' \| relative_url }}) | Short synthetic storage stress test (CTAS, VACUUM, CLUSTER, index scans); see also the [CBC Tutorial]({{ '/workloads/cbc/tutorial/' \| relative_url }}) |

pgbench also has UPDATE grids and `:-i` database population on the same client × size pattern.

* Database population: the init steps of building one of the pgbench test databases at some size. That workload is particularly useful for cloud benchmarking work. With the right command flags all the work to build a pgbench test database can run fully server side, which lets you test things while eliminating client latency from being a factor in the results.

* Fixed per-client rate UPDATE latency analysis. UPDATE tests without some sort of limit, either a rate limiter or a simple think time, they do more testing of caching filling behavior than anything else. Effectively using update tests for benchmarks deserves a full paper to do it justice.
