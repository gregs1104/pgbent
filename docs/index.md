---
layout: home
---

# pgbent

**pgbent** runs a Performance Farm on bare metal hardware for the PostgreSQL Community.  Code is hosted at **[github.com/gregs1104/pgbent](https://github.com/gregs1104/pgbent)**. Release summary snapshots and a general hardware leaderboard are published to the [getbent.io](https://getbent.io) documentation site. The best performing runs have been used to validate a [Tuning Model]({{ '/model/' | relative_url }}) for Postgres OLTP systems.

**[Leaderboards]({{ '/leaderboards/' | relative_url }})** — OSM planet load and pgbench SELECT rankings. Initial [PostgreSQL 19rc1 report]({{ '/results-summary/pg19/' | relative_url }}): 19 took the top spots with a tiny delta over 18 (rc1 2026-10-15, catalog 20261006).

![OSM score history by x86 CPU across PostgreSQL majors]({{ '/images/osm-history.png' | relative_url }})

The pgbent **OSM Score** grades how well PostgreSQL releases run on popular CPUs. The long-term history shows six years of tracked progress even as the underlying Planet extract has kept growing—a counterweight that slows the exponential hardware and software speedups so release-to-release and chip-to-chip gains stay readable. The same traces have also caught packaging and integration issues across PostgreSQL 16–18. Agent docs support reproducibility, and starting with PG19 the bulk of the data has been collected by agents.

## Workloads

Databases have a broad set of use cases—read-heavy web, OLTP stores, time series analysis, analytics—and each has enough dimensions that workloads must be precisely modeled to match. pgbent provides free, calibrated, auditable workloads that target known strong and weak spots of modern storage, and that respond predictably to database tuning.

pgbent includes a mix of fixed-size and automatically scaling workloads. Traces are collected over time as new software and hardware are introduced.

| Workload | What it exercises |
|----------|-------------------|
| [pgbench SELECT]({{ '/workloads/select/' | relative_url }}) | SELECT, nothing (`;`), and constant (`SELECT 1`) across client × size grids; sockets vs TCP, simple vs prepared |
| [OpenStreetMap import]({{ '/workloads/osm' | relative_url }}) | Real-world bulk load via osm2pgsql—COPY, index builds, checkpoint pressure |
| [Complete Block Check (CBC)]({{ '/workloads/cbc' | relative_url }}) | Short synthetic storage stress test (CTAS, VACUUM, CLUSTER, index scans) |

The OSM loader workload has produced the most interesting recent results, published as [blog posts](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours), [talks](https://www.youtube.com/watch?v=BCMnu7xay2Y), and [social media threads](https://x.com/postgresperf/status/1858905975446556876). CBC runs anywhere—from a `psql` session to a browser based Postgres.

## Tuning research

Sample results validate and extend the standard PostgreSQL [tuning guide](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server). The [Tuning Model]({{ '/model/' | relative_url }}) section documents studies of parameters that respond predictably to pgbent workloads:

- [shared_buffers]({{ '/model/shared_buffers' | relative_url }}) — buffer cache sizing and the ¼-RAM recommendation
- [max_wal_size]({{ '/model/max_wal_size' | relative_url }}) — WAL volume and checkpoint write smoothing
- [checkpoint_timeout]({{ '/model/checkpoint_timeout' | relative_url }}) — checkpoint frequency trade-offs
- [Linux dirty memory]({{ '/model/Linux_dirty_memory' | relative_url }}) and [pdflush / writeback]({{ '/model/Linux_pdflush' | relative_url }}) — OS-level writeback behavior during heavy loads

Reference tuning configurations for OSM workloads live in the [`conf/`](https://github.com/gregs1104/pgbent/tree/main/conf) directory.

## Technical Highlights

pgbent runs repeatable workloads, collects system and database metrics at one-second resolution, and stores everything in a results database for regression testing, tuning studies, and long-term performance history.

- **Orchestrated test runs** — Automate pgbench client × database-size grids and arbitrary custom workload scripts.
- **Deep metrics collection** — One-second resolution sampling into a PostgreSQL results database, without monitor averaging that hides peak GB/s behavior.
- **Human-readable internals** — Metrics grade how effectively each test stresses CPU and storage, useful for tuning training and regression diagnosis.
- **Configuration capture** — Server hardware, OS details, and PostgreSQL settings recorded with every run.
- **SQL and visual analysis** — Reports in the `reports/` directory; the [leaderboards]({{ '/leaderboards/' | relative_url }}) page is the public ranking; [PostgreSQL 19]({{ '/results-summary/pg19/' | relative_url }}) and [PostgreSQL 18]({{ '/results-summary/pg18/' | relative_url }}) keep the study tables.
- **Easy to extend and audit** — Workloads are plain scripts; the metrics system is transparent shell and SQL.

## How it works

While a workload runs, pgbent records system activity and a package of PostgreSQL internals—`pg_stat_statements`, `pg_buffercache`, and any custom SQL you attach. Metrics land in a separate results database, where summary SQL gives immediate feedback and Python/Pandas scripts draw workload summaries and per-metric time series.

When pgbent runs on the database server itself, it captures hardware and OS configuration and uses that to help size workloads. The included example metric query records client counts; you can change or extend it to watch anything readable via SQL.

Shell scripts (`benchwarmer`, `runset`) orchestrate each run. Scale and client combinations that share a common configuration—one `postgresql.conf`, one software build, one hardware platform—are grouped into a **test set** for comparison. See [How pgbent works]({{ '/introduction/' | relative_url }}) for more on metrics collection and test-set organization.

## Getting started

1. Clone [pgbent from GitHub](https://github.com/gregs1104/pgbent).
2. [Set up]({{ '/setup/' | relative_url }}) the test and results databases.
3. [Run tests]({{ '/running/' | relative_url }}) with `./runset` or `./benchwarmer`.
4. [Review results]({{ '/results/' | relative_url }}) with SQL reports or `./webreport`.

See also: [Reports]({{ '/reports/' | relative_url }}), [Version compatibility]({{ '/versions/' | relative_url }}), and [Troubleshooting]({{ '/troubleshooting/' | relative_url }}).

## Links

- [Leaderboards]({{ '/leaderboards/' | relative_url }}) — OSM and pgbench SELECT rankings
- [PostgreSQL 19 results]({{ '/results-summary/pg19/' | relative_url }}) — initial 19rc1 report (OSM ranking, OSM power, pgbench SELECT)
- [PostgreSQL 18 results]({{ '/results-summary/pg18/' | relative_url }}) — full published study tables

- TOC
{:toc}
