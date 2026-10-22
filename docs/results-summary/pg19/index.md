---
layout: home
title: PostgreSQL 19
permalink: /results-summary/pg19/
parent: Results summary
nav_order: 0
has_children: true
---

# PostgreSQL 19 results

Starting snapshot of the **19rc1** cycle. Package date **2026-10-15**, catalog **20261006**. The public ranking URL is still **[Leaderboards]({{ '/leaderboards/' | relative_url }})**. Pages here keep the study tables and the 18↔19 notes.

19 took the top leaderboard spots, with a tiny delta over 18. That's how this lab judges a release; it's easier than tracking medians. CPU-bound SELECT is the canary; OSM barely moved. This is not a frozen close-out—siren is retesting OSM, court is filling the Spark SELECT μs split—but the grids that matter for a first look are in.

## Pin

| | |
| --- | --- |
| PostgreSQL | **19rc1** (catalog **20261006**) |
| Planet | current extract, **10.79 billion** nodes |
| Board cell (SELECT) | scale 100, **90s**, `SETTIMES=2`, clients 1–64 |
| OSM default | replica WAL, `fsync` on; fast cells (`fsync` off / `wal_level=minimal`) stay labeled |

## Studies so far

- [OSM Leaderboard]({{ '/results-summary/pg19/osm-leaderboard/' | relative_url }}) — 19rc1 load ranking vs PG18 on the same CPUs
- [OSM Power]({{ '/results-summary/pg19/osm-power/' | relative_url }}) — throughput vs package watts and joules
- [pgbench SELECT]({{ '/results-summary/pg19/pgbench-select/' | relative_url }}) — siren four-face connection sweep, txn/J, 18↔19

Disk traces behind the OSM bars: [OSM Leaders: Performance vs. Power]({{ '/leaderboards/osm-performance-power/' | relative_url }}). 1-client `;` / `SELECT 1` / lookup split: [pgbench SELECT]({{ '/workloads/select/' | relative_url }}).

## Not in this snapshot

Network Mbps, checkpoint timeout, and dirty-memory sweeps from PG18 have not been opened as PG19 studies. Abbey has not installed 19 during RC (Homebrew after GA). The 9600X joules-hole SKU is still the next hardware swap on siren, not a published cell.

## Machines

| Host | CPU | In this snapshot |
| --- | --- | --- |
| siren | R9 9950X | SELECT four faces (19rc1); OSM fast + durable |
| twilight | i5-13600K | OSM fast + durable |
| court | NVIDIA Spark | OSM set 5 (enough to start); SELECT four faces in the results DB, not on the ranking yet |
| abbey | M4 Max Studio | PG17/18 OSM on the current Planet; no PG19 during RC |
