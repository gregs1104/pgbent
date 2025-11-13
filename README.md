pgbent is a benchmarking toolkit for testing PostgreSQL databases.  As a performance regression testing tool, the program has caught multiple bugs in PostgreSQL itself.  pgbent includes load generation orchestration features with arbitrary workload scripts and metrics collection going into a PG database for analysis.

[Documentation](https://getbent.io)

_pgbench_ is the best supported load generator but that's not all it handles.  You can supply any script and get a results database comparing it across multiple runs, recording second level precision system metrics and whatever arbitrary database internals queries you want to attach.  A sample connection count query is bundled, you can change or extend that to collect anything you can read via SQL--which for Postgres means just about anything!

While there are plenty of other options for running PostgreSQL scripts and collecting system metrics, the way _pgbent_ is assembled is aimed at providing repeatable standard workloads that can be used for regression testing and audited for correctness .  That tookit has allowed creating a small set of novel synthetic database workloads that target the known strong and weak spots of modern storage, ones that respond predictably to database tuning.  Database storage is tricky stuff, and any amount of the metrics time averaging typical to monitoring tools obliterates the interesting GB/s peak behavior of modern SSD.

![osm2pgsql workload](reports/images/samples/twilight-1494-read-write.png)

For a few years now, the most interesting benchmark results have been the Open Street Map tests, published as [blog entries](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours), [talks](https://www.youtube.com/watch?v=BCMnu7xay2Y), or [social media posts](https://x.com/postgresperf/status/1858905975446556876).  That runs via the pgbent's artibrary workload interface script.

There's also a new storage stress test sample program included, [Complete Block Check](tests/cbc/README.md).  That runs anywhere you want, from a psql session to orchestrated via pgbench generating its workload.   I've even run it on our web based [Postgres Playground](https://www.crunchydata.com/developers/playground) to compare web browser block performance. Seriously!

## Known issues

* On Solaris, where the benchwarmer script calls tail it may need
  to use `/usr/xpg4/bin/tail` instead
  
## Planned features

The planned follow up tech refresh coming in later 2025 is deprecating use of _gnuplot_ in favor of Python Pandas based graphs.  Right now Pandas is behind my slides and social media graph posts; there's still a few old gnuplot graphs left to replace.

Some older ideas that may be implemented include:

* Graphs for buffers/checkpoints throughtout 
* Fix the static number of scales/clients for rates_webreport
* Fix zombie files when crash of bench on OS-stats processes

## Contact

The project is hosted at https://github.com/gregs1104/pgbent

There are old versions hosted on by the PostgreSQL project at http://git.postgresql.org/git/pgbench-tools.git
or http://git.postgresql.org/gitweb that have not been updated in some time now.

If you have any hints, changes, improvements, or please contact:

 * Greg Smith gregs1104@gmail.com
 
Notable forks
=============
 
* Future featured upgrades and bug fixes:  https://github.com/emerichunter/pgbench-tools
* Full bash to Python port adding Windows compatibility:  https://github.com/rugging24/pg_pybench

Credits
=======

Copyright (c) 2007-2025, Gregory Smith
All rights reserved.
See COPYRIGHT file for full license details and HISTORY for a full list of
other contributions to the program.

Major contributors:

* Josh Kupershmidt <schmiddy@gmail.com>
* Emeric Tabakhoff <etabakhoff@gmail.com> or <e.tabakhoff@loxodata.com>

******
References:
1. Introduction [1](https://emerichunter.github.io/pgbench-tools-p1/) & [2](https://emerichunter.github.io/pgbench-tools-p2/)
and in french [1](https://www.loxodata.com/post/benchmarking-pratique/) & [2](http://www.loxodata.com/post/benchmarking-pratique2/)

