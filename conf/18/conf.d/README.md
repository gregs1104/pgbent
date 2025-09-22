PostgreSQL configuration file set for pgbent testing.

Intended to be deployed to a PostgreSQL server's configuration
include directory. This avoids making major, difficult to track
edits directly to the postgresql.conf file.  With this approach,
only the port number and locale related data like locale would
be in the main config file. 

Files set to .conf are used.  Unused files are labeled as .off instead.

# Install - Debian/Ubuntu - copy
On Debian/Ubuntu, a suitable directory is setup for you already as:

    /etc/postgresql/<version>/main/conf.d

You could check out this pgbent repo into the postgres
user's home directory, then just copy all of these files
into that directory and modify from there.  Example:

    cd /etc/postgresql/17/main/conf.d
    cp ~postgres/pgbent/conf/17/conf.d/* .

## Install - Debian/Ubuntu - sym link
Alternately, for a system that's only running pgbent, you could remove the
conf.d directory and replace it with a sym link to where you have pgbent
cloned at.  Example: 

    cd /etc/postgresql/<version>/main/
    rmdir conf.d
    ln -s ~postgres/pgbent/conf/17/conf.d

# Open Street Map osm2pgsql examples

There are two OSM loading durability examples, one with standard durability
and a default one intended to be as fast as possible instead.
To switch from the fast version to the durable, replication aware version:

    mv osm-sync-durable.conf osm-sync-durable.off
    mv osm-sync-fast.conf osm-sync-fast.off

There are 3 different OSM memory size examples.  These assume you are
running osm2pgsql on the server itself, so settings like
effective_cache_size are smaller than a normal server.
For example, to switch from the standard 128GB to the 16GB one:

    mv osm-mem-128.conf osm-mem-128.off
    mv osm-mem-16.off osm-mem-16.conf
