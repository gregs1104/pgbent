---
layout: home
title: CBC Workload
permalink: /workloads/cbc
nav_order: 10
parent: Workloads
has_children: true
---

Complete Block Check (CBC) stresses multiple major parts of block I/O in the database using synthetic test data. It was developed against PostgreSQL 15 and uses CREATE TABLE AS, VACUUM, CREATE INDEX, and CLUSTER. Two simple but difficult to execute queries are run along the way, initially with a Sequential Scan. By the end one query should use a quick indexed lookup.

To learn about the individual statements of CBC, how and why they work, see the [CBC Tutorial]({{ '/workloads/cbc/tutorial/' | relative_url }}).

CBC runs anywhere you want—from a `psql` session to orchestration via `pgbench`. It has even been run on Crunchy's web-based [Postgres Playground](https://www.crunchydata.com/developers/playground) to compare browser block performance.

The design reviewed the fastest parts of all the earlier workloads and picked out the statements that caused the most stress. Then they were arranged as a data pipeline designed to evade caching. CBC aims to include the hardest simple block workloads available, discovered by reviewing the highest I/O statements and sequences in other workloads and then tweaking them to be more difficult or comprehensive. The database size is the main input. Just like the pgbench database, 2–4× RAM works well for CBC.

## Background

I've evaluated many benchmark ideas that stress storage before, usually using `pgbench` to generate the test database and workload. When I was working on loading the Open Street Map data, I noticed that `CREATE TABLE AS` is really fast now, fast enough to be a load generator if you have a wide table to work with. And there is a wide table in the system views: `pg_settings` has a lot of columns of all sorts of data types, a lot more variation than the trivial `pgbench` tables.

## Example collector output

Here's a lightly formatted example via the collector script. Hardware is AMD 7700X processor, 128GB RAM, SK41 2TB SSD; times are in milliseconds, sizes in bytes, disk rates in MB/s:

```
SERVER        siren
CREATE_TABLE  33116.420
VACUUM        9293.740
CREATE_INDEX  36316.109
SELECT_u1     832.447
SELECT_b      209.221
SELECT_r      2443.925
CLUSTER       87918.913
SELECT_u2     81.555
SELECT_c      80.997
SIZE_T        21837168640
SIZE_I        636223488
READ_RATE     2277.521
WRITE_RATE    2279.278
```

The READ/WRITE_RATE figures come from the VACUUM command and only apply to that line. During benchmark development, that command was frequently the highest-rate step. Note that this server was configured for performance rather than reliability, with WAL and all normal sync work disabled. In a default configuration vacuum work will usually hit a WAL bottleneck before it stresses CPU and disk to the extent this sample does.

## psql driver

You can run CBC in command-line `psql` like this:

```bash
psql -d $DB -v scale=$SIZEDB -ef tests/cbc/cbc-psql.sql > $OUTBASE.log 2>&1
```

For testing in a browser `psql` like the Crunchy PostgreSQL Playground, put the scale number in manually instead:

```sql
\set SIZEGB 1
```

## CLI collector driver

The program includes a standalone results collector script named `tests/cbc/cbc` that runs the benchmark and saves to a text file in the `results/` directory.

Inputs:

* Database size in GB. Defaults to 20.

Output is in the key/value style, shown as an example above.

## pgbench driver

The workload runs in `pgbench` utilizing its scale setting. To make this compatible with using `pgbench-tools` to monitor each step, the pieces are split into individual files, also allowing execution by multiple clients. Currently that includes:

```
cbc-t00-ctas.sql    cbc-t01-vacuum.sql    cbc-t02-index.sql
cbc-t03-select-max.sql    cbc-t04-selectr.sql    cbc-t05-cluster.sql
```

(All under `tests/cbc/`.)

Here's a manual run of the benchmark steps using `pgbench` to monitor each step:

```bash
createdb cbc
psql -d cbc -c "DROP TABLE settings_loop"
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t00-ctas.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t01-vacuum.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t02-index.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t03-select-max.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t03-select-max.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t04-selectr.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t05-cluster.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t03-select-max.sql cbc
pgbench -n -t 1 -c 1 -s 20 -f tests/cbc/cbc-t03-select-max.sql cbc
```

Many of these steps can only run once. The main SELECT query can of course be run in parallel. This example starts 4 clients running it for 120 seconds, same as the automated workload because that's usually enough to observe heat issues:

```bash
pgbench -n -T 120 -c 4 -s 20 -f tests/cbc/cbc-t03-select-max.sql cbc
```

Note that while the other methods of running CBC allow fractions of a GB for the size setting, `pgbench` scales must be integers of 1 or larger. To test under 1GB configurations with `pgbench` you'd need to adjust the way the input scale is handled.

## Automated workload driver

A pgbench CBC workload driver at `wl/cbc` is available to make it easier to run every step with individual metrics collection. `pgbench-tools` workloads generate a series of configuration files, run each test with `pgbench`, and save the results into a results database for analysis. A sample report at `reports/cbc-best.sql` shows the results with associated disk metrics. On the Mac this includes only disk0 throughput.

The workload version of CBC also includes a second copy of the `cbc-t03-select-max` script labeled to distinguish the runs expected to use an index. The test itself is identical; the script name is simply `cbc-t06-iselect-max` instead for identification and sorting.

## Storage throughput validation

To prove that CBC is effective at stressing system storage, four test systems were used:

* MacBook Pro 16: M1 Pro CPU, 16GB RAM, 1TB SSD
* MacBook Air 15: M2 CPU, 8GB RAM, 512GB SSD
* AMD Ryzen 7700X: 128GB RAM, 2TB SK41 SSD
* AMD Ryzen 5950X: 128GB RAM, 2TB Inland Performance PCI 4.0 SSD

Tests tried a range of sizes, and as usual for benchmarking like this 3–4× RAM was enough to reach maximum speed in most tests.

| CPU | RAM | DB GB | Script | Metric | Best | Max | % Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1 Pro | 16 | 32 | t00-ctas | R+W | 5107 | 5263 | 97% |
| M2 Air | 8 | 20 | t00-ctas | R+W | 2556 | 3238 | 79% |
| R9 5950X | 128 | 384 | t04-selectr | read | 4709 | 5000 | 94% |
| R9 5950X | 128 | 256 | t00-ctas | write | 4072 | 4300 | 95% |
| R7 7700X | 128 | 384 | t04-selectr | read | 6240 | 7000 | 89% |
| R7 7700X | 128 | 384 | t00-ctas | write | 6529 | 6500 | 100% |

On the Mac, disk I/O data collected with `iostat` groups read and write operations into one total. In theory then, the M1 Pro capable of 5263MB/s writes and slightly higher reads has a true theoretical max combined value of over 10GB/s.

Here though, max values for the Mac systems only reflect the one I/O operation that the tests involved exercise. For example, `t00-ctas` only generates write traffic. The max possible on that test is the system's best write speed, not the max possible for the combined R+W metric being measured.

Some other systems were lightly tested as well, and only the systems with strong thermal activity throttling failed to reach the 90% goal development aimed at. The passive cooling of the Mac M2 Air, for example, makes it extremely hard to reach maximum I/O rates within its thermal constraints.

## Credits

`cbc` was developed by Greg Smith as part of the PostgreSQL regression testing effort at Crunchy Data. The scripts are being initially released as part of the `pgbench-tools` repository.

## Dedication

Greg's benchmark lab names its many servers after favorite songs. The AMD AM5 7700X system used for this development was named for "Siren Song" on the 1993 Alan Parsons Album *Try Anything Once*, written by Alan Parsons Project guitarist Ian Bairnson with composer Frank Musker. Ian passed away in April of 2023 just as `cbc` validation started on siren. Ian was Greg's friend and he went out at the top! Ian played on Kate Bush's first hit, and her "Running Up That Hill (A Deal with God)" (with APP drummer Stuart Elliott) featured prominently in Season 4 of the hit show *Stranger Things*. That brought the song smashing back to the radio internationally and filled Ian's last year with press coverage.
