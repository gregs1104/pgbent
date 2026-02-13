---
layout: home
title: shared_buffers
permalink: /model/shared_buffers
parent: Tuning Model
nav_order: 21
---

# shared_buffers

Postgres nails down a dedicated chunk of shared memory at startup time to hold its `shared_buffers` page cache.  Standard tuning practice makes this 1/4 of total memory in mid sized (1GB - 128GB of RAM) servers.

New pages are created in the buffer cache then written.  Reads of pages already there are counted as hits.  Misses go to the OS page cache, which will either return the page from its memory or send a read to storage.

PG servers work best when their working set all fits in RAM.  That means servers running in the optimal zone will not be reading that much from actual storage.  They'll be doing a lots of page transfers from the OS Cache to Postgres, then writing changes.  Modern processors usually have hard acceleration for memory moves, which make that style of read and write path performant.

## 1/4 RAM size recommendation

There's a scalability limit with large amount of shared_buffers.  The database doesn't get faster and faster just because it's given more memory to work with.  PG advice has long recommended the idea of using 1/4 of RAM for `shared_buffers`.  On my 128GB OSM test server results, 32GB gives good caching with low overhead.

Increase it to 48GB and it gets faster, but the CPU overhead of running the buffer cache makes that and higher values less efficient.   Eviction from the cache is done with a simple Clock Sweep method that requires multiple passes over the entire pool before something gets removed.  Obtaining locks on the buffer cache structures, with full database sementics, that adds overhead too.

Larger values ultimately take too much from the OS read cache as well.  Adding diversity to page evication logic, having both PG's reference counting and the OS's LRU approach, that triages some worst case behavior.

## Buffer hit overhead

The nailed down reads in `shared_buffers` look like the high performance path.  A buffer hit means no slow read to storage.

Reality is complicated.  `shared_buffers` is itself a bottleneck sometimes.  When the database has a page in memory anyway, it's subject to cleanup like vacuum.  Another process can have the page exclusively locked for changes.  On high performance host OSes like Linux, if any of that sort of concurrent activity is happening,  it could have been faster to just read the page from the OS page cache.  Heavily used pages are usually in there--that's the point of having everything in RAM.

# Deployment platform advances

Postgres then is not faster and more efficient at caching large read sets than Linux.  That distribution of work is not optimal, but it's been acceptable.  Work to improve an AIO path is ongoing and challenging.  Trying to access the underlying APIs in an OS neutral way has been a struggle since the first commit of POSIX `fadvise` support.  It hasn't been a higher priority because the current system works well enough to keep up with most hardware.  

Also, Postgres is aiming at the broadest possible user base.  That platform approach means everything only advances in time with the oldest systems in mass deployment.  Traditional DBMS deployment approaches might lock support to a short list of known good kernels; that isn’t practical for PG.

# Write benefits

If `shared_buffers` isn't always the fastest read path, what is it good for then?  The main OLTP job `shared_buffers` handles is absorbing writes to commonly used pages.  Everything from catalog changes to popular table index and data, they are assumed to be there already in the most common cases.  You can write a short note to WAL describing the change, amortize that write to the sequential WAL stream, and your transaction avoided a long random write to the backing page heap.

We know that large `shared_buffers` values (>48GB) struggle to deliver read gains.  But if you have a write workload that dirties 64GB per batch, you may still want to increase `shared_buffers` anyway.  You may pay some read overhead compared to Linux.  Absorbing those writes so they only happen once per checkpoint is the more important job.

## Eviction developent history

Databases need a robust Cache Replacement Policy deep in their core.  The current one in PG, a [Clock Sweep](https://en.wikipedia.org/wiki/Cache_replacement_policies#Clock_with_adaptive_replacement_(CAR)) method, wasn't built to be the best solution.  It was a [triage commit](https://www.postgresql.org/message-id/9533.1105991326%40sss.pgh.pa.us) to avoid foundational patents limiting what the PG community could do.
