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

Confirm with `taskinfo` on the postmaster (backends inherit the clamp).

| How Postgres is started | QoS clamp | I/O tier | select-scatter c=1 cold | c=32 cold |
|-------------------------|-----------|----------|-------------------------|-----------|
| `brew services` | `THREAD_QOS_UTILITY` | tier 1 | ~52–53 TPS | ~1670–1677 |
| `pg_ctl` from ssh/login | none | tier 0 | ~68 TPS | ~2577–2579 |

About **+30% at c=1** and **+54% at c=32** when unclamped. Published Abbey select-scatter set 13 was under the clamped service — treat those numbers as soft. Intermittent “Darwin looks fine / then doesn’t” OSM behavior matches sometimes using `brew services` and sometimes a manual `pg_ctl`.

### Recipe

For database work, do not use stock `brew services` as the long-running server:

```bash
brew services stop postgresql@18
export LC_ALL=en_US.UTF-8   # required; bare pg_ctl can fail "multithreaded during startup"
pg_ctl -D /opt/homebrew/var/postgresql@18 -l logfile -w start
```

A custom LaunchDaemon/Agent without the utility clamp is fine; the Homebrew one is not.

## Block size

Rebuilding Postgres with `--with-blocksize=16` to match Apple Silicon’s 16 KB VM pages was A/B’d unclamped against 8 KB Homebrew on the same cold select-scatter protocol: **flat** (~71 vs ~68 at c=1, ~2198 vs ~2160 at c=32). Spindle-era lore that larger pages half the I/O count does not show up here. Prefer fixing the I/O class over a custom page size.

## OSM check

An unclamped durable OSM load on Abbey (set 15) is the Relations confirmation: if Relations moves ~50% with the class fix, Darwin is solved enough for the current release cycle.

Details: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
