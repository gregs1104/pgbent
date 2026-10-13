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
| `osm-sync-fast` / `osm-sync-durable` | Durability; exactly one is `.conf` |
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

Deploy, Debian/Ubuntu:

```bash
cd /etc/postgresql/<N>/main/conf.d && cp ~postgres/pgbent/conf/<N>/conf.d/* .
# or, dedicated benchmark host:
cd /etc/postgresql/<N>/main && rmdir conf.d && ln -s ~postgres/pgbent/conf/<N>/conf.d
```

After deploying, verify no file was silently skipped:

```sql
SELECT sourcefile, name, setting FROM pg_settings
WHERE sourcefile LIKE '%conf.d%' ORDER BY sourcefile, name;
```

## Baseline vs study variants

`conf/<N>` is the shared baseline every machine runs. A study that varies a
setting changes it on the participating machines only, for the sets flagged for
that study. Use a `.conf`/`.off` variant file or a temporary edit, and revert it before
the next `newset`. Promote a study's winning value into `conf/<N>` only with a
commit that cites the study.

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

Checkpoint-related values (`max_wal_size`, `checkpoint_timeout`) follow the
tuning model in `docs/model/max_wal_size.md` and `docs/model/checkpoint_timeout.md`.
Larger WAL (256GB, 60 min) is faster but may not fit on 2TB drives. 100GB / 30 min is the default.
