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

WAL volume, fsync waits, and full-page writes are **separate** pairs (PG19).
Exactly one of each is `.conf`. Default is production: replica + fsync on +
FPW on. Historical bundled `osm-sync-fast` was all three off plus
`wal_level=minimal`.

    # thin WAL, keep fsync (and FPW) on
    mv osm-wal-replica.conf osm-wal-replica.off
    mv osm-wal-minimal.off osm-wal-minimal.conf

    # no fsync waits, keep replica WAL
    mv osm-fsync-on.conf osm-fsync-on.off
    mv osm-fsync-off.off osm-fsync-off.conf

    # FPW off only if WAL bytes still need explaining (not the 2×2 default)
    mv osm-fpw-on.conf osm-fpw-on.off
    mv osm-fpw-off.off osm-fpw-off.conf

OSM memory tiers (`osm-mem-{16,32,48,64,96,128}`) assume osm2pgsql runs on
the server itself, so `effective_cache_size` is smaller than a normal
dedicated-DB host. Exactly one should be `.conf`. Prefer the NOPASSWD helper:

    sudo /usr/local/bin/pgbent_drop_caches --test-shared-buffers 48 19 main
    # optional: --prefix osm-mem (default); other families use --prefix NAME
    # or from a checkout with config sourced: util/test-shared-buffers 48


Manual flip example (128GB tier → 16GB):

    mv osm-mem-128.conf osm-mem-128.off
    mv osm-mem-16.off osm-mem-16.conf
