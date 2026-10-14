---
name: pg-release-runs
description: >-
  Open and run pgbent studies during a PostgreSQL release cycle such as PG19:
  flag a study with newset on each participating machine, run the workload
  (osm2pgsql planet load, pgbench grids, or custom), validate, and ship the
  results with upload/download for assembly. Use when a new study topic comes up, when preparing a
  server for a release cycle, or when launching or babysitting study runs.
disable-model-invocation: true
---

# Release study runs

A release cycle starts with **no studies**. When a topic comes up (a new
GUC, a suspected regression, new hardware, an OS setting), a study is opened by
flagging test sets with `newset` on each machine that will take part. Several
studies run in parallel across the fleet. Once enough machines have reported,
the study's data is assembled (see `pg-release-publish`). Config prep is
covered by `pg-release-config`.

## How a study is identified

`./newset 'description'` inserts a `testset` row (`server`, `set` serial, `info`).
Every test run afterward on that machine belongs to that set until the next `newset`.
In `submission`, these appear as:

| Column | Source | Scope |
|--------|--------|-------|
| `batch` | `testset.info`, the newset description | **The cross-machine study key** |
| `batch_id` | `testset.set` | Per-server serial; not comparable across machines |
| `server` | `SERVERNAME` | Machine |
| `category` | `testset.category` | NULL means publishable; set it to retire or hide a set |

Study SQL selects by these columns. The PG18 dirty-memory study used
`server='siren' AND batch_id BETWEEN 35 AND 41`, which is a single-machine study selected by set range.
For a multi-machine study, **use the same description prefix on every machine**
so assembly can match on `batch`.

## Opening a study

```
Study: <topic>
- [ ] Write down the question and the one variable being changed (GUC, node cache, etc.)
- [ ] Confirm the active set is still the right batch (same major version, same planet, same non-GUC context)
- [ ] Choose the participating machines and the shared conf/<N> baseline
- [ ] On each machine: apply the setting → reload/restart → run the workload (same set)
- [ ] Reports split variants via test_settings (fsync, wal_level, shared_buffers, …), not via a new set
```

### When to call `newset`

A set is a **batch of related work**, not one config. Report SQL expects multiple
`postgresql.conf` combinations in the same set and filters on `test_settings`.
Trying a new set for every GUC change was a mess; the PG18 history is full of
sets that mix parameter combinations on purpose.

Call `./newset` when something **beyond Postgres GUCs** changes, for example:

- A new PostgreSQL major (or a named beta/RC campaign worth separating)
- A new raw planet dump / OSM data vintage
- A different workload script family, client topology, or hardware role that should not mix with the current batch

Do **not** open a new set just to flip `osm-sync-*`, `osm-mem-*`, `maintenance_work_mem`, or other GUCs. Change the files, reload, keep running under the same `testset.info`.

Rules for running studies in parallel:

- **One active set per machine.** Runs go to whichever set was flagged last.
- **Change one GUC (or node-cache) variable at a time** within that set so
  `test_settings` stays attributable. Reset the previous variant before the next.
- **Baseline runs can feed several studies.** PG18's leaderboard and power studies
  drew on the same default-config OSM loads in shared sets.
- **Ask before setting `category`** on another study's sets; it removes them from publishing.
  Set it on the source machine, because the central copy is replaced on every `download`.

## Server prep (once per server per cycle)

```
- [ ] In ~postgres/pgbent: `git stash && git pull && git stash apply`
      The server's checkout will not have `conf/<N>` until this pull. `config` and `params` are dirty on every host, so stash first and apply after.
- [ ] Install PostgreSQL <N> (plus PostGIS, hstore for OSM) and deploy conf/<N>/conf.d
- [ ] Edit ./config: TESTHOST/TESTPORT/TESTDB, RESULTHOST/RESULTDB, SERVERNAME, DISKLIST, ARCHIVE
- [ ] Install sudo helpers in /usr/local/bin with NOPASSWD rules (see each script header):
      util/pgbent_tune (governor=performance, readahead 4096, fstrim)
      util/pgbent_powermon (power sampling; set SUDODATA=1 in config)
- [ ] Update the `server` table row (cpu/mem/disk/OS) if hardware changed — submission reports the human-readable disk from it
- [ ] Confirm osm2pgsql version: `osm2pgsql --version`; set SCRIPT in wl/osm-import to match (it still says osm2pgsql-1.6)
- [ ] Planet + flat nodes paths: PLANET_FILE / NODES_FILE (defaults ~/osm/planet-latest.osm.pbf, nodes.db)
```

`SERVERNAME` defaults to the hostname. It is part of every study key, so keep it stable for the whole cycle.
It must not contain `-`, because `download` parses the server name from the archive filename.

One machine is configured by hand and is where the process gets written down. For this cycle that machine is **siren**, and only Greg works on it. A second machine, usually an easier build, receives only what has been committed and pulled. For this cycle that machine is **twilight**. Do not invent steps on the second machine that are not yet in the repo.

Two other machines are active:

- **abbey** is a Mac Studio on PostgreSQL 17 installed with Homebrew. Its PG17 tests on the 2026 planet are finished. Next is an update to PostgreSQL 18 and a retest.
- **court** is an NVIDIA DGX Spark (ARM64). As of 2026-10-14 it is on **DGX OS 7.6.0 / Ubuntu 24.04.5** with kernel **`7.0.0-1019-nvidia`**. That is the DGX OS 7 kernel update, not Ubuntu 26.04 (DGX OS 8 is a different line and is not supported on Spark yet). It is still on the PostgreSQL **16** launch configuration and was running an OSM load after the reboot. The hardware has been unreliable about booting; the force-restart procedure that worked last time has not been written down here yet.

### Planned study: node cache vs shared_buffers (after identical PG19 baselines)

Do **not** open this until all four servers (siren, twilight, abbey, court) are on PostgreSQL 19 with the same durable `conf/19` baseline and the same one-point OSM load (`osm2pgsql-1.11`, 5 clients, same `scale` / `OSMNODECACHE`).

**Question.** The PG17 OSM config was a local maximum: high memory use that delivered peak throughput. Parallel GIN / index work in PG18 destabilized that peak (see the final PG18 retune commit). On 128GB hosts the node-cache phase packs `osm2pgsql` RSS (~60GB at scale 75000), `shared_buffers` (48GB in `osm-mem-128`), and shared memory into RAM and spills into the default ~15GB swap. When the loader enters the index phase it **drops the node cache**; Postgres pages that were pushed out are not pulled back automatically, then `maintenance_work_mem` × parallel maintenance workers allocates on top. Suspect the fix is to shrink **either** the osm2pgsql node cache (`scale` / `OSMNODECACHE` in `params`) **or** `shared_buffers` (`osm-mem-*`), not to keep chasing the PG17 packing.

**How to run it.** Stay on the existing PG19 set. Change one variable at a time
(`osm-mem-*` tier or `scale` / `OSMNODECACHE`), keep durability durable, and let
report SQL separate the rows via `test_settings`. Compare hours, `nodes_kips`,
`index_kips`, and swap/iowait across the index transition (`watch util/progress`,
`free -h`, `results.txt` leaving node processing). Promote a winner into
`conf/19` only with a commit that cites the study.

### Recorded setup: siren, PostgreSQL 19 (2026-10-13)

Taken from the `gsmith` and `postgres` shell histories. Failed typos are omitted. Older major versions stay installed; this setup does not remove PostgreSQL 18. On this host the benchmark drive is `/sk51` (same disk as the PG18 `main` cluster) and Debian assigned port **5437**.

As `gsmith`. The PGDG source line ends in the major version to install:

```bash
sudo mkdir /sk51/19
sudo chown postgres:postgres /sk51/19
# /etc/apt/sources.list.d/pgdg.list:
#   deb http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main 19
sudo apt update
sudo apt install postgresql-19 postgresql-19-postgis-3-scripts
```

The data-directory move below is specific to siren's 2TB disk. `conf/19` sets `max_wal_size = 100GB`, and that OSM load plus the planet database barely fits 2TB, so the old PG18 cluster had to be moved off that disk before PG19 could use it. A 4TB host such as twilight does not need that shuffle: leave the previous major installed and put the new cluster on the same drive. There are six test servers, and keeping their `params` identical by hand is the failure this setup is meant to avoid.

As `postgres`. Home is `/var/lib/postgresql`. The package creates the `19/main` cluster; `pg_createcluster` was also run. Move the data directory only while that cluster is stopped (`sudo systemctl stop postgresql@19-main` as `gsmith`).

```bash
cd ~/19
rsync -av --progress main /sk51/19/
mv main main.old
ln -s /sk51/19/main
pg_lsclusters
```

As `postgres`, update the pgbent checkout before copying config. A new major's `conf/<N>` is not on the server until this pull. Twilight already had `conf/19` only because the checkout had been fast-forwarded to `9959630` at 16:24; do not skip the pull on the next host.

```bash
cd ~/pgbent
git stash && git pull && git stash apply
```

As `gsmith`, deploy that config and the local trust rules, then start:

```bash
cd /etc/postgresql/19/main/conf.d
sudo cp ~postgres/pgbent/conf/19/conf.d/* .
cd /etc/postgresql/19/main
sudo vi pg_hba.conf    # trust block from ~postgres/pgbent/conf/pg-hba.trusted
sudo systemctl start postgresql@19-main
```

As `postgres`, point pgbent at the new port and confirm `util/newgis`:

```bash
cd ~/pgbent
# config: TESTPORT=5437
util/newgis            # creates gis; pg_stat_statements, pg_buffercache, postgis, hstore; pgbent_tune
```

Leave only two clusters online: the results database and the active one. On siren the results database is still the PostgreSQL 17 cluster (port 5433). Everything else stays installed and is stopped:

```bash
pg_lsclusters
sudo systemctl stop postgresql@15-main
sudo systemctl stop postgresql@16-main
sudo systemctl stop postgresql@18-main
sudo systemctl stop postgresql@18-nocheck
```

That leaves `17/main` and `19/main` online.

As `postgres`, confirm the running server is PostgreSQL 19 and that the 128GB memory tier from `conf/19/conf.d/osm-mem-128.conf` loaded. On siren `psql -p 5437` reported `19beta4 (Debian 19~beta4-1.pgdg12+1)` and:

```sql
SHOW shared_buffers;          -- 48GB
SHOW work_mem;                -- 1GB
SHOW maintenance_work_mem;    -- 8GB
SHOW fsync;                   -- on after the durable switch; currently off on the leftover fast-sync runs
SHOW wal_level;               -- replica after the durable switch; currently minimal
```

Open one baseline set and start a single OSM load. Every server should use the same one-point planet load: `osm2pgsql-1.11`, 5 clients, scale **75000**, one set. Siren was already on 75000. Twilight's first PG19 load (set 118, test 2593) started at scale 60000 because `params` was stale; that run was left alone. Results on siren stay on the PostgreSQL 17 cluster.

```bash
cd ~/pgbent
./newset "PG19 beta4"
nohup ./runset &
util/progress
tail -f results/siren/2974/results.txt
```

`util/progress` on this run showed the load writing `gis` on port 5437 and storing results with `psql -h localhost -U postgres -p 5433 -d results`. The test number was 2974. It also printed `ERROR: extension "pg_buffercache" already exists` because `wl/osm-import` creates that extension again after `util/newgis`; the load continued (node processing in `results.txt`).

`./latest_set` shows only the active set. Mid-run the test row is there and TPS is still blank. On this run that was set 71, `osm2pgsql-1.11`, scale 75000, version 19, test 2974, 5 clients, with empty `tps`, `avg_latency`, `90%<`, and `max_latency`. After the run finishes, a blank TPS means the run failed. That holds for any test, not only OSM.

Finished OSM loads are read in context from the results database. `reports/osm-speed.sql` returns three summaries: one row per test (hours and nodes/s), a phase breakdown (polygon, line, and point time, plus node, way, relation, and index rates), and the tuned settings (buffers, durability, checkpoint and WAL rates).

```bash
./latest_set
psql -p 5433 -d results -f reports/osm-speed.sql
```

Siren's first PG19 runs (tests 2974, 2975, 3009) finished in **4.17 / 4.13 / 4.03** hours under **fast-sync** (`fsync=off`, `wal_level=minimal`). PG18 set 70 (`New planet 2026-08-13`, 4.45–4.73 hours on the same 850GB planet) is the **durable** reference. Do not treat those gaps as a version comparison.

Aim for **at least three finished runs** on a given config before judging the result range. Siren and twilight were collecting that third (and following) fast-sync pass with `complete` armed so the loop exits after the current load. `conf/19` in git is already durable (`d33ba0a`); after those loads finish, pull, **copy** into `/etc/postgresql/19/main/conf.d` (do not symlink — systemd permissions reject that), confirm `SHOW fsync` / `SHOW wal_level`, and keep running in the **same** set — durable vs fast-sync rows are distinguished by `test_settings`, not by a new batch (see `pg-release-config`).

`pgbent_tune` was already installed on siren. Still unchecked from the prep list above: the `server` table row, `osm2pgsql --version`, and the planet / flat-nodes paths.

## Workloads

| Workload | How to run | `script` in submission |
|----------|------------|------------------------|
| OSM planet load | `wl/osm-import`, then `nohup util/repeat-gis &` | `osm2pgsql%` |
| pgbench SELECT grid | `wl/select-grid && ./runset` | `select` |
| pgbench init (build time) | Recorded automatically by `runset` before each scale when `NEWINIT=1` | `:-i%` |
| Single point | `./benchwarmer <clients>` | as configured |

`wl/osm-import` writes the standard `params` for this loop, including `RECOVERY=3600`. Run it, then edit those parameters if this host needs a change. `repeat-gis` does not invent that file. `wl/osm-import` also calls `./newset "OSM"`; if this host is already on the right batch (e.g. `PG19 beta4`), run `./newset` again only when that batch boundary is wrong — not for each GUC tweak.

OSM loop control:

```bash
watch util/progress   # live dashboard: disk use, DB/WAL size, tail of current results.txt and nohup.out
touch complete        # (in STATEDIR) stop after the current run finishes
```

`watch util/progress` follows `repeat-gis` through its transitions: newgis, recovery sleep, and the next `runset`. It always shows the latest set's newest test, so one dashboard can stay open for the whole loop. This was verified on siren. On macOS, `watch` comes from Homebrew (`brew install watch`).

- A planet load takes roughly 3–5 hours on desktop hardware. `RECOVERY=3600` gives an hour of cooldown between runs.
- `util/newgis` recreates `gis` with extensions and runs `pgbent_tune`. If it fails, `repeat-gis` stops and removes the pid files. A failed `dropdb` means connections are still open, so investigate that before starting again. Don't force it.
- After each `runset`, `repeat-gis` reads the latest test's `tps`. A blank or zero TPS means the run failed, often because the disk filled, and the loop stops instead of starting another load.
- Configured `max_wal_size` is 100GB. That plus the planet database barely fits a 2TB drive, so a 2TB host has to move the previous major's cluster off that disk first. 256GB `max_wal_size` will not fit on 2TB. A 4TB host does not need that disk shuffle.
- A crashed run can leave orphaned OS stats collectors (`timed-os-stats`, iostat, vmstat). Check `ps` before restarting.

## Validate each finished run

```sql
SELECT t.server, t.test, s.set, s.info, t.script, t.server_version, t.end_time - t.start_time AS elapsed
FROM tests t JOIN testset s ON s.server = t.server AND s.set = t.set
WHERE t.server = '<host>' ORDER BY t.test DESC LIMIT 5;
```

```
- [ ] ./latest_set shows a TPS once the run has finished. Blank TPS after the run ends means it failed
- [ ] Run is in the intended study set (info = study description)
- [ ] server_version shows PostgreSQL <N>.x
- [ ] test_settings shows the study variable at the intended value
- [ ] test_metrics_data rows exist (power rows too if SUDODATA=1)
- [ ] Run appears in submission; OSM studies need non-null max_write_mbps
- [ ] Spot-check graphs: python3 metview.py <server> <test>
```

## Ship results for assembly

On each benchmark machine, whenever it has new results:

```bash
./upload    # data-only pg_dump of the results DB + results/<server>/ → <server>-<timestamp>.tar.gz → rsync to $ARCHIVE:results/
```

On the assembly machine:

```bash
./download  # rsync all archives into archive/, import only those newer than the last download
```

For each new archive, `download` takes the server name from the filename up
to the first `-`. It runs `./wipe_server <server>`, unpacks into `results/`, and loads
`<server>/<server>-results.sql`. Consequences:

- **An upload is a full replacement** of that server's data centrally: tests, testset,
  settings, metrics, and the `server` row. Make corrections (testset `info`, `category`,
  the `server` row) **on the source machine**, then re-upload. Edits made only in the
  central DB are lost on that server's next import.
- **`SERVERNAME` must not contain `-`**, or the import wipes and loads under a truncated name.
- When one server has several new archives, every one is imported and the last one processed wins.
  Upload once per batch of work, or confirm the newest archive was loaded.
- `./submit` is separate. It exports a server's `submission` view as CSV for outside
  sharing and is not part of assembly.

## Recording findings

Regressions and crashes found during a study are a deliverable. PG18 testing
found an 18.0 `maintenance_work_mem` crash. When something breaks:

1. Reproduce it on a second run, ideally on a second machine.
2. Record the server, test number, version, and the study variable's value from `test_settings`.
3. A finding may itself open a new study. Flag it with its own `newset`.
4. Work around it in `conf/<N>` with the issue cited in the commit message (`pg-release-config`).
