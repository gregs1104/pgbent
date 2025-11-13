---
layout: home
title: Versions
permalink: /versions/
nav_order: 8
---

# Version compatibility

The default configuration now aims to support the pgbench that ships with
PostgreSQL 9.6 and later versions, which uses names such as "pgbench_accounts"
for its tables.  There are commented out settings in the config file that
show what changes need to be made in order to make the program compatible
with PostgreSQL 8.3, where the names were like "accounts" instead.

pgbench went through major changes in version 9.6, and the random function
used in most test scripts was renamed.  The main tests/ directory has the
current scripts for versions 9.6, 10, 11, 12, and 13 (so far).

To test against versions 8.4 through 9.5, use the tests/tests-9.5 directory
in the confile file.

Support for PostgreSQL versions before 8.3 is not possible, because a
change was made to the pgbench client in that version that is needed
by the program to work properly.  It is possible to use the PostgreSQL 8.3
pgbench client against a newer database server, or to copy the pgbench.c
program from 8.3 into a 8.2 source code build and use it instead (with
some fixes--it won't compile unless you comment out code that refers to
optional newer features added in 8.3).

## Multiple worker support

Starting in PostgreSQL 9.0, pgbench allows splitting up the work pgbench
does into multiple worker threads or processes (which depends on whether
the database client libraries haves been compiled with thread-safe 
behavior or not).  

This feature is extremely valuable, as it's likely to give at least
a 15% speedup on common hardware.  And it can more than double throughput
on operating systems that are particularly hostile to running the
pgbench client.  One known source of this problem is Linux kernels
using the Completely Fair Scheduler introduced in 2.6.23,
which does not schedule the pgbench program very well when it's connecting
to the database using the default method, Unix-domain sockets.

(Note that pgbench-tools doesn't suffer greatly from this problem itself, as
it connects over TCP/IP using the "-H" parameter.  Manual pgbench runs that
do not specify a host, and therefore connect via a local socket can be
extremely slow on recent Linux kernels.)

Taking advantage of this feature is done in pgbench-tools by increasing the
MAX_WORKERS setting in the configuration file.  It takes the value of `nproc`
by default, or where that isn't available (typically on systems without a
recent version of GNU coreutils), the default can be set to blank, which avoids
using this feature altogether -- thereby remaining compatible not only with
systems lacking the nproc program, but also with PostgreSQL/pgbench versions
before this capability was added.

When using multiple workers, each must be allocated an equal number of
clients.  That means that client counts that are not a multiple of the
worker count will result in pgbench not running at all.

Accordingly, if you set MAX_WORKERS to a number to enable this capability,
pgbench-tools picks the maximum integer of that value or lower that the client
count is evenly divisible by.  For example, if MAX_WORKERS is 4, running with 8
clients will use 4 workers, while 9 clients will shift downward to 3 workers as
the best option.

A reasonable setting for MAX_WORKERS is the number of physical cores
on the server, typically giving best performance.  And when using this feature,
it's better to tweak test client counts toward ones that are divisible by as
many factors as possible.  For example, if you wanted approximately 15
clients, it would be best to use 16, allowing worker counts of 2, 4, or 8, 
all likely to match common core counts.  Second choice would be 14,
compatible with 2 workers.  Third is 15, which would allow 3 workers--not
improving upon a single worker on common dual-core systems.  The worst
choices would be 13 or 17 clients, which are prime and therefore cannot
be usefully allocated more than one worker on common hardware.
