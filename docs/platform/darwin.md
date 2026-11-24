---
layout: home
title: macOS LaunchAgent I/O class
permalink: /platform/darwin/
parent: Platform guides
nav_order: 3
---

# macOS LaunchAgent I/O class

## Homebrew `brew services` I/O class

Homebrew’s `brew services` installs a LaunchAgent (`sh.brew.postgresql@N`) that starts Postgres under launchd. On Apple Silicon that agent runs with a **QoS clamp of `THREAD_QOS_UTILITY`**, which drops the process to **I/O throttle tier 1 (STANDARD)** instead of tier 0 (IMPORTANT). Disk reads look like background work relative to the desktop.

| How Postgres is started | QoS clamp | I/O tier | c=1 | c=32 | OSM Relations/s |
|-------------------------|-----------|----------|-----|------|-----------------|
| `brew services` | `THREAD_QOS_UTILITY` | tier 1 | 85–115 | 2331–2400 | **~1,360** |
| `pg_ctl` from ssh/login | none | tier 0 | 86–139 | 3188–3368 | **~1,930** |

Published cold/hot select-scatter-64 grids (scale 17500, durable face) plus durable OSM Relations on the same I/O classes. Unclamping is about **+20% at c=1 hot**, **+40% at c=32**, and **~1.43×** Relations/s (~10 600 s → ~7 500 s). An earlier ad-hoc restart A/B (`results/logs/darwin-qos-ab/`) saw a similar direction at lower absolute TPS. Intermittent “Darwin looks fine / then doesn’t” OSM behavior matches sometimes using `brew services` and sometimes a manual `pg_ctl`.

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

**pg_ctl / tier 0** — no utility clamp; I/O stays IMPORTANT (from the select-scatter-64 A/B log):

```text
eff iotier: THROTTLE_LEVEL_TIER0 (IMPORTANT)
eff qos clamp: THREAD_QOS_UNSPECIFIED
```

Backends inherit the postmaster’s effective policy. Spot-check one with `pgrep -P $pm -f 'postgres: '` and the same `taskinfo` grep.

## Verdict (closed 2026-11-21)

**Unclamping I/O class is not a free win for the whole OSM load.** Keep the operator recipe (prefer `pg_ctl` / tier 0 over stock `brew services`) for Relations-shaped random reads and SELECT scatter. Do **not** expect it to fix planet **index** wall time or board score by itself. No further Abbey I/O-class / REINDEX chase unless a new question opens.

| probe | result |
|-------|--------|
| Cold `select-scatter-64` clamp → unclamp (set **13** vs **20**) | Clear win (set **20**: 86–139 @1 / 3188–3368 @32) |
| Durable OSM unclamp (sets **15** / **16**) | Relations ~**1.43×**; overall still ~**10.4h** — indexes stay slow |
| Clean-disk confirmation (set **21**, ~1.4 Ti free) | Indexes match **15**/**16** (~40k s); overall **10.86h** / score **276** — banked, not a board cell |
| pgbench init btree ladder tier 1 vs 0 (sets **17** / **18**) | Mostly flat — no OSM-index-shaped free lunch |
| Block size 8 KB vs 16 KB | Flat |

**Disk fill is a separate flaw.** When the Data volume is short on free space, Abbey OSM index builds can collapse into **>11 h** runs that are not fair comparisons. Set **11** tests **67** and **68** (~11.1 h, scores 268/270) were that pattern and have been **ejected** from the results DB. Keep headroom before a planet load. Slow indexes on the durable unclamped face (~40k s on **15**/**16**/**21**, including cool-disk and clean-disk retries) are **not** that fill cliff — they are the real cost of this face on Darwin.

## Block size

Rebuilding Postgres with `--with-blocksize=16` to match Apple Silicon’s 16 KB VM pages was A/B’d unclamped against 8 KB Homebrew on the same cold select-scatter-64 protocol: **flat** (~71 vs ~68 at c=1, ~2198 vs ~2160 at c=32). Spindle-era lore that larger pages half the I/O count does not show up here. Prefer fixing the I/O class over a custom page size.

Public durable board cell remains set **16** (score **279**, **10.41h**). Details: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
