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

| How Postgres is started | QoS clamp | I/O tier | select-scatter-64 c=1 cold | c=32 cold |
|-------------------------|-----------|----------|-------------------------|-----------|
| `brew services` | `THREAD_QOS_UTILITY` | tier 1 | ~52–53 TPS | ~1670–1677 |
| `pg_ctl` from ssh/login | none | tier 0 | ~68 TPS | ~2577–2579 |

About **+30% at c=1** and **+54% at c=32** when unclamped. Published Abbey select-scatter-64 set **13** was under the clamped service — treat those numbers as soft. The unclamped A/B lives in ad-hoc `results/logs/darwin-qos-ab/` logs, not as a results-DB set. **Loose end:** after the btree build ladder (sets **17**/**18**), re-run the cold `select-scatter-64` grid under **tier 0** (`pg_ctl`) into a proper `testset` so the study has a published unclamped peer to set 13. Intermittent “Darwin looks fine / then doesn’t” OSM behavior matches sometimes using `brew services` and sometimes a manual `pg_ctl`.

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

## Verdict (closed 2026-11-20)

**Unclamping I/O class is not a free win for the whole OSM load.** Keep the operator recipe (prefer `pg_ctl` / tier 0 over stock `brew services`) for Relations-shaped random reads and SELECT scatter. Do **not** expect it to fix planet **index** wall time or board score by itself. No further Abbey I/O-class / REINDEX chase unless a new question opens.

| probe | result |
|-------|--------|
| Cold `select-scatter-64` clamp → unclamp (set **13** vs **20**) | Clear win (~86–139 @1 / ~3188–3368 @32 unclamped) |
| Durable OSM unclamp (sets **15** / **16**) | Relations ~**1.43×**; overall still ~**10.4h** — indexes stay slow |
| pgbench init btree ladder tier 1 vs 0 (sets **17** / **18**) | Mostly flat — no OSM-index-shaped free lunch |
| Block size 8 KB vs 16 KB | Flat |

Set **21** (clean-disk unclamped OSM retry, started 2026-11-20 with ~1.4 Ti free) may finish as a banked confirmation cell; it is **not** a gate and needs no follow-up matrix. Disk fill can spoil NVMe runs (leftover `gis`+`pgbench` left only ~393 Gi free before the cleanup) — keep headroom — but set **16** already had **1.5 Ti** free at start with slow indexes, so fill alone does not reopen the case.

## Block size

Rebuilding Postgres with `--with-blocksize=16` to match Apple Silicon’s 16 KB VM pages was A/B’d unclamped against 8 KB Homebrew on the same cold select-scatter-64 protocol: **flat** (~71 vs ~68 at c=1, ~2198 vs ~2160 at c=32). Spindle-era lore that larger pages half the I/O count does not show up here. Prefer fixing the I/O class over a custom page size.

Public durable board cell remains set **16** (score **279**). Details: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
