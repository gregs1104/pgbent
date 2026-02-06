---
layout: home
title: shared_buffers
permalink: /model/shared_buffers
parent: Tuning Model
nav_order: 21
---

# shared_buffers

Postgres nails down a dedicated chunk of shared memory at startup time to hold its `shared_buffers` page cache.  New pages are created there then written.  Reads of pages already there are counted as hits.  Misses go to the OS page cache, which will either return the page from its memory or send a read to storage.

PG servers work best when their working set all fits in RAM.  That means servers running in the optimal zone will not be reading that much from actual storage.  They'll be doing a lots of page transfers from the OS Cache to Postgres, then writing changes.  Modern processors accelerate memory moves.  With that hardware acceleration, the code doesn't have to be expert in loop unrolling for the read and write path to deliver.

## 1/4 RAM size recommendation

There's a scalability limit with large amount of shared_buffers that shows up easily in benchmarks.  The database doesn't get faster and faster just because it's given more memory to work with.  We've long recommended people only use 1/4 of RAM for shared_buffers.  On my 128GB OSM test server results, 32GB gives good caching with low overhead.  Increase it to 48GB and it gets faster, but the CPU overhead of running the buffer cache--the locks, the the page eviction clocksweep--it makes higher values less efficient.  Larger values ultimately take too much from the OS reads as well.  Adding diversity to page evication logic, having both PG's reference counting and the OS's LRU approach, that triages some worst case behavior too.

Postgres is not faster and more efficient at caching large read sets than Linux.  That distribution of work is not optimal, but it's been acceptable.  Work to improve the AIO path is ongoing and challenging.  Trying to access the underlying APIs in an OS neutral way has been a struggle since the first commit of POSIX fadvise support.  It hasn't been a higher priority because the current system works well enough to keep up with most hardware.  PG development avoids speculation when it can, it takes on problems as proven examples of behavior and relevant OS APIs arrive.

## Buffer hit overhead

The nailed down reads in shared_buffers look like the high performance path, as it has been for much of database history.  A buffer hit means no slow read to storage.

Reality is always complicated.  shared_buffers is itself a bottleneck sometimes.  When the database has a page in memory anyway, it's subject to cleanup like vacuum.  Another process can have the page exclusive locked for changes.  If any of that sort of concurrent activity is happening, on high performance host OSes like Linux it could have been faster to just read the page from the OS page cache.  Heavily used pages are usually in there--that's the point of having everything in RAM.  

# Write benefits

If shared_buffers isn't always the fastest read path, what is it good for then?  The main OLTP job shared_buffers handles is absorbing writes to commonly used pages.  Everything from catalog changes to popular table index and data, they are assumed to be in there already in the most common cases.  You can write a short note to WAL describing the change, amortize that write to the sequential WAL stream, and your transaction avoided a long random write to the backing page heap.

We know that large shared_buffers values (>48GB) struggle to deliver read gains.  But if you have a write workload that dirties 64GB per batch, you may still want to increase shared_buffers anyway.  You may pay some read overhead compared to Linux.  Absorbing those writes to only happen once per checkpoint is the important job.

## Eviction

Running the clock sweep method that evicts pages from the cache was never a great solution.  It was a triage commit to avoid a whole pile of foundational patents limiting what the PG community could do.  PG has been lying low, getting by with what was available, waiting for the most obstructive of the relevant intellectual property to clear.
