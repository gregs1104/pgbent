---
layout: home
title: Model
permalink: /model/
nav_order: 1
has_children: true
---

# Tuning Model

Sample results from `pgbent` have been published as a reference to good PostgreSQL tuning practice.  pgbent has primarily published benchmark results optimizing the Open Street Map loading process as a way to validate whether the way that database is tuned for checkpoints and buffer cache is optimal.

There's already a tuning guide for osm2pgsql that accurately covers related information about this workload, and the OSM workload page here covers similar ground.  Outside of the loading stages bounded by the OSM's node cache, the rest of the loading work benefits from classic OLTP checkpoint tuning work.

## History

My pgtune project published early recommendations for a tuning model for Postgres.  The basic model has been reviewed academically and through years of practice.  The main deficiency noted was not allocating enough space for WAL data, the modern setting that's `max_wal_size`.  That was already well understood in the context of the TPC-C, but difficult to replicate in public given the restrictions around TPC-C results.

This was frustrating enough to spawn a few alternative projects to finish the sort of thorough investigation into checkpoints suggested by the review.  What worked as well as a research method for checkpoint performance was increasingly fast runs loading the Open Street Map data.  Originally a source of CPU bottlenecks, the current osm2pgsl loader stresses the database's buffer cache heavily during its multiple COPY bulk loading phases, during regular index building, and building inverted Geospatial indexes.
