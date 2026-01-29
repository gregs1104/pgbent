---
layout: home
title: Tuning Model
permalink: /model/
nav_order: 20
has_children: true
---

# Tuning Model

Sample results from `pgbent` have been published as a reference to good PostgreSQL tuning practice.  pgbent has primarily published benchmark results optimizing the Open Street Map loading process as a way to validate whether the way that database is tuned for checkpoints and buffer cache is optimal.

There's already a tuning guide for osm2pgsql that accurately covers related information about this workload, and the OSM workload page here covers similar ground.  Outside of the loading stages bounded by the OSM's node cache, the rest of the loading work benefits from classic OLTP checkpoint tuning work.

## History

My pgtune project published early recommendations for a tuning model for Postgres.  The basic model has been reviewed academically and through years of practice.  The main deficiency noted was not allocating enough space for WAL data, the modern setting that's `max_wal_size`.  That was already well understood in the context of the TPC-C, but difficult to replicate in public given the restrictions around TPC-C results.

This was frustrating enough to spawn a few alternative projects to finish the sort of thorough investigation into checkpoints suggested by the review.  What worked as well as a research method for checkpoint performance was increasingly fast runs loading the Open Street Map data.  Originally a source of CPU bottlenecks, the current osm2pgsl loader stresses the database's buffer cache heavily during its multiple COPY bulk loading phases, during regular index building, and building inverted Geospatial indexes.

## Postgres CPU Hardware

pgbent's OSM results represent a medium memory sized Apple Silicon vs. Intel vs. AMD showdown that's been long in the making.  I've been publishing Intel shootouts [since 1996](https://web.archive.org/web/19980521093812/http://westnet.com/~gsmith/memory.htm) when the competitors were Cyrix and VIA!  In 2020 I did a release day preview of [Apple Silicon's M1](https://www.crunchydata.com/blog/postgresql-benchmarks-apple-arm-m1-macbook-pro-2020).  It's only recently they've released models with enough memory to run more interesting database workloads.

The goal of documenting the best we can do on Apple's popular and standardized hardware platform gives an easy to replicate arm64 result that other core PostgreSQL development can use as a reference.
