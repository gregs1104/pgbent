---
layout: home
title: "CBC Tutorial: Benchmarking PostgreSQL block I/O with SQL"
permalink: /workloads/cbc/tutorial/
parent: CBC Workload
nav_order: 1
---

# CBC Tutorial: Benchmarking PostgreSQL block I/O with SQL

Databases queries with lots of clients are complicated to benchmark. The database comes with the `pgbench` client tool to help. But sometimes all you have is port 5432 access to the server, no available system to run `pgbench` on, and a benchmark running with just `psql` is a lot easier to explain.

Today then we'll show how to usefully test the basic speed of a server with a single client and simple workload. Tests will stress the speed block I/O occurs when creating new data and then scanning through it.

This document is being provided as text and as a full active tutorial using Crunchy's [Postgres Playground](https://www.crunchydata.com/developers/playground) tutorial system. When talking about the tutorial results here, that's the rates things run at in the playground.

## Data creation

First we need some benchmark data. PostgreSQL provides documentation of all its tuning and setup parameters with a system view named `pg_settings`. This is a fairly wide table with a multitude of data types, from small numbers to text descriptions. There are about 350 lines in the table.

```sql
SELECT count(*) from pg_settings;
\x on
SELECT * FROM pg_settings LIMIT 1;
```

One copy of all these rows takes up just over 90K. The PostgreSQL `generate_series` function is easy to use for data generation. By joining `pg_settings` with a generated table, we can easily target some number of gigabytes of data to create. For a serious test you would want the database to be at least 2× the amount of memory in the server. Even a single gigabyte is a useful sized test workload for these tests, because they're statements trying to evade easy caching.

For this browser based tutorial 1/10 (0.1) of a GB gives a tolerable workout wait time; these steps can take 15–60 seconds:

```sql
\timing
\set SIZEGB 0.1
SET track_io_timing=on;
CREATE TABLE settings_loop AS SELECT gs.x AS seq,pgs.* FROM
  generate_series(0, :SIZEGB * 12500,1) gs(x)
  LEFT JOIN pg_settings pgs ON (true);
SELECT pg_size_pretty(pg_relation_size('settings_loop')) AS "Size-Table";
```

Tutorial systems tested so far run this query at around 2% the speed of the heavily optimized bare metal test servers here, which create the table in about 300ms. For consistent results on a more serious benchmark, you'd need to execute database `checkpoint` and operating system `sync` commands to flush everything to disk after this.

## Data cleanup for use

After you add rows to the database, there is a period where you can abort that transaction and roll back its creation. After enough transactions have gone by, eventually the transaction becomes permanent, what is called frozen, and its transaction number reclaimed. That all normally happens as Autovacuum background activity, slowly processing within moments of the transaction being committed.

We can force it to happen immediately and all at once instead. That speed is itself an interesting benchmark result, and getting it out of the way keeps the background work from impacting the next tests we run.

```sql
VACUUM (FREEZE ON, ANALYZE ON, VERBOSE ON) settings_loop;
```

The test servers here run this size in about 230ms, and the tutorial servers manage about 3% of that speed. If you design your database with small enough partitions, you can spot clean newly imported data like this in production, perhaps as an overnight job.

Running vacuum like this will give you a quick read on how fast one client can stress the system disks. Limitations of the tutorial server don't show that number; here are a few examples for your reference, from servers tuned for fast benchmarks with replication off:

* Apple M2 Air, peak SSD about 5GB/s: avg read rate: 937.057 MB/s, avg write rate: 1110.027 MB/s
* AMD r7700X, peak SSD about 6.5GB/s: avg read rate: 2228.507 MB/s, avg write rate: 2263.396 MB/s

## Unindexed queries

Since there are no indexes yet, running a query against this database forces a table Sequential Scan. Standard PostgreSQL will give you two workers to execute that in parallel. You need to run that query twice to get useful timing data; the second one will hopefully execute against cached data instead of reading from disk.

```sql
EXPLAIN (ANALYZE ON, BUFFERS ON) SELECT max(sourceline)
  FROM settings_loop WHERE name='shared_buffers';
EXPLAIN (ANALYZE ON, BUFFERS ON) SELECT max(sourceline)
  FROM settings_loop WHERE name='shared_buffers';
```

On the Linux 7700X server, the whole data set moves into cache in 2.2ms and repeats all take 0.6ms. The Mac takes 3.5ms when the data is cold and repeats are also around 0.6ms. Interestingly on Mac repeats can slowly speed up if done together quickly enough. The effect is most obvious on larger queries than the 0.1GB sample here.

To use more of the database features, here's how to pull 1% of the data out from the middle of the table, again without an index to help:

```sql
EXPLAIN (ANALYZE ON, BUFFERS ON) SELECT max(sourceline)
  FROM settings_loop WHERE seq < :SIZEGB * 6250 LIMIT :SIZEGB * 125;
```

Bare metal averages 23.5ms here; the tutorial server reaches about 0.8% of that speed.

## Adding an index

The settings name is the most useful key for the queries being run here. We can add an index on it:

```sql
CREATE INDEX by_name ON settings_loop (name);
SELECT pg_size_pretty(pg_relation_size('by_name')) AS "Size-Index";
```

The index is 30MB; dedicated hardware takes 200ms to build it; the tutorial server achieves almost 2% of that speed.

Unfortunately that index alone cannot help slim down the data read because the rows themselves repeat across every disk page. Since the table itself is ordered by the `seq` column, you have to touch every block of the table to find anything in it.

## Table build for query speed

What this table really needs is to be ordered by `name` instead of `seq`. PG allows that if you can afford the downtime of rewriting the entire table with the CLUSTER command.

```sql
CLUSTER verbose settings_loop USING by_name;
```

Here tweaked bare metal has Best/Average/Worst times of 354/562/772ms; the tutorial server maintains 2% of that.

The differences in OS caching and other speed tweaks are really highlighted by this clustering step. A system optimized with no WAL and reduced sync requirements can easily go twice the speed of the fully safe default setup.

## Final query results

With that done, we can finally see a quick query time.

```sql
EXPLAIN (ANALYZE ON, BUFFERS ON) SELECT max(sourceline) FROM
  settings_loop WHERE name='shared_buffers';
EXPLAIN (ANALYZE ON, BUFFERS ON) SELECT max(sourceline) FROM
  settings_loop WHERE name='shared_buffers';
```

All the test systems run this in a short period, with the 4 hardware systems taking 0.3ms at this size. This form of quick query is hard for the tutorial system to execute fast; it runs at only 0.4% of the test bare metal speed. It might be surprising that the tutorial was more competitive running bulk I/O (2–3%) than quick queries (0.4–0.8%), but that's what the results consistently show.
