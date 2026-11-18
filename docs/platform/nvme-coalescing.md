---
layout: home
title: NVMe interrupt coalescing
permalink: /platform/nvme-coalescing/
parent: Platform guides
nav_order: 4
---

# NVMe interrupt coalescing

**Sales pitch:** database too slow on a new NVMe box? Check whether the drive left interrupt coalescing on. Turning it off is free and, on the DGX Spark lab host, made the OSM Relations phase about **1.75×** as fast.

## What it is

NVMe can delay completion interrupts until N completions pile up on a queue, or a timer fires. Desktop OEM firmware sometimes ships with something like **100 µs aggregation, threshold 8**. That helps interrupt rate and sequential throughput. It is a bad match for Postgres buffer misses: a backend waiting on one synchronous `pread` never reaches 8 completions, so every read can wait out the timer.

Check and clear (not saved to the drive unless you pass a save flag):

```bash
nvme get-feature /dev/nvme0 -f 8 -H
nvme set-feature /dev/nvme0 -f 8 -V 0
```

pgbent does the clear in `pgbent_tune` when `nvme-cli` is installed. A power cycle restores the firmware default until the script runs again.

## Evidence (court / DGX Spark)

Samsung `MZALC4T0HBL1`, firmware `NXHB202Q`, shipped with coalescing on. Twilight’s Kingston had it off. Same Postgres durable face, same select-scatter / OSM shape:

![Court NVMe coalescing on vs off — select-scatter and OSM Relations]({{ '/images/nvme-coalescing-compare.png' | relative_url }})

| | Coalescing on (shipped) | Coalescing off |
|--|-------------------------|----------------|
| select-scatter cold c=1 | ~35 TPS | ~100 TPS |
| select-scatter hot c=32 | ~1870 TPS | ~3880 TPS |
| OSM Relations | 13251 s (~1104/s) | 7614 s (~1921/s) |

Relations **~1.75×** faster (overall wall clock also improved; not charted here). Court still trails a similar-class x86 host by about 2× on Relations — not parity, and not claimed to be. Isolation ruled out AIO method, `effective_io_concurrency`, and IRQ pinning as the main lever.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/nvme-coalescing-compare.py`

Full write-up: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
