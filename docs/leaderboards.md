---
layout: home
title: Leaderboards
permalink: /leaderboards/
nav_order: 0
---

# Leaderboards

Public OSM planet-load and pgbench SELECT rankings from the pgbent farm personally run by Greg Smith. This page is updated when there are new cells; it is not a live dashboard. PostgreSQL 19 numbers start landing here when the beta or RC testing is stable enough to pass.

The ranked tables below are the current published snapshot ([PostgreSQL 18]({{ '/results-summary/pg18/' | relative_url }})). Watts, durability (`fsync` / `wal_level`), and checkpoint columns travel with the OSM rows.

## OSM

Best OpenStreetMap planet load per CPU and configuration (host-local client). Throughput is **kNodes/s**; lower **hours** is faster. Study cells with `fsync=off` / `wal_level=minimal` stay on the board and are labeled, not hidden.

![OSM load leaderboard — best run per server configuration]({{ '/images/pg18-osm-leaderboard.png' | relative_url }})

Full ranked table, including package power: [OSM Leaderboard (PG18 snapshot)]({{ '/results-summary/pg18/osm-leaderboard/' | relative_url }}). Workload notes: [OSM]({{ '/workloads/osm' | relative_url }}).

## pgbench SELECT

Phoronix-comparable **SELECT** cells: `-M prepared`, **90s**, scale 100, single-client and full-client. Package power and memory sit on the same row as TPS; Postgres developers care whether a code change moves those up or down. For hardware outside this lab, use [OpenBenchmarking.org pts/pgbench](https://openbenchmarking.org/test/pts/pgbench) as the comparable TPS set.

The board has two faces: on-box unix sockets, and a network client. Multi-million TPS on OpenBenchmarking is the networked face on DC hardware (fast interconnect, on the order of a thousand clients)—not unix sockets sharing the server with pgbench. A sockets-versus-network mapping study will be published once. The remote rate sweep (same Mbps labels as [OSM Network]({{ '/results-summary/pg18/osm-network/' | relative_url }})) sits with that study, not as a third ranking.

Current published SELECT grid (older mix of protocols): [pgbench SELECT (PG18 snapshot)]({{ '/results-summary/pg18/pgbench-select/' | relative_url }}). Workload notes: [pgbench grids]({{ '/workloads/' | relative_url }}).

### Sockets

Unix-domain connections (`SOCKETS=1`), prepared statements. Clients run on the server.

### Networked

TCP to a dedicated client (`host`), prepared statements. Unthrottled only on this board. This is the face that can exceed on-box rates once the link is faster than ~10Gb/s.

## Contact

Greg is on Discord or e-mail. This page is the lab ranking, not an open submission program.
