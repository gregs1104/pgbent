---
layout: home
title: Tuning Model
permalink: /model/
nav_order: 20
has_children: true
---

# Tuning Model

Sample results from `pgbent` have been [published](https://pgbent.streamlit.app/) as a reference to good PostgreSQL tuning practice, validating some parts of the standard PG [tuning guide](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server).  pgbent has primarily published benchmark results optimizing the Open Street Map loading process.  That provides way to validate whether the way that database is [tuned](https://github.com/gregs1104/pgbent/tree/main/conf) for checkpoints and buffer cache is optimal.

There's already a [osm2pgsql tuning guide](https://osm2pgsql.org/doc/manual.html#tuning-the-postgresql-server) that accurately covers related information about this workload.  The [OSM workload](https://getbent.io/workloads/osm) page here covers similar ground.  Outside of the loading stages bounded by the OSM's node cache, the rest of the loading work benefits from classic OLTP checkpoint tuning work.

## History

My [pgtune](https://github.com/gregs1104/pgtune) project published early recommendations for a tuning model for Postgres.  The basic model has evolved through years of practice and been reviewed academically.  The main deficiency noted (see [CMU](https://db.cs.cmu.edu/papers/2017/p1009-van-aken.pdf), end of section 7) was not allocating enough space for WAL data, the modern setting that's `max_wal_size`.  That parameter is well understood in the context of the TPC-C.  It's been difficult to replicate in public given the restrictions around both TPC-C result disclosure and so much earlier work operating under the commercial database [DeWitt Clause]
(https://www.brentozar.com/archive/2018/05/the-dewitt-clause-why-you-rarely-see-database-benchmarks/).

This was frustrating enough to spawn a few alternative projects to finish the sort of thorough investigation into checkpoints suggested by the review.  What worked as well for this project's research method for checkpoint performance was increasingly fast runs loading the Open Street Map data.  While earlier the loader itself suffered CPU bottlenecks moving XML around, the modern [Protocol Buffers](https://protobuf.dev/) osm2pgsl loader stresses the database's buffer cache heavily.  It has a few clear phases with multiple COPY bulk loading phases, regular B-tree index building, building inverted Geospatial indexes, and building inverted GIN indexes.

## Postgres CPU Hardware

pgbent's OSM results represent a medium memory sized Apple Silicon vs. Intel vs. AMD showdown that's been long in the making.  I've been publishing Intel shootouts [since 1996](https://web.archive.org/web/19980521093812/http://westnet.com/~gsmith/memory.htm) when the competitors were Cyrix and VIA!  In 2020 I did a release day preview of [Apple Silicon's M1](https://www.crunchydata.com/blog/postgresql-benchmarks-apple-arm-m1-macbook-pro-2020).  It's only recently they've released models with enough memory to run more interesting database workloads.

A goal of documenting the best we can do on Apple's popular and standardized hardware platform is to provide an easy to replicate arm64 result that other core PostgreSQL development can use as a reference.
