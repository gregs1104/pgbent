---
layout: home
title: macOS / Darwin
permalink: /platform/darwin/
parent: Platform guides
nav_order: 5
---

# macOS / Darwin

## Homebrew `brew services` I/O class

Homebrew’s `brew services` installs a LaunchAgent (`sh.brew.postgresql@N`) that starts Postgres under launchd. On Apple Silicon that agent runs with a **QoS clamp of `THREAD_QOS_UTILITY`**, which drops the process to **I/O throttle tier 1 (STANDARD)** instead of tier 0 (IMPORTANT). Disk reads look like background work relative to the desktop.

| How Postgres is started | QoS clamp | I/O tier | select-scatter c=1 cold | c=32 cold |
|-------------------------|-----------|----------|-------------------------|-----------|
| `brew services` | `THREAD_QOS_UTILITY` | tier 1 | ~52–53 TPS | ~1670–1677 |
| `pg_ctl` from ssh/login | none | tier 0 | ~68 TPS | ~2577–2579 |

About **+30% at c=1** and **+54% at c=32** when unclamped. Published Abbey select-scatter set 13 was under the clamped service — treat those numbers as soft. Intermittent “Darwin looks fine / then doesn’t” OSM behavior matches sometimes using `brew services` and sometimes a manual `pg_ctl`.

### Startup: tier 1 (brew / LaunchAgent)

```bash
brew services start postgresql@18
# LaunchAgent: ~/Library/LaunchAgents/sh.brew.postgresql@18.plist
```

### Startup: tier 0 (pg_ctl / unclamped)

For database work, do not use stock `brew services` as the long-running server:

```bash
brew services stop postgresql@18
export LC_ALL=en_US.UTF-8   # required; bare pg_ctl can fail "multithreaded during startup"
pg_ctl -D /opt/homebrew/var/postgresql@18 -l logfile -w start
```

A custom LaunchDaemon/Agent without the utility clamp is fine; the Homebrew one is not.

### Which tier is running?

`brew services list` only tells you whether Homebrew *thinks* the LaunchAgent is loaded. Confirm on the live postmaster:

```bash
PGDATA=/opt/homebrew/var/postgresql@18
pm=$(head -1 "$PGDATA/postmaster.pid")

brew services list | grep postgres
# tier 1:  postgresql@18 started … ~/Library/LaunchAgents/sh.brew.postgresql@18.plist
# tier 0:  postgresql@18 none   (or stopped) while pg_ctl still has a postmaster

ps -o pid,ppid,command -p "$pm"
# brew:    PPID 1, started by launchd
# pg_ctl:  often still PPID 1 after daemonize — do not trust PPID alone

sudo taskinfo "$pm" | grep -E 'qos clamp|eff iotier|coalition'
```

Decisive lines from `taskinfo` (Abbey, PostgreSQL 18.6 Homebrew):

**brew / tier 1** — coalition is the LaunchAgent; clamp and I/O tier match:

```text
coalition (type 0 RESOURCE) ID: … (sh.brew.postgresql@18)
requested policy
	req qos clamp: THREAD_QOS_UTILITY
effective policy
	eff iotier: THROTTLE_LEVEL_TIER1 (STANDARD)
	eff qos clamp: THREAD_QOS_UTILITY
```

**pg_ctl / tier 0** — no utility clamp; I/O stays IMPORTANT (from the select-scatter A/B log):

```text
eff iotier: THROTTLE_LEVEL_TIER0 (IMPORTANT)
eff qos clamp: THREAD_QOS_UNSPECIFIED
```

Backends inherit the postmaster’s effective policy. Spot-check one with `pgrep -P $pm -f 'postgres: '` and the same `taskinfo` grep.

## pgbench build-time experiment (Abbey)

OSM index builds stayed slow even after unclamping Relations. A cheaper first pass is the instrumented pgbench init that `runset` already records when `NEWINIT=1` (`script` like `:-i%`).

**Protocol (in flight as set 17):**

1. Start via **brew** (tier 1). Stash the class in `MULTI` (`1` = tier 1, `0` = tier 0).
2. Small scale ladder ≈ **½ / 1× / 2× RAM** on Abbey’s 128 GB: `SCALES="4250 8500 17500"`.
3. One client, short SELECT spacer, two reps: `SETCLIENTS=1`, `RUNTIME=30`, `SETTIMES=2`.
4. Repeat the same ladder after a **pg_ctl** restart with `MULTI=0`.

Default `config` already enables `NEWINIT` / server-side init (`:-i -I dtGvp`); only `params` needs the overrides above. Compare init wall time and disk metrics on the `:-i%` rows, split by `multi`. This surveys ordinary btree PK/index build under each I/O class — not OSM GIST/GIN — so a flat result here does not clear the planet index cliff.

If the ladder does not move with tier, next step is **`REINDEX`** on an already-loaded OSM database (same brew vs `pg_ctl` A/B). That still is not a perfect simulation: the real loader builds indexes **in parallel**, and the tier lever may only show up when several index builds (each multi-process) contend for I/O at once. A single `REINDEX` (or serial reindexes) can miss that interaction even on the same GIST/GIN shapes.

## Block size

Rebuilding Postgres with `--with-blocksize=16` to match Apple Silicon’s 16 KB VM pages was A/B’d unclamped against 8 KB Homebrew on the same cold select-scatter protocol: **flat** (~71 vs ~68 at c=1, ~2198 vs ~2160 at c=32). Spindle-era lore that larger pages half the I/O count does not show up here. Prefer fixing the I/O class over a custom page size.

## OSM check

Unclamped durable OSM on Abbey confirms the Relations win (set **15** ~**1944**/s; cool-disk retry set **16** ~**1930**/s, **~1.43×** vs clamped). Overall wall clock still lands near **10.4h** because index builds stay slow — unclamping is not free for the whole planet load. Public durable board cell is set **16** (score **279**).

Details: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
