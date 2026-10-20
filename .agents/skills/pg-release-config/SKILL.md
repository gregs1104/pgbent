---
name: pg-release-config
description: >-
  Prepare and evolve the per-release PostgreSQL configuration set
  (conf/<N>/conf.d) for a new pgbent release study such as PG19. Covers
  copying forward from the prior release, deploying to a server's conf.d,
  retuning during the cycle, and recording why each setting changed. Use when
  starting a new major-version test cycle or adjusting conf/<N> settings.
disable-model-invocation: true
---

# Release config prep (conf/<N>)

Each major release gets its own `conf/<N>/conf.d/` include directory, which is
deployed into the server's `conf.d`. Only the port number and locale stay in
`postgresql.conf`. Files ending in `.conf` are active and `.off` are inactive.
Switch a variant by renaming files, never by editing them in place.

| File | Holds |
|------|-------|
| `logging.conf` | Checkpoint/temp/statement logging, `pg_stat_statements` preload, `track_io_timing` |
| `network.conf` | `listen_addresses`, `max_connections`, parallel worker counts, comparability toggles |
| `osm-general.conf` | WAL size, checkpoints, bgwriter, autovacuum off |
| `osm-mem-{16,32,64,128}` | Memory tiers; exactly one is `.conf` |
| `osm-wal-replica` / `osm-wal-minimal` | WAL volume; exactly one is `.conf`. **PG19 default is replica** |
| `osm-fsync-on` / `osm-fsync-off` | Sync waits; exactly one is `.conf`. **PG19 default is on** |
| `osm-fpw-on` / `osm-fpw-off` | Full-page writes; exactly one is `.conf`. **PG19 default is on** |
| `README.md` | Deploy instructions |

## Start a cycle

```
- [ ] cp -r conf/<prev> conf/<N>  (PG19 was seeded from 18's final settings in ae49a78)
- [ ] Update version numbers in conf/<N>/conf.d/README.md examples (they still say 17)
- [ ] Check release notes for removed/renamed GUCs and new defaults; fix any .conf that would fail startup
- [ ] Note new GUCs that are candidate study topics (PG18 examples: io_method, data_checksums default on). Each becomes a study only when opened with newset (pg-release-runs)
- [ ] Revisit settings disabled "to match earlier tests" (network.conf: wal_compression, and `random_page_size`, which is a misspelling of `random_page_cost` and would block startup if uncommented as-is) — decide whether comparability with the prior release still outweighs testing them
- [ ] Deploy to a test server and confirm `SHOW` values match
```

Deploy, Debian/Ubuntu — **copy**, do not symlink:

```bash
cd /etc/postgresql/<N>/main/conf.d && sudo cp ~postgres/pgbent/conf/<N>/conf.d/* .
```

A symlink from `/etc/postgresql/<N>/main/conf.d` into the pgbent checkout
failed on systemd's permission setup; leave that approach alone. **Copy is
the isolation:** `git pull` never changes the running cluster. The cost is
noticing a conf change in the repo and copying by hand, then reload or
restart so the new files are read.

After deploying, verify no file was silently skipped:

```sql
SELECT sourcefile, name, setting FROM pg_settings
WHERE sourcefile LIKE '%conf.d%' ORDER BY sourcefile, name;
```

### Homebrew / macOS (no conf.d)

Homebrew PostgreSQL (`/opt/homebrew/var/postgresql@<N>/`) does not ship a
`conf.d` include directory. Fold the active settings from `conf/<N>/conf.d`
(`.conf` files only; skip `.off`) into that cluster's single `postgresql.conf`.
Keep port and locale as the host-specific bits; memory tier, durability,
logging, and OSM knobs should match the Linux baseline for the same release.
Verify with `SHOW shared_buffers;` / `SHOW fsync;` / `SHOW wal_level;` (and any
other study-critical GUCs) rather than `sourcefile LIKE '%conf.d%'`.

When the Homebrew cluster major changes, migrate the results database with the
upload-then-reload workflow in `pg-release-runs` before opening a new study set.

**PG19 rc1 catalog bump (2026-10-19).** A beta4 (or earlier 19) data directory
will not start on rc1. **Twilight’s** PG19 **test** instance must be recreated
from scratch — Greg leads because that datadir is **partitioned** on the Fury
volumes, not a stock PGDG path. Do not `pg_upgrade`, do not `initdb` into the
live path until he walks it. Keep the results instance; only the test cluster
is thrown away. **This is why results stay on a 1GB previous-major cluster** —
never in the beta. After a catalog bump the beta datadir can be unreadable.
**Abbey has not gotten PG19 yet.**

**Brew PG restarts are a struggle.** `brew services restart postgresql@<N>` often
claims success while the **old postmaster keeps running** (idle `gis` backends,
metrics collectors, etc. hold it open). After folding durability or memory
changes into `postgresql.conf`:

1. `SHOW` the GUCs — if `sourcefile`/`sourceline` still point at the old values,
   the restart did not take.
2. Terminate backends, then stop for real: `pg_ctl -D … stop -m fast` (and/or
   `brew services stop`), confirm no `postgres` left on that data directory.
3. When flipping `osm-wal-minimal` → replica, drop leftover `max_wal_senders = 0`
   from the folded block; `wal_level=replica` needs the default senders.
4. Start with a valid locale (`LC_ALL=en_US.UTF-8`) or via `brew services start`
   — bare `pg_ctl start` can die with `postmaster became multithreaded during
   startup` / “Set the LC_ALL environment variable”.
5. `SHOW fsync; SHOW wal_level;` again before starting the next OSM load.

Abbey PG18 fast→durable (2026-10-15) hit all of the above.

### Homebrew Python (`dateutil` / `pgsysinfo`)

pgbent needs the Python `dateutil` module (`import dateutil`); `./pgsysinfo` is the
smoke test. After a Homebrew Python upgrade the module is often gone (PEP 668
marks the brew interpreter as externally managed). The clean fix is a local
venv + `pip install python-dateutil` (or the `dateutils` meta-package). On a
Mac that only runs these benchmarks, the short path used on abbey is:

```bash
sudo pip3 install dateutils --break-system-packages
./pgsysinfo   # must print version / SETCLIENTS / SCALES / OSMNODECACHE again
```

(`--break-system-packages` is a trailing pip option; putting it before `install`
fails.) Re-run that after brew Python updates when `pgsysinfo` starts ImportErroring.

### Planned: abbey post-process Python crash (after PG18 numbers)

OSM loads on abbey often finish (`osm2pgsql took … overall`) but post-process
dies in Homebrew Python — empty `results.json`, null `tps` — recovered with
`util/repair-osm-result` (and `--metrics` when brew Python cooperates). Symptom
seen: `init_sys_streams` / `Bad file descriptor` during Darwin `metrics2csv` /
`csv2gnuplot`.

**After abbey’s PG18 durable/fast cells are collected**, dig in. Strongest
clue so far: it only hiccups **as part of the live run**; `repair-osm-result`
on the same files **always works**. That points at run-context state more
than a pure parse bug in the scripts.

Suspects, ordered by that clue:

1. **Collector-exit hangover** — post-process starts while `timed-os-stats` /
   iostat/vmstat children are still dying or holding FDs. Fits
   `init_sys_streams` / `Bad file descriptor` on Darwin: stdin/stdout/stderr
   or inherited pipes from the collector teardown, not bad CSV. Repair runs
   in a clean shell with collectors long gone — so it succeeds.

   Handoff today (`benchwarmer`): `kill_pg` SIGKILLs the collector process
   groups (no `wait`), then a pile of SQL/`art-import` work, then
   `metrics2csv` / `csv2gnuplot`. No explicit settle before Python.

   **Two digs when abbey 18 is done** (prefer instrument; sleep is fine as A/B):

   - **Sleep and hope** — cheap empirical test: `sleep 2` (or 5) right after
     the `kill_pg` block (~L382–398) and/or immediately before
     `metrics2csv` (~L616). If live runs stop crashing, hangover is confirmed
     even if the root cause is still fuzzy; leave the sleep (or replace with
     a real `wait`) until something cleaner lands.
   - **Instrument to catch it exactly** — before invoking `metrics2csv`, log:
     whether any `timed-os-stats` / iostat/vmstat PIDs remain (`pgrep`/`ps`);
     Darwin `lsof -p $$` (or python’s `os.fstat` on 0/1/2) for broken
     stdin/out/err; wrap the Python entry so `Bad file descriptor` /
     `init_sys_streams` dumps FD state + traceback to the test dir. That
     tells sleep-vs-wait-vs-FD-reset without guessing.

2. **Datetime / `dateutil` path backfiring** — `csv2gnuplot` uses
   `dateutil.parser.parse` then `time.mktime` on iostat/vmstat timestamps, plus
   a hard-coded gnuplot `set xtics 10` workaround for HH:MM:SS label overlap.
   Less favored while repair-always-works holds, unless live runs feed
   different/truncated stamps than the on-disk files repair reads.
3. **Homebrew Python itself** — brew’s interpreter has been fragile across
   upgrades (`dateutil` vanishing under PEP 668, odd FD/stdio failures). Try
   another Python source for the post-process shebang path: **python.org /
   framework build**, **MacPorts**, or a dedicated **venv** pinned for pgbent
   collectors — not “whatever `brew` `python3` is today.” Still worth trying
   if hangover fixes don’t stick; brew may just be more sensitive to bad FDs.

Web search so far turned up no similar complaints (`init_sys_streams` /
`Bad file descriptor` after Darwin collector teardown). That is weak
negative evidence: this path is niche (Homebrew Python + `setsid` collectors
+ `kill_pg` SIGKILL + immediate post-process), and Stack Overflow volume has
collapsed, so “nobody posted it” no longer means much. Treat as
instrument-locally, not “must be unique to our datetime hack.”

Stronger prior: this collector → `metrics2csv` / `csv2gnuplot` path is
**over a decade old** and was never a problem before. So favor “something
in the environment changed” (Homebrew Python / Darwin stdio sensitivity)
over a brand-new logic bug in the scripts themselves. Sleep, wait, FD
instrumentation, or a non-brew interpreter — one of those fixes should
clear it; the decade of quiet use is why we dig the handoff/runtime, not
rewrite the parsers first.

Until that lands, keep using `repair-osm-result` rather than blocking OSM
collection. Do not rewrite collectors mid-Monday bar; this is the follow-on
once abbey 18 numbers are done.

## Baseline vs study variants

`conf/<N>` is the shared baseline every machine runs. A study that varies a
setting changes it on the participating machines only. Use a `.conf`/`.off`
variant file or a temporary edit, reload, and keep the **same** testset —
reports expect multiple GUC combinations in one set. OSM reports
(`osm-speed.sql`) and the submission summary (`submission.sql`,
`write_internals.sql`) pull `shared_buffers`, checkpoint settings, and
durability into each row for that purpose. Do not open a new set for each
GUC flip (see `pg-release-runs`).
Promote a study's winning value into `conf/<N>` only with a commit that cites
the study.

## Retuning during the cycle

The config is expected to move as early .0/.1 releases expose bugs and new
features shift optimal settings. Rules:

- **One reason per commit.** Put the *why* in the commit message. The PG18 history is the model:
  - `Lower PG18 maint_work_mem due to 18.0 crash bug. Setting to max of 256MB until resolved.`
  - `Have PG18 use up to 8 maint workers.`
  - `Adjust final PG18 tuning numbers downward ... parallel GIN work in PG18 destabilized that peak.`
- **Workarounds are temporary.** When a setting is capped for a bug, say so in a
  comment in the `.conf` file. Revert it once a fixed minor release is under test.
- **Results must be attributable.** `benchwarmer` captures every run's
  `pg_settings` into `test_settings`, and the submission views break out the key
  GUCs (`csum`, `w_p_g`, `p_m_w`, `fsync`, `wal_level`, `max_wal_gb`). When a new
  GUC becomes a study variable, add it alongside those in
  `reports/write_internals.sql` (pattern: `test_settings.name='data_checksums') AS csum`)
  and in the submission view, so results can be filtered by it.
- **End of cycle:** the last `conf/<N>` state is the published "tuned" config,
  and it seeds `conf/<N+1>`.

## Memory tier selection

`osm-mem-*` assumes osm2pgsql runs **on the server**, so
`effective_cache_size` is lower than for a normal server. Pick the tier
at or below installed RAM:

```bash
mv osm-mem-128.conf osm-mem-128.off && mv osm-mem-64.off osm-mem-64.conf
```

On 128GB hosts, `osm-mem-128` (`shared_buffers=48GB`) plus a large osm2pgsql
node cache (scale / `OSMNODECACHE`, e.g. 75000 → ~60GB RSS) was a **PG17 local
maximum**. Parallel index / GIN work in PG18 undid that peak; the pack spills
into the default ~15GB swap, and the pain shows when the loader **drops the
node cache** for the index phase. A planned PG19 study (see `pg-release-runs`)
will compare shrinking the node cache versus dropping to a smaller `osm-mem-*`
tier once all four servers share the durable baseline. Do not retune those
numbers ad hoc before that study.

Checkpoint-related values (`max_wal_size`, `checkpoint_timeout`) follow the
tuning model in `docs/model/max_wal_size.md` and `docs/model/checkpoint_timeout.md`.
Larger WAL (256GB, 60 min) is faster but may not fit on 2TB drives. 100GB / 30 min is the default.

## Durability default (PG19)

The published baseline is **production durability**: `wal_level=replica`,
`fsync` / `synchronous_commit` on, `full_page_writes` on. Those are **three
independent pairs** in `conf/19/conf.d` (`osm-wal-*`, `osm-fsync-*`,
`osm-fpw-*`). Default files are the `.conf` side of each pair. Conf 16–18
keep the bundled `osm-sync-fast` / `osm-sync-durable` pair.

Abbey PG18 set 11 showed a **severe** bundled penalty (fast 7.45h / 404
kNodes/s vs durable 11.1h / 270). Some systems are WAL-volume driven; abbey
is suspected **Darwin fsync**. Further PG19 testing flips WAL level and fsync
separately (FPW held on unless WAL bytes still need explaining). A `git pull`
on siren is fine; do **not** copy into `/etc/postgresql/19/main/conf.d` (or
reload) until the current PG19 grid cells finish.

`SHOW fsync; SHOW wal_level; SHOW full_page_writes;` after each flip. Stay
on the existing PG19 set — corners are told apart by `test_settings`.

**First PG19 study** is durability / WAL volume vs throughput on the 100GB·30min
envelope: 2×2 (`osm-wal-*` × `osm-fsync-*`, FPW on) on PG19 only. See
`pg-release-runs`.
