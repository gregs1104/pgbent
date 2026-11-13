---
layout: home
title: ARM random read vs x86
permalink: /studies/arm-random-read-vs-x86/
parent: Studies
nav_order: 1
---

# ARM vs x86: slow scattered index→heap buffer misses

**Status:** Initial report (2026-11-13). Intended for discussion on pgsql-hackers. Not claiming a PostgreSQL bug yet.

On a pair of ~128 GB NVMe boxes running PostgreSQL **19**, the durable OSM **Relations** phase is about **3.5× slower on ARM** than on a similar-class x86 host:

| host | CPU | Relations (s) | overall (s) |
|------|-----|---------------|-------------|
| court (ARM) | NVIDIA P4242 / Cortex-X925+A725, 20 threads, ~121 GB, Samsung 3.7 TB NVMe | 13251 | 30871 |
| twilight (x86) | i5-13600K, 20 threads, ~125 GB, Kingston 3.7 TB NVMe | 3797 | 19118 |

Same major, same durable face (`wal_level=replica`, `fsync=on`), same planet load path. Court tests **149**; twilight **2713**.

The usual CPU suspects do not add up here. Missing wide AVX-class SIMD on ARM, or a big Intel core’s stronger branch prediction, would show up as busy Postgres backends burning cycles. On court the ARM CPUs were mostly **idle** — stuck waiting somewhere — so this is a stall story, not a “x86 executes the same Postgres path faster” story. That also explains the **very low package power** in these sections; the power cliff was the first clue that the cores were not working hard.

Profiles on court light up the single-block buffer-fill path (`StartReadBuffer` → `pgaio_io_perform_synchronously` → `pread`). That looks scary next to AIO, but for index nested-loop heap fetches that path is intentionally synchronous under `io_method=worker` as well — so the profile may just be “where the miss waits,” not “AIO is broken on ARM.”

To separate hypotheses, a small durable-face miniature of that access shape was run as an isolation series on both hosts.

## Workload

`pgbench` custom script **select-scatter**: **64 unsorted random `aid`s** → nested-loop index probes + heap fetches on `pgbench_accounts` (planner forced off seq/bitmap).

Artifacts in this study directory (also wired into the live toolkit as `tests/select-scatter.sql` and `wl/arm-miss-isolation`):

| File | Role |
|------|------|
| [select-scatter.sql](select-scatter.sql) | pgbench script |
| [arm-miss-isolation](arm-miss-isolation) | run grid / cold start / RA cells |
| [iso-io-worker.conf](iso-io-worker.conf) / [iso-io-sync.off](iso-io-sync.off) | flip `io_method` for the sync cell |

- Linux pair: **scale 13700 (~200 GB)**; Abbey (Darwin): **scale 17500 (~256 GB, ~2×RAM)** — working set does **not** fit in RAM either way
- Cold OS page cache before the grid (Linux `drop_caches`; Darwin `purge`)
- Clients **1 / 8 / 32**, 180 s, two passes
- `shared_buffers` **48 GB**; default cell `io_method=worker`; Linux device `read_ahead_kb=2048` unless noted

## Results (tps, select-scatter)

Second pass is warmer; gaps are stable either way.

### Linux isolation (PG 19rc2, scale 13700)

| cell | court c=1 | court c=32 | twilight c=1 | twilight c=32 |
|------|-----------|------------|--------------|---------------|
| worker, RA=2048 | ~35 → ~73 | ~1865 / ~1871 | ~158 → ~306 | ~6655 / ~6699 |
| **sync**, RA=2048 | ~34 → ~72 | ~1936 / ~1879 | ~158 → ~306 | ~6540 / ~6678 |
| worker, **RA=128** (court) | ~33 → ~70 | ~1848 / ~1851 | — | — |
| worker, **RA=0** (court) | ~17 → ~36 | ~913 / ~1018 | — | — |

Sets: court **14–17**; twilight **124–125**.

### Darwin ARM cross-check (PG 18.6, scale 17500)

| host | CPU | c=1 | c=8 | c=32 |
|------|-----|-----|-----|------|
| abbey | Apple M4 Max, 128 GB, macOS | 85 → 115 | 867 → 957 | 2331 → 2400 |

Set **13**, durable face (`fsync=on`, `wal_level=replica`, `io_method=worker`). Slightly larger DB than the Linux pair, so if anything this understates Abbey vs court/twilight.

### Takeaways

1. **`io_method=sync` ≈ `worker` on both Linux hosts.** The ARM/x86 gap does **not** move. That kills “PG19 AIO worker glue is the ARM tax” for this shape.
2. **Court `read_ahead_kb` 2048 vs 128 is flat.** Setting **0 hurts** (~½ throughput). So the gap is not “ARM is over-readaheading at 2048.”
3. **A second ARM vendor/OS is also well below x86.** At 32 clients, twilight is ~**3.5×** court and ~**2.8×** Abbey. Abbey beating court by ~**1.3×** is more or less the **standard CPU gap** between an M4 and the ARM cores in the DGX Spark — not evidence that Darwin “fixed” the miss path. Both ARM hosts still lose the same way to the x86 box (and Abbey was on PG 18 with a slightly larger DB).
4. After (1)–(3), what remains is the boring, hard one: **miss cost / miss behavior on ARM hosts** for this scattered index→heap pattern (page cache, storage, copy/clear, locality — not the AIO method switch and not the usual readahead knob).

## Handoff

The useful product of this investigation is the **public reproduction**, not a root-cause in the ARM memory/storage stack. Isolating past AIO and `read_ahead_kb`, with the same stall/low-power signature on two ARM vendors, is as far as this lab is going to push without platform experts. If you have ARM page-cache / block-layer / Darwin-vs-Linux I/O background, the scripts below are meant to be dropped onto your own boxes.

Natural next reproduction: **Graviton** (another Linux ARM vendor, easy for cloud folks to spin). Worth pinging Andres, Haas, or one of the Amazon people on `-hackers` to try the same `select-scatter` cold grid there — if Graviton matches court/abbey, the story is “ARM buffered random miss” broadly; if it matches twilight, we learn something about the DGX/Apple side instead.

Open threads for someone else (optional): `effective_io_concurrency=0`, `posix_fadvise`/prefetch shape, filesystem, `perf` on the fill path under `io_method=sync`, sequential heap walk of similar bytes.

## Reproduce

```bash
./newset 'ARM miss isolation — select-scatter durable baseline'
SKIPINIT=0 COLD=0 SCALES=17500 ./wl/arm-miss-isolation   # build DB
SKIPINIT=1 COLD=1 CELL=baseline SCALES=17500 ./wl/arm-miss-isolation
# then CELL=sync (after flipping io_method), CELL=ra128 / ra0 on Linux
```
