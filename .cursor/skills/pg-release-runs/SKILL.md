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
- [ ] Write down the question and the one variable being changed (GUC, kernel setting, link speed, hardware)
- [ ] Choose a short slug and description convention, e.g. 'pg19 io_method=worker', 'pg19 io_method=io_uring'
- [ ] Choose the participating machines and the baseline config they share (conf/<N>)
- [ ] On each machine, per variant: apply the setting → ./newset '<description>' → run the workload
- [ ] Record the study (slug, description prefix, machines) wherever the user tracks open studies
```

Rules for running studies in parallel:

- **One study per machine at a time.** A machine's runs go to whichever set was
  flagged last, so call `newset` before switching topics. Never interleave two studies'
  runs under one set.
- **Change one variable per set.** Reset the previous study's setting before flagging the next one.
  `test_settings` captures every GUC per run, so stray settings will show up in the data.
- **Baseline runs can feed several studies.** PG18's leaderboard and power studies drew on the same
  default-config OSM loads. Experiments that move off the baseline get their own sets.
- **Ask before setting `category`** on another study's sets; it removes them from publishing.
  Set it on the source machine, because the central copy is replaced on every `download`.

## Server prep (once per server per cycle)

```
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

## Workloads

| Workload | How to run | `script` in submission |
|----------|------------|------------------------|
| OSM planet load | `wl/osm-import`, then `nohup util/repeat-gis &` | `osm2pgsql%` |
| pgbench SELECT grid | `wl/select-grid && ./runset` | `select` |
| pgbench init (build time) | Recorded automatically by `runset` before each scale when `NEWINIT=1` | `:-i%` |
| Single point | `./benchwarmer <clients>` | as configured |

`wl/osm-import` calls `./newset "OSM"` itself. For a study, run `./newset '<description>'`
**after** it so the runs land in the study's set. Alternatively, write `params` the way it does
and skip its `newset`.

OSM loop control:

```bash
util/progress     # disk use, DB/WAL size, tail of current results.txt and nohup.out
touch complete    # (in STATEDIR) stop after the current run finishes
```

- A planet load takes roughly 3–5 hours on desktop hardware. `RECOVERY=3600` gives an hour of cooldown between runs.
- `util/newgis` recreates `gis` with extensions and runs `pgbent_tune`. If `dropdb`
  fails, connections are still open, so stop and investigate. Don't force it.
- 256GB `max_wal_size` plus the planet DB will not fit on a 2TB drive.
- A crashed run can leave orphaned OS stats collectors (`timed-os-stats`, iostat, vmstat). Check `ps` before restarting.

## Validate each finished run

```sql
SELECT t.server, t.test, s.set, s.info, t.script, t.server_version, t.end_time - t.start_time AS elapsed
FROM tests t JOIN testset s ON s.server = t.server AND s.set = t.set
WHERE t.server = '<host>' ORDER BY t.test DESC LIMIT 5;
```

```
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
