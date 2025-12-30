---
layout: home
title: OSM Workload
permalink: /workloads/osm
nav_order: 10
parent: Workloads
---

## osm2pgsql Workload

The osm2pgsql loading program populates the entire Open Street Map planet data set.  Based on the options you can get a svelte version suitable for production, or one with fully decoded metadata build options at about 750GB.  Until about 2020 there were multiple heavy CPU bound problems running this loader.  Major improvements in the Open Street Map distribution, loading workflow, and the underlying PostgreSQL on Linux platform turned the loading into a capable SSD challenger.  Particularly useful were its chain of CTAS single core work speeding up and CREATE INDEX becoming multi-process.  

 The main downside of this test is that you can't reach the high speeds unless you have a client available capable of caching the entire `nodes` data file, which is growing steadily toward where the popular 96GB threshold can barely host it.  That size has only recently become feasible on Apple Silicon Mac hardware, and that's limited the practicality this workload to measure OS X fairly so far.  Correspondingly that's made it hard for this one workload to be a fully general PostgreSQL testing platform.

![osm2pgsql workload](/images/twilight-1494-read-write.png)

For a few years now, the most interesting benchmark results have been the Open Street Map tests, published as [blog entries](https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours), [talks](https://www.youtube.com/watch?v=BCMnu7xay2Y), or [social media posts](https://x.com/postgresperf/status/1858905975446556876).  That runs via the pgbent's artibrary workload interface script.  It's classic shell scripting work, there's no use of pgbench.

