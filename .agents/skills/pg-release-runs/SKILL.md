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

**New-version tooling period.** Every major starts with a stretch of getting
the farm onto the new packages (conf.d, PGDG/Homebrew, OSM stack, collectors,
`newset` labels). That period is **already over for PG19**. **2026-10-20 —
19rc1 validated:** took the top leaderboard spots with a tiny delta over
18. The leaderboard is how this lab judges a release; it's easier than
tracking medians. Everything tested — three Linux platforms plus a Mac.
Siren OSM import finished; that closes the SELECT-then-OSM pair on the 9950X. **PG17** and **PG18** each
dragged for months because a real defect showed up (Ubuntu packaging bug in
17, GIS bug in 18). Community **19rc1 testing deadline is 2026-11-12**; this
lab is **weeks ahead**. SELECT leaderboard and the siren pgbench-SELECT
variation graph are follow-up, not more validation.

## Siren 9950X retirement (full data)

Retire **9950X + SK51** with a complete pack before the chip comes out.
Twilight already **leads relations/s** (4590 vs 4529); this OSM is the
9950X archive and a second rc1 pass, not a bid for the relations crown.
**2026-10-23 — 9950X testing closed.** Set **108** has durable **3265**
(4.49h / 668 overall / score 1176) and alternate **3266** (4.14h / 725 /
1454; `fsync` off / `wal_level=minimal` / FPW off) — in the beta4 fast
band. Next hands-on: **power down and swap to 9600X**. No agent SSH.
Court set 8 is done; **set 9 test 145** is the durable 19rc1 OSM +
`OSMRELPROF` retry (1h cap). Do not start a second Spark planet load
while 145 runs.

Hands-on on siren (no agent SSH):

1. Put **PG19 rc1** back on **SK51** if it is not already there (catalog
   **20261006**, `debug_assertions` off).
2. **Empty `;`** (`wl/empty-grid`, `SCRIPT=nothing`) on the existing
   scale-100 database (`SKIPINIT=1`). Same cell as SELECT: 90s,
   `SETTIMES=2`, clients `1 2 4 8 16 32 64`. **Sockets `;` and
   sockets simple `constant` are in** (set 107). `;` 1-client
   **281,019** / **280,201**; peak **4.05M** simple / **3.81M**
   prepared at 32 (re-run 3254 / 3251). 64-client prepared **3252**
   is 3.65M TPS, avg 7 μs, P90 0, max **1.45 s** — repeating stalls
   on the per-row plot, not a connect() artifact. That is why every
   `pgbench -l` row is copied. Sockets `constant` is in both faces:
   simple 1-client **179,635** (5.6 μs), peak **2.48M** at 32, 1.79M at 64;
   prepared 1-client **212,745** (4.7 μs), peak **2.96M** at 32, 2.24M at 64.
   Execute `SELECT 1` +1.1 μs, plan it +0.9 μs, lookup +2.9 μs.
   Then TCP faces if the box is staying up. Then OSM.
3. **OSM 19rc1** set **108**: durable **3265** 4.49h; alternate **3266**
   4.14h. That closes 9950X tests. Power down.
4. Swap to **9600X**.

## Comparing versions

Hold `conn_method` constant. An early mixed `latest_set` on siren put PG18
sockets next to 19beta4 host and looked ~25% down. That was a **test-method
error**, not debug assertions — `SHOW debug_assertions` was off on those
beta4 rows anyway. Not worth chasing; cover the whole connection grid once
the RC is ready. Always sweep the four faces (sockets vs host, simple vs
prepared): PG18 connection study, kept as a code exercise. Phoronix switched
to prepared years ago and reset public history; numbers went up, few noticed.
Public note: [Comparing versions](../../../docs/workloads/select.md).

Scale 100 SELECT is ~1.6GB in RAM; a disk swap between pins does not matter.

Siren 9950X, 90s, 32 clients, mean of two `SETTIMES`, same `conn_method`:

| pin | conn | TPS |
| --- | --- | ---: |
| 18.3 | sockets prepared | 2,013,812 |
| 19rc1 | sockets prepared | 2,058,653 |
| 19beta4 | host prepared | 1,500,701 |
| 19rc1 | host prepared | 1,517,063 |

19 took the ranking cell with a tiny delta over 18 and over 19beta4. Beta packages can still ship
`--enable-cassert` (wiki); that was not this drop.

SELECT also publishes **transactions per joule** per client count (same
1-second `PkgWatt` integral as OSM kJ). At the 200 W PPT rail every face
burns the same ~17.8 kJ in 90s; sockets prepared does about twice the
work of localhost TCP simple. Energy efficiency is the virtuous side of
the protocol fan.

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

**Method (since 8.2 vs 8.3).** Map a workload **grid**, run each cell **3–5 times**,
graph means with **error bars**. Original axes were scale × clients
(`SETTIMES` / `runset`). Anything capturable to a text file and imported can
be an axis or plotted metric — power normalized across hardware is the
template; durability GUCs, `shared_buffers`, and `maintenance_work_mem` are
discrete points on the same idea, split in reports via `test_settings`. A
study that stops at one run per corner is unfinished. **Last step:** write a
query that shows the study (see `pg-release-publish`). For PG19 that is SQL +
static getbent.io pages — not a hosted Streamlit app.

```
Study: <topic>
- [ ] Write down the question and the grid axes (GUC, node cache, scale, …)
- [ ] Plan repeats per cell (OSM: 3–5 via repeat-gis / complete; CPU-bound SELECT: `SETTIMES=2` unless the two diverge; noisier pgbench: `SETTIMES` 3+)
- [ ] Confirm the active set is still the right batch (same major version, same planet, same non-GUC context)
- [ ] Choose the participating machines and the shared conf/<N> baseline
- [ ] On each machine: apply the setting → reload/restart → run the workload (same set)
- [ ] Reports split variants via test_settings (fsync, wal_level, shared_buffers, …), not via a new set
```

### When to call `newset`

A set is a **batch of related work**, not one config. Trying a new set for every
GUC change was a mess; the PG18 history is full of sets that mix parameter
combinations on purpose.

That mix is intentional and supported by the reports. `reports/osm-speed.sql`,
the OSM submission helpers (`reports/submission.sql`, `submission-best-osm.sql`,
`write_internals.sql`), and the published study SQL pull common GUCs into each
row — `shared_buffers` / `shared_gb`, `maintenance_work_mem`, `max_wal_size`,
`checkpoint_timeout`, `fsync`, `wal_level`, checksums, parallel-maintenance
workers — so variants in one set stay distinguishable without a new batch.

Call `./newset` when you need a **named batch**, for example:

- A new PostgreSQL major (or a named beta/RC campaign worth separating)
- A new raw planet dump / OSM data vintage
- A different workload script family, client topology, or hardware role that should not mix with the current batch
- **Opening a study** that should stand alone later — same description prefix on every
  participating machine so assembly can select it. PG18's published sections
  (checkpoint, dirty memory, network, …) started as sets flagged this way, then
  became study SQL and results pages. Use a clear `testset.info` while the topic
  is live; GUC variants *inside* that study stay in the same set.

Do **not** open a new set just to flip `osm-wal-*`, `osm-fsync-*`, `osm-fpw-*`,
`osm-mem-*`, `maintenance_work_mem`, or other GUCs on the baseline. Change the
files, reload, keep running under the same `testset.info`.

### Backfill into an earlier set (temporary set, then reassign)

When adding runs that belong with an **older** published/comparison set (e.g.
siren PG18 minimum-durability bridge into the set-70-era durable envelope) while
you are already mid-stream on a later set:

1. **`./newset '… temporary backfill …'`** — park the current work; new runs land
   in this scratch batch.
2. **Run and confirm** the backfill cells look accurate (hours, rates, GUCs in
   `test_settings`, WAL volume, etc.).
3. **Move the tests** into the target earlier set (no FK from `tests.set` →
   `testset`; still do it carefully on that server only):

```sql
-- example: temp set 72 → historical set 70 on siren
BEGIN;
UPDATE tests SET set = 70 WHERE server = 'siren' AND set = 72;
DELETE FROM testset WHERE server = 'siren' AND set = 72;
COMMIT;
```

4. **`./newset '…'` again** for the batch you were already using (or the next
   study), and keep adding there. The temporary `testset` row is gone; the
   reassigned `tests` rows now report with the earlier set’s `info` / batch.

Do **not** leave the temporary set around once the move is confirmed — assembly
and study SQL key off `batch` / `batch_id`, and a leftover empty or half-moved
set confuses both. Confirm row counts before/after the `UPDATE`. This is a
**Greg-operated** results-DB edit on the source machine (then `./upload`); agents
do not invent set-number surgery unless asked.

**PG18 minimum-durability backfill on siren:** stopped 2026-10-16 (Ways
deaths). The temporary-set → reassign path remains the way to land a later
bridge cell into an older comparison set.

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
      **Ship `wl/` and `tests/` via the public repo, then pull.** Copying a
      script onto the box is the exception (court set 8: checkout at
      `8fc7fec` with dirty OSM `params`, `component-faces` not on origin
      yet). Do not make scp the default.
- [ ] Install PostgreSQL <N> (plus PostGIS, hstore for OSM) and deploy conf/<N>/conf.d
- [ ] Edit ./config: TESTHOST/TESTPORT/TESTDB, RESULTHOST/RESULTDB, SERVERNAME, DISKLIST, ARCHIVE
- [ ] **Linux `DISKLIST`** — set to the database disk device name(s) as they appear in
      `iostat` / `lsblk` (no `/dev/` prefix). Default in `config` is `DISKLIST="sda"`.
      NVMe hosts need something like `DISKLIST="nvme0n1"`. Wrong or stale values mean
      `metrics2csv` / `csv2gnuplot` produce no `iostat.csv`, so disk metrics never land
      in `test_metrics_data` (seen on court until corrected). Darwin ignores this.
- [ ] Install sudo helpers in /usr/local/bin with NOPASSWD rules (see each script header):
      util/pgbent_tune (governor=performance, readahead 4096, fstrim)
      util/pgbent_powermon (power sampling; set SUDODATA=1 in config)
      util/pgbent_perf (perf record/report for OSMRELPROF=1 relation profiling)
- [ ] Update the `server` table row (cpu/mem/disk/OS) if hardware changed — submission reports the human-readable disk from it
- [ ] Confirm osm2pgsql version: `osm2pgsql --version`; set SCRIPT to match — but see **OSM stack freeze** below before upgrading packages
- [ ] Planet + flat nodes paths: PLANET_FILE / NODES_FILE (defaults ~/osm/planet-latest.osm.pbf, nodes.db)
```

`SERVERNAME` defaults to the hostname. It is part of every study key, so keep it stable for the whole cycle.
It must not contain `-`, because `download` parses the server name from the archive filename.

If a setup mistake (wrong `DISKLIST`, missing power import path, etc.) is fixed after runs
already finished, re-import from the on-disk logs without re-running the workload:

```bash
./metrics2csv recurse   # from the pgbent checkout; walks results/<server>/<test>/
```

That regenerates CSVs (including `iostat.csv` once `DISKLIST` matches) and reloads
`test_metrics_data` for every result directory. Safe only when no test is actively
writing those directories.

### Repair a finished OSM run with missing artifacts / TPS

When the load completed (`results.txt` has `osm2pgsql took … overall`) but
post-process died (Homebrew Python `init_sys_streams` / `Bad file descriptor`
during Darwin `metrics2csv`, empty `results.json`, null `tps`), rebuild without
re-running osm2pgsql:

```bash
# from the pgbent checkout on that server
util/repair-osm-result <test> <server>           # artifacts + TPS only
util/repair-osm-result <test> <server> --metrics # also re-run metrics2csv
```

`repair-osm-result` parses `results/<server>/<test>/results.txt`, writes
`results.json`, and fills **that** `tests` row. `util/art-import.sql` is
write-once (exact `server`/`test`, never `{}`, never replace a populated
cell) so repair is the path that can fill `{}` after a finished load.
Then sets OSM TPS to kNodes/s. Add `--metrics` once the Python/`DISKLIST`
issues are fixed.

A hard power-off of the DUT also takes the **results cluster** (siren: PG17
`:5433` on the same box). The old post-process used `max(test)` plus
`art-import` on **latest start_time**, and a failed OSM parse is `{}`.
That stamped `end_time=now()` **and replaced artifacts with `{}`** on the
last good cell — siren **3047** (set 72) was not uploaded yet, so it is
gone; **3083** was the later incomplete start. This is why durable became
the default (fewer trips) and why upload archives exist. `benchwarmer`
now `INSERT … RETURNING test`, will not close an incomplete OSM row, and
will not import `{}`. Salvage: `grep overall results/<server>/<test>/results.txt`
then `util/repair-osm-result` if the summary line survived.

Not repairable: incomplete loads (no overall line, `nodes.db` still present,
tiny `dbsize`) — delete those test rows/dirs instead. Abbey set 11 test **64**
was recovered this way (404 kNodes/s); test **66** was still mid-load.

**Who runs studies.** Greg defines the matrix and points an agent at a host; he does
not babysit the loads himself. Commit conf / skill / report changes in the repo
first; the agent then pulls and executes on the target machine. Do not invent
host-only steps that are not yet in the repo.

**Why the metrics kit is painful on purpose.** New-release weeks always look like
this lab: broken post-process, zombie collectors, TRIM waits, mid-load failures.
Second-by-second first-party metrics (`iostat` / `vmstat` / `timed-os-stats` /
`metric-query.sql` DB size, …) into `test_metrics_data` are how you see *what*
happened (e.g. twilight 2599’s ~220GB `pg_db_size` cliff when `planet_osm_line`
was rewritten). Delegating that layer to other tools historically lost
granularity and trust. Keep the simple collectors; fix their edges — do not
replace them with an opaque stack mid-cycle. See `AGENTS.md` § Architecture.

The schema was never meant to be this large. Each year some study needs extra
metadata, so another column or metric lands. The 19rc1 SELECT power table is
the method: every face rounded to **200 / 200 W** looked copied; the 1-second
`PkgWatt` files showed 1-client ~62 W and 16+ clients pegged at **199.6**
(PPT rail). A monitoring-system average would have erased that check. Combined
with per-second averaging hiding cliffs, this lab is stuck with the collector
work on purpose.

### OSM stack freeze (hold regression points)

Do **not** casually upgrade osm2pgsql / PostGIS / related loader packages mid
cycle just because a newer build is available. Greg intentionally runs an older
pinned OSM stack so throughput stays comparable across majors and hosts; the
loader is part of the regression baseline, not “always latest.”

Cadence: refresh the whole stack about **every two years**, aligned with the
major **Debian/Ubuntu** schedule — and **this is that year** (2026 / PG19).
Until a few clean PG19 collections are in on the current pins, leave
`osm2pgsql` where it is (Linux fleet currently **1.11**; abbey may differ on
Homebrew — do not “fix” the others up to match without an explicit cutover).
After that data is in, upgrade to the new stack as its own deliberate step
(newset / note in study text), not as drive-by `apt upgrade` during a matrix.

**Where to explore.** Use **twilight** for PG19 study matrices (durability 2×2,
checksums on/off, `shared_buffers` / node-cache sweeps, `maintenance_work_mem`).
It is not the fastest box, but it has more RAM and disk than the alternatives,
so it tolerates WAL volume, swap pressure, and leftover clusters. **siren** and
**abbey** run out of memory or disk regularly — keep them on known-safe configs
and short backfills, not on “mess around” corners. Siren remains useful for
process notes and tight comparisons once a winner is known; it is a poor place
to discover that a corner needs 1.5TB of WAL.

**Lab CPU / thermal stability (roles flipped).** Treat hard power-off under OSM
load as a **hardware** failure class, not a Postgres bug. Greg does not run the
lab at full capacity over the summer for this reason. The post-PG18 plan was
to retire this lab and move the workload onto approved **datacenter** iron;
that did not happen. The farm is **Greg-owned** hardware now — do not assume a
DC cutover, a company disk refresh, or that siren’s 2TB / 240mm limits are
temporary corporate inventory. Finish the OSM/PG19 cells on these boxes.

| Host | CPU | Notes |
|------|-----|--------|
| **siren** | **9950X** (was **9600X**) | **2026-10-18 — OSM probe finished in 4.07h** (clean hold through Ways; replacement for the wiped cell). **2026-10-18 — 32 clients is the max**: **2,011,141** then **2,016,484 TPS** (PG18, sockets SELECT, 90s). The two sets agree; halt after the second — CPU-bound SELECT is this tight, so **`SETTIMES=2`** is the default and a third only if they diverge. The missing rear vent had been capping this chip; ~2M is the 9950X unlocked. `newset` **`pgbench SELECT`** on **PG18**: **on-box UNIX vs localhost TCP** (overhead only; split on `conn_method`). Set **106** sockets prepared: PG18 **2,011,141** / **2,016,484** at 32 clients. Early 19beta4 **1.50M** cells in that `latest_set` were **host prepared** (method error, not asserts). **19rc1** covered the whole connection grid; sockets prepared **2.06M**. **2026-10-20 — 19rc1 SELECT+OSM done on the 9950X** (took the top leaderboard spots, tiny delta over 18; OSM import finished). Siren SELECT set is the **starter pgbench leaderboard**. **Retirement pack before 9600X:** empty `;` + `constant` + nothing 32/64 re-run (latency + watts, both configs) + one 4h OSM with `OSMRELPROF=1` (also re-tests rc1). Twilight already leads relations/s. Usual 18↔19 regression pair is **pgbench SELECT (small scale) + OSM (writes)**. True remote TCP at **128 clients** waits on the **new 2S**. `PREPARED=1` in params, `SUDODATA=1` already in `config`. Rear ST120 works **hard by the end of each 90s** and **harder during latency import** (`pgbench -l` at this TPS is a second heat spike). Thermal fix first was the right order. Rear **Lian Li ST120** exhaust is in; AIO pair also ST120s, **AIO cleaned of heavy dust**. Earlier heat had the new exhaust **maxed** (~**75°C**); it **chugged through Ways** (the old death phase) and in **Relation** the fan is at **medium** with **~60°C**. Chassis looks thermally fixed. **No agent SSH** — when a box is this fragile, Greg has to be hands-on to fix it; remote poking is how it gets worse. Data via `download`. **9950X SELECT** sockets grid is in (`wl/select-grid`, halt after two sets); then **9600X** for the OSM comparison SKU. The comparison / joules charts are done as graphics; they still have a **hole between high-power x86** (9950X **1046 kJ**, 13600K **824 kJ**) **and low-power ARM** (Apple **224 kJ**, NVIDIA **671 kJ**). **9600X** is that middle point — even better than the 9700X that was in the plan. OSM barely moved **9600X→9950X**. **2026-10-18 — Greg is looking for the 9600X** (the physical chip). PG19 sets 70/71 are enough for 18↔19. The **9600X** is the comparison SKU this box should publish: OSM barely used the 9950X’s second CCD (`Tccd2` ~43°C while Tctl/Tccd1 sat in the 80s), so the 16-core swap did not buy planet-load speed, only package watts (9950X **70 W** avg / **180 W** peak / **1046 kJ** vs Apple **8 W** / **37 W** / **224 kJ**). A 6-core **9600X** at nearly the same OSM score (~**47 W** avg / **89 W** peak on this board) is the bang-for-buck point on the system-comparison chart and a fairer fight against the Mac. **9950X** is still the short-pgbench / ~1M TPS chip; the 240mm AIO plus a missing rear fan could not hold OSM. Overhaul order: **1. rear airflow** done (Lian Li ST120 exhaust 2026-10-18, AIO ST120s cleaned). **1b. OSM probe** done: **4.07h**, held through Ways. Chassis is usable. **2. 19rc1 SELECT+OSM** done on the 9950X (2026-10-20). **3. retirement pack** (empty `;` + `constant` + nothing 32/64 re-run + 4h OSM with `OSMRELPROF=1`). **4. switch to 9600X** for the OSM / system-comparison SKU. Do not keep the 9950X here hoping AC will hold Ways. **2026-10-16 evening — parked.** Died in **Ways** again. Do **not** retry PG18 low-durability / thin-WAL on this chassis; that corner is what trips the board, and those cells get re-run after the WAL vs fsync split anyway. Downloaded set **70** (PG18.3 durable) vs set **71** (PG19 fast 2974/2975/3009/3010 and durable 3011–3013) is enough for the 18↔19 regression; twilight 117 vs 118 and abbey 11 fill the rest of the fleet. Rear case fan was the first fix (installed 2026-10-18); the 2026-10-16 Ways deaths were hot air staying in a chassis with none. Cooler is a **240mm AIO** (undersized for 9950X; 9600X was stable). **9600X→9950X barely moved OSM**, as expected (second CCD idle); the buy was for **short pgbench / ~1M TPS** (perceptually important). OSM *might* improve on a 9950X **after a larger heatsink**, not in this chassis. Workaround is the **room AC**, same as keeping the lab alive at **100°F** outside — not a CPU swap mid-grid. `wl/osm-import` `RECOVERY=3600` is an **informed** hour between planet loads (AIO/room heat dump); Greg expected another crash and wanted **`k10temp` live**. 2026-10-15 hard off; 2026-10-16 way ingest (`Node(10791148k …) Way(1133809k …) Relation(0)`); same-day restart still heat-soaked, `sensors` **Tctl 79°C / Tccd1 78.5 / Tccd2 42.6**, died in **Node** phase. Later the same day, cooled+AC **cleared Nodes at peak Tctl 87°C**; Ways sat ~**77°C** for a while with intake ~**68°F** (room normally **71°F**), then **still died in Ways** — 3°F of AC was not enough for the rest of that pass. Delete incomplete tests; thermal **starts as the host vanishing**. After the beta cells: rear fan (done), OSM probe (**4.07h**, done), then 9950X SELECT cells, then 9600X. Confirmed chip **`k10temp-pci-00c3`**: collect `sensors -u k10temp-*` (no sudo) → `Tctl_temp1_input` (package, vis 9) plus `Tccd1`/`Tccd2` (split, vis 5) — **do not average the CCDs**. The split is the teaching sample: **Tccd2 stayed ~43°C while Tccd1/Tctl sat in the 80s** — the second CCD is not on the OSM critical path, so extra cores on that die do not help a struggling load (and dump all the watts onto one hot chiplet). Live samples work; shutdown looks like the **motherboard cutting power near 90°C Tctl**, before the 9950X hits Tjmax throttle. Hands-on only — do not SSH. |
| **twilight** | **13600K** (was **14900K**) | **188GB** RAM, **Fury G5 4TB**. Roles used to be reversed: the **14900K** made twilight the unstable box. Back on a cool-running **13600K** it is trouble-free again — preferred host for long PG19 matrices. **2026-10-22 — up, no expected downtime.** Unused majors **14/15/17/18** `start.conf` **manual** (they all come up `auto` each boot; stop them). Results **16:5432** stays. **19rc1** test cluster recreated on the Fury symlink (`/var/lib/postgresql/19/main` → `/fury1/19/main`, catalog **202610061**). Set **119** `PG19 rc1`: sockets prepared SELECT **done** (2610 init, 2611–2624; 64-client **838k** / **757k**). **2026-10-22 11:06 ET — boot `/` hit 100%** during 2624 post-process: leftover **PG15** logs (179G + stuck `logrotate` copying 128G onto `postgresql-15-main.log.1`). 15 is down and its datadir is gone. Killed logrotate 1056, truncated both files as postgres (`/` back to ~34% / 296G). Empty `params` made face 2 fly through 0-TPS host cells; wiped 2625–2662 junk; **do not wipe 2610–2624**. 2622–2624 have TPS but no latency import. Remaining three faces resumed 11:11 (`remaining-faces.sh`). **Four faces done 13:22** (14 ok cells each face, 0 blank TPS). **OSM started 13:35** `repeat-gis` on set **119** (durable; do not `wl/osm-import`). TRIM was short on the fresh cluster (`/fury1` 4.5 GiB); first loop skipped the 3600s recovery. Test **2706** `osm2pgsql-1.11` / 5 clients / scale 75000. Nodes done 13:48 (10791148k @ 14.6M/s). **Ways healthy 14:01** (~99M @ 126k/s); live iostat writes on **nvme0n1** `/fury1` (~90 MB/s), not boot **nvme3n1**; planet reads **nvme2n1**; nodes.db on **nvme1n1**. gis 104 GB, WAL 33 GB. Pins: 19rc1 catalog **202610061**, fsync on / `wal_level=replica`, 48GB buffers. Do not `touch complete` yet (first load). `pgbent_perf` still not installed — no `OSMRELPROF`. See **Twilight boot + Fury 19 recreate**. Abbey has not gotten PG19 yet. |

Other machines:

- **abbey** — Mac Studio on Homebrew. **No PG19 during RC** — brew lags
  PGDG; every major still gets a brew pass **after** release bottles
  (PostGIS linked). Court is the ARM OSM cell. Abbey RC work is four-face
  SELECT + `nothing` / `constant` on **PG18** plus the OSM WAL vs fsync
  2×2. PG17 planet sets 8–10 done. **2026-10-16 — PG18 set 11 bundled
  cells:** fast 64/66 (7.43h/404, 7.49h/400) and durable 67/68
  (11.17h/268, 11.10h/270). Uploaded **2026-10-16**. **2026-10-22 — OSM
  2×2 unparked** on the same set: `wal_level` and `fsync` as separate
  controls, FPW on. First corner **replica + fsync off**. Do not
  `wl/osm-import` (it `newset "OSM"`). No `conf.d`; fold `conf/18/conf.d`
  into `postgresql.conf`. Capacity-constrained; not the exploration host. **Collector Python:** `./util/setup-python` → `.venv`
  (official CPython 3.12, not brew `python3` 3.15). PATH:
  `$HOME/repos/pgbent/.venv/bin` **before** brew python, **after** brew
  `shellenv` so `psql`/`pgbench` stay 18.6. Always `bash -lc`. After reboot
  wait out Spotlight/`mds*` and the end-of-recovery checkpoint before
  SELECT. `wl/select-faces` is copied; params still OSM until that driver
  rewrites them.
- **court** — NVIDIA DGX Spark (ARM64). As of 2026-10-14: **DGX OS 7.6.0 /
  Ubuntu 24.04.5**, kernel **`7.0.0-1019-nvidia`**. Spbm power works (test 13+);
  `DISKLIST="nvme0n1"` or `iostat.csv` is empty. **PG18 set 4:** fast 16/17
  (7.81h/384, 7.74h/387) then durable 18 (8.68h/346) — about **+12% / −10%**
  vs abbey’s bundled **+49% / −33%**. **PG19 rc1 set 5** has enough to start
  with: durable **20/21/22** (8.73h/343, 8.78h/342, 8.50h/353) and fast **23**
  (8.30h/361, `fsync` off). **2026-10-19 — halted:** `stop-set cleanup` wiped
  unfinished **24**; `shutdown -h now`. SSH closed. Came back **2026-10-20**.
  OSM stayed parked through set 8 SELECT. **OSM Power** stays public with the
  PG16 Spark row; the other boxes already have concurrent GIS on 19, so
  that mix is not a fair board. Do not share that study as finished until
  a **PG19** cell on kernel **7.0** is in the table (after set 8). **2026-10-21 — set 6 aborted because
  the box rebooted**, not because a sort failed. Tests 26–32 were one
  sockets-prepared pass; 64-client `COPY` of 55M `timing` rows was still
  wrapping (`timing.csv` 2.5G at 23:54) when watchdog ping to
  `192.168.50.1` failed and it **shut down at 00:07** (`Network is
  unreachable`). Disk-full is the known ingest failure mode (siren 31GB);
  court still has ~2T free. **Retest:** `wl/select-faces` (logs rc,
  continues). Skip 20-bucket / per-row gnuplot above 10M rows is
  optional time, not the court bug. New set, `SKIPINIT=1`. **Watchdog
  off:** Debian `watchdog` was leftover from a resolved power-management
  hang. Disabled the service and set `run_watchdog=0` /
  `run_wd_keepalive=0`. Kernel `[watchdogd]` left alone. **Do not use
  ping-to-gateway as a reboot trigger on this LAN.** The 10Gb segment
  (`192.168.50.0/24`, court `enP7s7` at 10Gb) is not fully reliable.
  Suspected path: **ARP handoff between the Mikrotik 10G switch and
  the Asus consumer routers upstream of it**. Default **MAC aging
  5 min** can drop court’s idle port mapping; next Mikrotik visit
  raise Bridge Host Table Aging / MAC Aging Time to **2h+**. Same
  signature as **~2s ping** until the ARP entry reappears; the
  watchdog reboot was the miss that stayed `Network is unreachable`.
  Do not configure the Mikrotik or Asus gear from here. A failed
  ping to `192.168.50.1` is a LAN glitch, not a hung host. Treat SSH
  drops the same way — retry, do not reboot. **Set 7 four faces
  done** 2026-10-21 22:09 UTC (`four faces done`, tests 33–88, all
  four `conn_method`s × 14).   No OSM after. **Set 8 done** 2026-10-22 20:21 UTC
  (`component faces done`, tests 89–144, sockets nothing+constant
  × prepared/simple × 14, 0 blank). 1-client means: `;` **100,843**
  simple / **94,911** prepared; `SELECT 1` **70,185** simple /
  **83,630** prepared. Wiped aborted set-6 **32** (5.9G `pgbench -l`
  leftovers) and init **25**. **2026-10-22 20:58 UTC — OSM unparked:**
  set **9** `PG19 rc1 OSM durable OSMRELPROF`, test **145**, durable
  (`fsync` on / `wal_level=replica` / FPW on), `OSMRELPROF=1` with
  **1h cap** (`OSMRELPROF_MAX_SEC=3600`). `complete` armed so this is
  one cell. PG18 stopped (`start.conf` **manual**); 16/19 stay up.
  Prior profiles failed: 20/21 leftover `perf` (deleted 121G+56G);
  22/23 hit the 8GB cap and are unreadable. Do not start a second
  court OSM while 145 runs. Unreliable about booting; force-restart
  procedure not written down yet.
- **rising** — **5950X** now (was **3950X** in the 2022 `SELECT 1` /
  `;` notes). Large pgbench + OSM archive on the box. **2026-10-22 —
  will not start.** SSD may have lost state after a long power-down,
  or it needs a BIOS fix; Greg has not sorted which. Do not mix 2022
  rising TPS into the siren 19rc1 table. Not the 9600X joules-hole
  SKU. Do not start, probe the disk, or flash BIOS from here. CBC
  already published a 5950X / 128GB / Inland 2TB point.

## Near-term deadline (lab downtime)

**By Monday (solar power upgrade — lab goes down):**

1. **Basic PG19 verification** finished — enough clean durable (and planned
   alternate) OSM loads to trust the major, not the full GUC matrix yet.
2. **Court Spark: at least one PG19 OSM run** — basic functional integration
   on a platform few people can touch. One clean load is enough to say it
   was tested there before the lab goes down; full profile/matrix later.
   Fit it after the in-flight PG18 durable cell if the clock allows (~8h
   class on court); do not starve item 3 for a second repeat.
3. **PG18 CPU vs power study at publication quality** — refresh/complete
   `osm-power` (and relation-power as needed) with current fleet points
   (including court Spark / abbey M-series / twilight·siren AMD·Intel as data
   allows); graphs + getbent.io page worthy of citing. Prefer data already
   collecting on the four boxes. Agent SSH: **abbey, court, twilight**.
   **siren** is Greg-only: a fragile thermal/disk box stays **hands-on**;
   do not SSH or change it. Still in the review loop via data Greg pulls
   over (`download` / results DB) — pair-programming split across the farm,
   not a blind spot. The 2TB squeeze is why it is easy to make worse remotely.
   Normally this is “buy a larger disk”; as of late 2025 fast 4TB pricing and
   availability make limping cheaper. Lab expansion was **July 2025** on purpose:
   early price rise read as the start of a swing boom (not luck) — do not
   “fix” the squeeze by retuning WAL upward.

Do **not** start the big twilight GUC exploration (durability 2×2 corners,
checksums, buffers, …) until Fury TRIM is understood and this Monday bar is
met. After the outage, resume the PG19 study sequence below.

**2026-10-16 — twilight parked (set 118 done).** Set 118 (`PG19 beta4`) is in
the assembly DB (`twilight-20261016-163051.tar.gz`): fast 2593–2595
(~4.8h / 623–628) and durable 2596, 2597, 2600, 2601 (~5.05h / 586–597),
about **+6%**. Box was powered down 2026-10-18; **back 2026-10-22** on 19rc1
(set 119). Four-face SELECT done 13:22 after the PG15-log disk-full (see
twilight host note). OSM `repeat-gis` started 13:35, same set; test **2706** **Ways healthy 14:01** (Fury `nvme0n1` writes confirmed).

**Siren retirement `OSMRELPROF` is the 9950X archive**, not the x86 peer
slot. Twilight still **leads relations/s** and remains the later control.

**After set 119 SELECT + usual OSM:** 128GB + `OSMRELPROF` vs court. The
comparison chart’s x86 peer for court’s relation `perf` is twilight:
**i5-13600K** is reliable, almost matches 9950X score (1407 vs 1480), and
**leads relations/s** (4590 vs 4529) at less package energy. Court’s Spark
reports **~121Gi**; twilight’s extra **188GB** would gift the node-cache /
OS-cache packing. Equalize with a Linux **`mem=128G`** kernel cap (GRUB) so
`MemTotal`, dirty ratios, and `pgsysinfo` / `server.mem_gb` all look like
the 128GB class — keep `osm-mem-128` as the Postgres tier. Then a **few
durable 19rc1** planet loads with `OSMRELPROF=1` (same path as court:
`pgbent_perf`, artifacts in the test dir). Not the big GUC matrix; TRIM
still taxes each `newgis`.

**Before `OSMRELPROF=1` on twilight (reinstall on court too):** use the
`pgbent_perf` that waits up to **10 minutes** for a flush after SIGINT
(`PGBENT_PERF_FLUSH_SEC`, default 600). Court 22/23/145 still got `data
size field is 0` because stop SIGKILLed after 15–20s mid-flush on an ~8GB
sample. Earlier 20/21 never died at all (SIGINT hit sudo only). Copy
`util/pgbent_perf` to `/usr/local/bin/pgbent_perf` (NOPASSWD already),
`git pull` so `osm-rel-prof` matches, then profile. Confirm no leftover
`perf record` after the first relation phase. Do not reuse court’s hung
captures.

**19rc1 OSM on court:** set 5 durable 20/21/22 plus fast 23 is enough to
start the report. Set **9** test **145** finished (8.32h); relation
`perf` hit the 1h cap but the report is unreadable (`data size 0`).
**2026-10-23 — set 10** test **146** is the durable + `OSMRELPROF` retry
with the flush-wait `pgbent_perf` installed (`complete` armed). Community
rc1 testing deadline is **2026-11-12**; this lab should be weeks ahead.

Fleet notes (update as needed):

- **Do not** use `pgrep -f` patterns that appear in the waiter’s own
  `bash -c '...'` string — twilight’s Oct 15 `wait-then-repeat` matched
  itself forever and never started `repeat-gis` after 2600 finished.
- Starting `repeat-gis` under a live OSM load would `newgis` mid-import; only
  attach a loop when idle, or wait on PIDs that cannot match the waiter.

## PG19 study sequence

Ordered topics for this cycle. Finish (or park with enough data to publish)
before opening the next; do not fan out a second matrix on PG18.

1. **Durability and WAL volume vs throughput** (open now — first PG19 study)
2. **Checksum overhead** (`data_checksums` on vs off) — deferred from PG18
3. **Node cache vs `shared_buffers`** (after durable baselines match across hosts)
4. **`maintenance_work_mem` sweep** (after memory packing is settled)

## After 19rc1 wrap: OS upgrades (siren, twilight)

Do **not** start this until the 19rc1 results and experiments have wrapped
(siren dump, twilight set 119 SELECT+OSM, abbey WAL/fsync 2×2, court set 8,
OSM Power Spark cell as needed). Then:

1. Upgrade **siren** and **twilight** to the new OS releases (Greg names
   the targets; do not guess Debian/Ubuntu versions).
2. Re-test the main **SELECT faces** and **OSM** on the same 19 pin so an
   OS/kernel move cannot hide as a Postgres change. Usual pair: pgbench
   SELECT (small scale) + OSM (writes).
3. `./newset` with an OS-vintage batch so assembly can split pre/post OS.

Hands-on on siren (no agent SSH). Agent SSH twilight. Abbey and court
are not in this cutover unless asked. `super` already showed a 24.04 vs
26.04 SELECT drop and then died — treat an OS retest as environment
until a second host agrees.

**Execution.** Once a study’s matrix is written down here (and any conf fragments
are in git), Greg points the agent at **twilight** to run it. Repeat / validate
on other hosts only after twilight shows which corners matter — and prefer
known-safe settings on siren/abbey so they do not OOM or fill the disk mid-matrix.

### Study 1: durability / WAL volume vs throughput

**Question.** On the medium-frequency checkpoint envelope (`max_wal_size=100GB`,
`checkpoint_timeout=30min`), how much of the fast→durable gap is **WAL volume**
(`wal_level`) versus **sync waits** (`fsync` / `synchronous_commit`)?

Abbey PG18 set 11 paid a **severe** bundled penalty: fast 7.43–7.49h / 404–400
kNodes/s vs durable 11.10–11.17h / 270–268. Some systems are WAL-volume
driven; abbey is suspected **Darwin fsync** (APFS / `fsync` behavior, not
`wal_level`). Bundled `osm-sync-fast` / `osm-sync-durable` (conf 16–18) flipped
all of `wal_level`, `fsync`, `synchronous_commit`, and `full_page_writes` at
once and cannot answer that. Conf 18 and 19 split them:

| File pair | Axis | Default |
|---|---|---|
| `osm-wal-replica` / `osm-wal-minimal` | WAL volume (`max_wal_senders=0` with minimal) | replica |
| `osm-fsync-on` / `osm-fsync-off` | `fsync` + `synchronous_commit` | on |
| `osm-fpw-on` / `osm-fpw-off` | full-page writes | on |

**2×2** (same set; `test_settings`; **FPW held on**). **2026-10-22 — abbey
set 11 is running it on PG18** (Homebrew fold; Darwin fsync-suspect).
First corner **replica + fsync off**. Siren is parked (Ways deaths).
Twilight after set 119 OSM is the Linux comparison. Do not run a third
bundled fast/durable repeat.

| | `osm-fsync-on` | `osm-fsync-off` |
|---|---|---|
| `osm-wal-replica` | current durable | fat WAL, no sync waits |
| `osm-wal-minimal` | thin WAL, durable waits | WAL+sync off (add `osm-fpw-off` only to match historical fast) |

Fat-WAL (`replica` + `fsync` off) belongs on twilight’s disk headroom, not on
siren’s 2TB squeeze. `git pull` on siren does not change GUCs (conf.d is a
copy). Do not `cp` into `/etc/postgresql/19/main/conf.d` until its PG19 cells
finish.

**PG18 — backfill on siren: stopped 2026-10-16.** Do not retry PG18
fast/minimal / thin-WAL on siren (those Ways deaths were 240mm + no rear
fan). Those corners are re-run after the WAL vs fsync split, not by burning
more bundled cells on this chassis. Rear fan is in; leftover PG18 OSM is
the probe (**4.07h** 2026-10-18, replacement for the wiped cell). Hands-on only — do
**not** SSH siren.

**18↔19 from data already on decade.** Siren set **70** PG18.3 durable
(2970–2973, 4.45–4.52 h / 663–673) vs set **71** PG19 durable (3011–3013,
4.34–4.44 h / 675–690) and PG19 fast (2974/2975/3009/3010, 4.03–4.17 h /
719–744). **19rc1 durable 4.49h** matches that beta4 durable band. Twilight
117 (PG18.3 fast) vs 118 (PG19 fast+durable). Abbey set 11 is PG18 only
(Mac).

### Study 2: checksum overhead

**Deferred from PG18** — planned then, pushed forward to deal with GIS bugs.
PG18 defaulted `data_checksums` on for new clusters; the question never got a
clean OSM grid.

**Question.** What is the throughput / CPU / WAL cost of page checksums on the
same durable medium-checkpoint baseline used after study 1? Rows already carry
`data_checksums` via `test_settings` (`write_internals` / submission `csum`).

**How to run it.** Checksums are **cluster-level** (initdb / `pg_checksums`), not
a GUC flip on a live data directory. Prefer a second cluster on twilight (siren
already had an `18-nocheck` pattern) with checksums off, same `conf/19` otherwise,
same planet load, 3–5 repeats. Compare against checksums-on baselines from study
1 — do not retune durability or memory in this matrix. Publish via study SQL
keyed on `csum` / `data_checksums`.

### Study 3: node cache vs shared_buffers

Do **not** open this until study 1 has a durable baseline worth keeping and the
participating servers share that durable `conf/19` plus the same one-point OSM
load (`osm2pgsql-1.11`, 5 clients, same `scale` / `OSMNODECACHE`). Prefer all
four (siren, twilight, abbey, court) on PG19 when practical; do not block the
memory study forever on court if the others already match.

**Question.** The PG17 OSM config was a local maximum: high memory use that delivered peak throughput. Parallel GIN / index work in PG18 destabilized that peak (see the final PG18 retune commit). On 128GB hosts the node-cache phase packs `osm2pgsql` RSS (~60GB at scale 75000), `shared_buffers` (48GB in `osm-mem-128`), and shared memory into RAM and spills into the default ~15GB swap. When the loader enters the index phase it **drops the node cache**; Postgres pages that were pushed out are not pulled back automatically, then `maintenance_work_mem` × parallel maintenance workers allocates on top. Suspect the fix is to shrink **either** the osm2pgsql node cache (`scale` / `OSMNODECACHE` in `params`) **or** `shared_buffers` (`osm-mem-*`), not to keep chasing the PG17 packing.

**How to run it.** Explore the matrix on **twilight** first (agent-driven once
Greg points at it). `./newset` with a shared description prefix; change one
variable at a time (`osm-mem-*` tier or `scale` / `OSMNODECACHE`), keep
durability durable, and let report SQL separate rows via `test_settings`.
Compare hours, `overall_kips`, `score_kips`, `index_kips`, and swap/iowait across the index
transition. Replicate only interesting corners on other hosts; avoid packing
experiments on siren/abbey until twilight shows they fit. Promote a winner into
`conf/19` only with a commit that cites the study.

### Study 4: maintenance_work_mem

Open only after study 3 has picked a memory packing (or confirmed the current
one). Sweep additional `maintenance_work_mem` values on **twilight** under that
fixed durable + buffer/cache baseline — one GUC at a time, same set — watching
index-phase throughput and whether larger values revive the PG18-era
parallel-maintenance pain. Do not mix this sweep with durability, checksums, or
`shared_buffers` changes.

### Recorded setup: court, PostgreSQL 18 via PGDG (arm64, 2026-10-15)

Court was on Ubuntu’s `postgresql-16` (not PGDG). Goal: install PG18 from
[apt.postgresql.org](https://wiki.postgresql.org/wiki/Apt) the way twilight does
on amd64, then cut pgbent over. **PGDG publishes `noble`/`arm64` packages** —
`postgresql-18` 18.6 and `postgresql-18-postgis-3` 3.6.x are in the index.

**Do not `apt install` while an OSM load is on PG16.** The install upgrades
`postgresql-common` (257 Ubuntu → 293 PGDG) and refreshes `postgresql-16-postgis-3*`,
which is unsafe under osm2pgsql. Add the repo anytime; install only when the
cluster is idle (after `repeat-gis` finishes / `complete`).

#### Already done (2026-10-15, mid set-3 load)

As `gsmith` on court:

```bash
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc
# /etc/apt/sources.list.d/pgdg.list (twilight-style major pin):
#   deb [arch=arm64 signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
#     http://apt.postgresql.org/pub/repos/apt noble-pgdg main 18
sudo apt-get update
# Simulated only:
#   sudo apt-get install -s postgresql-18 postgresql-18-postgis-3 \
#     postgresql-18-postgis-3-scripts
```

Repo was live; packages resolved. Install deferred until idle, then completed
**2026-10-15**:

- `apt-get install` PGDG `postgresql-18` 18.6 + PostGIS 3.6.4 (also refreshed
  `postgresql-common` / PG16 PostGIS). **`pg_createcluster 18 main --start`**
  was required — package install did not auto-create the cluster
  (`create_main_cluster` off in createcluster.conf).
- Port **5433** (`16/main` remains **5432** for the results DB).
- Deployed `conf/18/conf.d` by copy (fast-sync active in tree: `fsync=off`,
  `wal_level=minimal`, `shared_buffers=48GB`, `max_wal_size=100GB`,
  `checkpoint_timeout=30min`). `pg_hba` matched 16’s trust LAN block.
- `config`: `TESTPORT=5433`, `RESULTPORT=5432` (results stay on 16),
  `DISKLIST=nvme0n1`. `util/newgis` + PostGIS OK. `./newset 'PG18'`.
- **Shrunk results cluster:** flipped `16/main` from `osm-mem-128` (48GB) to
  `osm-mem-16` (`shared_buffers=1GB`) and restarted — see **Two majors in
  parallel** below. Then `nohup util/repeat-gis` (test 16, `osm2pgsql-1.11`,
  scale 75000); do **not** re-run `wl/osm-import` (it would `newset "OSM"`).

#### When told to fire up the new cluster (done on court 2026-10-15)

Historical checklist (for the next Spark / similar host):

1. Confirm idle: no `osm2pgsql` / `benchwarmer` / `repeat-gis`.
2. `sudo apt-get install -y postgresql-18 postgresql-18-postgis-3 postgresql-18-postgis-3-scripts`
3. If `pg_lsclusters` has no 18: `sudo pg_createcluster 18 main --start`
4. Pull pgbent as postgres; `sudo cp ~postgres/pgbent/conf/18/conf.d/* /etc/postgresql/18/main/conf.d/`
5. Trust `pg_hba` from `conf/pg-hba.trusted` / existing 16; restart 18
6. `TESTPORT=<18 port>`, keep `RESULTPORT` on the results major; `util/newgis`; `./newset 'PG18'`

Reference: twilight’s `/etc/apt/sources.list.d/pgdg.list` pins `noble-pgdg main 19`
(with 17/18 lines commented). Court uses the same file shape with `main 18`.

#### Court: `OSMRELPROF` on durable PG18; stretch = PG19 (2026-10-16)

Court’s Linux post-process path is fine (no Darwin/`init_sys_streams` hiccup).
It is the slowest box on this OSM cell, so durable repeats trail the fleet —
good place to shake out relation-phase perf collection.

**Done on court 2026-10-16:** installed `/usr/local/bin/pgbent_perf` + NOPASSWD;
after fast test 17 (`complete`), flipped to durable (`fsync=on`,
`wal_level=replica`), set `OSMRELPROF=1`, restarted `repeat-gis` (same set).
Expect `osm-rel-perf.data` / report / `osm-rel-prof.log` under each new test
dir. If `perf record` fails on Spark (permissions / PMU), fix from that log;
do not block durability collection.

**Court PG19 rc1 set 5** is enough to start: durable **20/21/22**
(8.73–8.78h / 342–353) and fast **23** (8.30h / 361). **2026-10-22 —
set 9 test 145** is the extra durable cell with `OSMRELPROF=1` and the
1h stop (22/23 were unreadable after the 8GB cap). Do not start a
second court OSM while 145 runs. The matching x86 `perf` series is
**twilight at `mem=128G`**, not siren.

### Two majors in parallel (test + results)

This is why the small (**1GB `shared_buffers`**) results clusters hang around
on the **previous major**. **Do not put `results` in a beta instance.** After
a catalog version bump (PG19 rc1 vs beta4 is the example), that datadir can
be unreadable — `pg_upgrade` will not save it, and the history is gone. Keep
`RESULTPORT` on a released major until you choose to migrate. The test cluster
can be thrown away and recreated; the results cluster cannot.

pgbent often keeps **two clusters online** on one host: the **test** major
(OSM / pgbench, fat memory settings) and an older **results** major (just the
`results` database). `config` splits them:

| Knob | Role |
|------|------|
| `TESTPORT` | Active study cluster (`gis`, large `shared_buffers`) |
| `RESULTPORT` | Results DB — usually the previous major; **do not** set this equal to `TESTPORT` while the old cluster still holds history |

Leaving the results major on its old OSM memory tier (e.g. `osm-mem-128` →
48GB) **doubles** the shared-memory bill next to a 48GB test cluster and can
starve the load. After cutover, shrink the results cluster before starting
OSM:

```bash
# on the results major's conf.d (example: court 16/main)
cd /etc/postgresql/<results-major>/main/conf.d
sudo mv osm-mem-128.conf osm-mem-128.off   # or whichever fat tier is active
sudo mv osm-mem-16.off osm-mem-16.conf     # shared_buffers = 1GB
sudo pg_ctlcluster <results-major> main restart
psql -p <RESULTPORT> -c 'SHOW shared_buffers;'   # expect 1GB
```

`osm-mem-16.conf` in `conf/<N>/conf.d` is the intended “results babysitter”
size (1GB). Keep other OSM-oriented GUCs on that cluster harmless; the point
is not to retune results performance — only to stop it gobbling RAM.

Also stop every major that is neither test nor results (`pg_lsclusters` /
`systemctl stop postgresql@…`) so idle clusters are not sitting on memory.
Siren’s pattern: results on 17, test on 19, everything else stopped. Court’s
PG18 cutover (2026-10-15): results on **16:5432 @ 1GB**, test on **18:5433 @
48GB**. Twilight after the 2026-10-22 boot: results **16:5432**, test
**19:5437**, **14/15/17/18** stopped and `start.conf` **manual**.

### Twilight boot + Fury 19 recreate

Twilight keeps many PGDG majors installed. `postgresql.service` starts every
cluster with `start.conf` **auto**, so a reboot brings up 14+16+17+18+19
together (15’s datadir is already gone). **Each boot:** `pg_lsclusters`,
stop every major that is not results or test, and set those
`/etc/postgresql/<N>/main/start.conf` lines to **manual** plus
`systemctl daemon-reload` so the next boot does not repeat the pile-up.
Leave **16/main** (results, port 5432) and **19/main** (test, port 5437)
**auto**. Packages stay installed.

**PG15 logs on boot `/`.** 15’s datadir is gone but
`/var/log/postgresql/postgresql-15-main.log` was **179G** (2023–2025).
Boot `logrotate` (pid 1056, 2026-10-22) copied it to `.log.1` and filled
`/` (0 bytes free). `stop-set` does not kill `wl/select-faces`; kill that
PID too. Truncate 15 logs **as postgres** (`sudo truncate` as gsmith was
denied). Empty `params` (disk-full `pin()` / `mv`) makes later faces
0-TPS — restore params before resuming.

**19 datadir is a symlink** (`/var/lib/postgresql/19/main` →
`/fury1/19/main`). A catalog bump (beta4 → rc1) cannot `pg_upgrade`. Debian
PostgreSQL also does **not** support running `initdb` directly when a catalog
change needs a new data directory. The only supported route is the
`pg_*` wrappers exclusively (`pg_dropcluster`, `pg_createcluster`,
`pg_ctlcluster`). That is why this looks odd: create on the boot-disk
default path with `pg_createcluster`, then rsync/relink onto Fury. Do not
`initdb -D /fury1/19/main`.

1. Save `/etc/postgresql/19` (conf.d, `pg_hba`, port).
2. `pg_ctlcluster 19 main stop`.
3. `mv /fury1/19/main /fury1/19/main.orig` **before** dropcluster follows
   the link (that tree was ~919GB of beta4 `gis`).
4. `rm` the dangling `/var/lib/postgresql/19/main` symlink.
5. `pg_dropcluster 19 main` (warns if the data directory is already gone).
6. `apt-get install` `postgresql-19` **rc1** (and jit / PostGIS).
7. `pg_createcluster 19 main --port 5437 --locale en_US.UTF-8` on the boot
   disk (do not `--start` yet).
8. `rsync -aHAX` that new `main/` to `/fury1/19/main/`.
9. Remove the boot-disk copy, `ln -s /fury1/19/main /var/lib/postgresql/19/main`.
10. Restore saved `conf.d` + `pg_hba.conf`; keep the rc1 `postgresql.conf`.
11. `systemctl start postgresql@19-main`. If the unit fails, start with
    `pg_ctlcluster 19 main start` and read
    `/var/log/postgresql/postgresql-19-main.log`.

Confirm `version()` is 19rc1, `pg_control_system()` catalog **202610061**,
`debug_assertions` off, `fsync` on / `wal_level=replica`, `shared_buffers=48GB`.
Results stay on 16. Fresh cluster has no `pgbench` database — `createdb -p 5437
pgbench` before `wl/select-faces` (benchwarmer’s checkpoint wait connects to
`$TESTDB`). Then `./newset 'PG19 rc1'` and the four-face sweep; `util/newgis`
waits until OSM (Fury TRIM tax).

During OSM validation, a brief `iostat` look confirms writes landed on the
Fury datadir disk (`nvme0n1` = `/fury1`), not the boot SSD (`nvme3n1`).
Nodes/`nodes.db` is `/fury0` (`nvme1n1`); the planet file is `/fury2`
(`nvme2n1`). Wait until the **Way** phase — that is when write volume to
the database shows up. Earlier phases will not prove the symlink.

Migrate results onto the new major only when ready (see **Migrating the
results database** below); until then, `RESULTPORT` stays on the shrunk old
cluster.

### Recorded setup: siren, PostgreSQL 19 (2026-10-13)

Taken from the `gsmith` and `postgres` shell histories. Failed typos are omitted. Older major versions stay installed; this setup does not remove PostgreSQL 18. On this host the benchmark drive is `/sk51` (same disk as the PG18 `main` cluster) and Debian assigned port **5437**. See **Siren hardware** above for 9950X power-off-under-load / possible 9600X rollback after initial PG19 results.

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

Leave only two clusters online: the results database and the active one (see
**Two majors in parallel** — shrink the results major’s `shared_buffers`). On
siren the results database is still the PostgreSQL 17 cluster (port 5433).
Everything else stays installed and is stopped:

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

Finished OSM loads are read in context from the results database. `reports/osm-speed.sql` returns three summaries: one row per test (hours, overall_kips, score_kips), a phase breakdown (polygon/line/point index kips scaled by node_count, plus node, way, relation, score, and index rates), and the tuned settings (buffers, durability, checkpoint and WAL rates). `score_kips` is the OSM scoreboard number: `node_count / (relation_seconds + polygon + line) / 1000`.

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
| OSM planet load (loop) | `wl/osm-import`, then `nohup util/repeat-gis &` | `osm2pgsql%` |
| OSM one-shot | `util/newgis` (if needed), then `nohup ./runset &` — not `repeat-gis` + `complete` | `osm2pgsql%` |
| pgbench SELECT grid | `wl/select-grid && ./runset` | `select` |
| pgbench init (build time) | Recorded automatically by `runset` before each scale when `NEWINIT=1` | `:-i%` |
| Single point | `./benchwarmer <clients>` | as configured |

### Wiping bad tests

Failed pgbench runs leave a lot of junk (`pgbench_log.*`, huge `timing.csv`);
TPS is usually junk too, so they are easy to find. Suspect init rows
(`script` like `:-i%`) can usually be wiped unless this set is a build-time
study — scale 100 SELECT is not reviewing build time.

```bash
./cleanup_singlevalue <test>
./webreport          # always, so index.htm and charts drop the gone rows
```

`./stop-set cleanup` wipes only the unfinished latest test; still run
`./webreport` after.

`wl/osm-import` writes the standard `params` for this loop, including `RECOVERY=3600`. Run it, then edit those parameters if this host needs a change. `repeat-gis` does not invent that file. `wl/osm-import` also calls `./newset "OSM"`; if this host is already on the right batch (e.g. `PG19 beta4`), run `./newset` again only when that batch boundary is wrong — not for each GUC tweak.

**One-shot vs loop.** For a single OSM (or other) cell, use `./runset`
directly — do not start `repeat-gis` and then try to arm `complete`.
`repeat-gis` clears `complete` at start and is for multi-run collection.
Greg’s usual one-cell path: set GUCs / `params`, `util/newgis` if the DB
needs a fresh `gis`, then `nohup ./runset &` (or `setsid nohup ./runset`).

OSM loop control (`repeat-gis` only):

```bash
watch util/progress   # live dashboard: disk use, DB/WAL size, tail of current results.txt and nohup.out
util/progress f       # same snapshot, then tail -f results.txt (OSM loader)
touch complete        # (in STATEDIR) stop after the current run finishes
./stop-set            # kill the loop / workload / collectors now
./stop-set cleanup    # same, and wipe the unfinished latest test
```

`watch util/progress` follows `repeat-gis` through its transitions: newgis, recovery sleep, and the next `runset`. It always shows the latest set's newest test, so one dashboard can stay open for the whole loop. This was verified on siren. On macOS, `watch` comes from Homebrew (`brew install watch`).

- A planet load takes roughly 3–5 hours on desktop hardware. `wl/osm-import` sets `RECOVERY=3600` as an **informed** hour of cooldown (disk cache **and** thermal: 240mm AIO / room heat dump). On siren’s 9950X that hour is why a crash can be followed by a live `k10temp` look; it is not a guess that the box will stay up.
- `util/newgis` recreates `gis` with extensions and runs `pgbent_tune`. If it fails, `repeat-gis` stops and removes the pid files. A failed `dropdb` means connections are still open — usually **zombie `timed-os-stats` collectors** left from a crashed OSM/`benchwarmer` (they keep a `psql` session on `gis` via `util/metric-query.sql`). Clear them, then retry:

```bash
# as postgres, from ~/pgbent
./stop-set            # loop + osm2pgsql/pgbench + timed-os-stats (+ gis backends)
# ./stop-set cleanup  # also wipe the aborted test row
util/newgis
```

Confirm `pgrep` shows no collectors and `pg_stat_activity` has no `gis` rows before `dropdb`. `pgbent_tune` at the end of `newgis` may sit in `fstrim -av` for a long time on multi-TB hosts; `gis` is already usable once extensions are created. Twilight 2026-10-15 after test 2599: idle metric `psql` from 08:00 blocked `newgis` until collectors were killed.

**Twilight Fury TRIM (open question).** On twilight’s **4TB Fury** NVMe mounts
(`fury0`/`fury1`/`fury2`), `fstrim -av` from `pgbent_tune` routinely takes a
**very** long time (tens of minutes; seen trimming ~1.9 TiB reported on a Fury
volume). Greg has a personal note to dig into **why** (discard behavior, mount
options, firmware, whether weekly fstrim + per-`newgis` trim is redundant, etc.).
**Get to the bottom of that before launching the big PG19 GUC exploration
matrix on twilight** — otherwise every `newgis` between corners burns a long
TRIM tax. Until resolved: expect the wait, do not treat a stuck-looking
`pgbent_tune` as a hung newgis if `gis` already answers, and prefer not to
stack back-to-back newgis cycles when debugging TRIM itself.
- After each `runset`, `repeat-gis` reads the latest test's `tps`. A blank or zero TPS means the run failed, often because the disk filled, and the loop stops instead of starting another load.
- Configured `max_wal_size` is 100GB. That plus the planet database barely fits a 2TB drive, so a 2TB host has to move the previous major's cluster off that disk first. 256GB `max_wal_size` will not fit on 2TB. A 4TB host does not need that disk shuffle.
- A crashed run can leave orphaned OS stats collectors (`timed-os-stats`, iostat, vmstat). Check `ps` before restarting.
- After a datadir move or catalog recreate, a brief live `iostat` check during
  OSM validation: wait for the **Way** phase before judging write volume to
  the database disk. Nodes and planet-file reads will not show that.

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
- [ ] test_metrics_data rows exist (power rows too if SUDODATA=1; `Tctl_temp1_input` on AMD hosts with k10temp)
- [ ] Run appears in submission; OSM studies need non-null max_write_mbps
- [ ] OSM after a disk move / catalog recreate: live `iostat` in the **Way** phase shows writes on the database disk
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
- Every successful `./upload` leaves a durable copy: locally under `results/<server>/`
  (including `<server>-results.sql`) and as a timestamped tar.gz on `$ARCHIVE`.
  `./download` also keeps those tar.gz files under `archive/` on the assembly machine.

## Migrating the results database across a major upgrade

When the host that holds the **results** database moves to a new PostgreSQL major
(Homebrew single-cluster Macs like abbey, or a dedicated results cluster on Linux),
preserve history **before** the old major goes away:

```
- [ ] On the old major, still running: `./upload`
      Confirms `results/<server>/<server>-results.sql` exists and a fresh
      `<server>-<timestamp>.tar.gz` is on `$ARCHIVE`.
- [ ] Install/start the new major. Create an empty results DB
      (`createdb results && psql -f init/resultdb.sql -d results`, or the host's usual bootstrap).
- [ ] Point `./config` (RESULT* / TEST*) at the new cluster/port.
- [ ] Reload history, pick one:
      - Local: `psql -d results -f results/<server>/<server>-results.sql`
      - Via archive: `./download` on a machine that imports that server's newest tar.gz
        (`wipe_server` + unpack + load, same as assembly).
- [ ] `./newset` with no args — prior sets must list. Errors for objects not in
      `init/resultdb.sql` (e.g. `submission*`) are harmless if core tables loaded.
- [ ] `./newset "…"` for the new major's study, then continue runs as usual.
```

Do not open the new major's study set until the reload check passes. Abbey's
Homebrew PG17→18 move (2026-10-14) is the reference for this path.

## Recording findings

Regressions and crashes found during a study are a deliverable. PG18 testing
found an 18.0 `maintenance_work_mem` crash. When something breaks:

1. Reproduce it on a second run, ideally on a second machine.
2. Record the server, test number, version, and the study variable's value from `test_settings`.
3. A finding may itself open a new study. Flag it with its own `newset`.
4. Work around it in `conf/<N>` with the issue cited in the commit message (`pg-release-config`).

**Bug vs environment.** Separating a real Postgres/osm2pgsql defect from a lab
glitch is hard and expensive. Prefer a second host and a stock-stable config
before treating a crash as upstream news. Hardware ghosts look like software
until they do not — same class as siren’s 9950X hard power-off (2026-10-15
and **again 2026-10-16**) and twilight’s past 14900K instability. Thermal
problems **start by looking like the machine went down**, not like a tidy
package-power cliff. On siren that is a **board trip near 90°C Tctl**
(k10temp now on the trace), not CPU throttle. Document suspected environment factors next to the
finding; do not open a community bug (or publish a “Postgres regression”)
on a single flaky box without that check.

Examples that burned real calendar time / reputation:

- **Overclock** — publicly spent a **month** chasing a “crash bug” that was a
  motherboard overclock of a few percent; survived weeks of light testing,
  lethal under the real load.
- **Early Intel SSD** — device bug set **maximum queue depth to 0**; published
  numbers based on that setup later needed an **official retraction apology**.
- **AIO fan** — failed in public on early pgbent; **TPS moved first**, then the
  hardware story. Same pattern as `super` (2× EPYC 7702): 960-client sockets
  SELECT on a **24.04** kernel (~1.53M TPS) could not be matched on **26.04**
  (big drop), then the server died — suspect slow thermal, not a kernel
  verdict, until a second 2S reproduces. That line of work published as
  [PostgreSQL 13 Benchmark: Memory Speed vs. TPS](https://www.crunchydata.com/blog/postgresql-13-benchmark-memory-speed-vs.-tps)
  (also covers the overclocking/holiday-crash saga: a few percent CPU
  overheat flipping a bit, chased as a once-per-day PG crash).

Storage firmware, queue depth, thermal limits, and “it passed a few weeks of
basic soak” are not proof the platform is innocent.
