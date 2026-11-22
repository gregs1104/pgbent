---
layout: home
title: NVMe interrupt coalescing
permalink: /platform/nvme-coalescing/
parent: NVIDIA DGX Spark
nav_order: 1
---

# NVMe interrupt coalescing

**Sales pitch:** database too slow on a new NVMe box? Check whether the drive left interrupt coalescing on. Turning it off is free and, on the DGX Spark lab host, made the OSM Relations phase about **1.75×** as fast.

## What it is

NVMe can delay completion interrupts until N completions pile up on a queue, or a timer fires. Desktop OEM firmware — and some vendor boot scripts — sometimes leave something like **100 µs aggregation, threshold 8** (`0x107`). That helps interrupt rate and sequential throughput. It is a bad match for Postgres buffer misses: a backend waiting on one synchronous `pread` never reaches 8 completions, so every read can wait out the timer.

Interrupt coalescing only changes **when the drive signals completion** (batch N completions or wait ~100 µs). It does not add, remove, or resize write commands, and it does not change how the controller programs NAND. Host write volume and write amplification stay the same; you just get more interrupts (and a bit more CPU) when it is off. That is a claim about **this feature alone**. Other `nvme set-feature` knobs, power-state / APST play, write-cache flips, forced TRIM storms, or synthetic fio write torture can absolutely wreck endurance — and people often change several things in one sitting. If wear skyrockets after a tuning binge, do not pin it on clearing feature 8; isolate changes, and treat everything beyond this interrupt-timing switch as your own experiment.

Check and clear (not saved to the drive unless you pass a save flag):

```bash
nvme get-feature /dev/nvme0 -f 8 -H
nvme set-feature /dev/nvme0 -f 8 -V 0
```

pgbent does the clear in `pgbent_tune` when `nvme-cli` is installed. A power cycle restores the firmware default until the script runs again. On DGX OS the story is stronger: the `nvidia-nvme-options` package installs `nvidia-nvme-interrupt-coalescing.service`, which **turns coalescing on at every boot** for Samsung, Kioxia, and Micron drives. Clearing feature 8 once is not enough if that unit is still enabled — stop/disable (or mask) the service, then set `-V 0`. NVIDIA documents the service and the enable/disable helpers in the [DGX OS 8 additional-software guide](https://docs.nvidia.com/dgx/dgx-os-8-user-guide/latest/additional_software.html) (package notes in the [software stack appendix](https://docs.nvidia.com/dgx/dgx-os-8-user-guide/latest/appendix_c_dgx_software_stack.html)). The [Grace performance tuning guide](https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/optimizing-io.html) shows the same `0x107` recipe as the intended “coalesce to cut interrupt overhead” setting — the QD1 latency cost is the other side of that trade.

### Spark / token generation (outbound pitch)

Nobody can promise this will help **your** token-generation path — those stacks vary a lot, and many never miss to SSD while decoding. What was unclear is now easy to try: DGX OS quietly turns on NVMe interrupt coalescing at boot (`nvidia-nvme-interrupt-coalescing.service` → feature 8 = `0x107`), and at queue depth 1 that can **more than double random-read speed**. Mask the unit, `nvme set-feature … -f 8 -V 0`, and A/B on your own stack. As far as a guess goes for tokens: you might see some **tail latency** reduction when generation waits on a lonely SSD read — not a claim about average tokens/sec. Model load and high-QD sequential I/O usually will not move.

The **evanwtf/local-llm** project already measured the storage side on Spark (same drive family `MZALC4T0HBL1` / `NXHB202Q`): fio QD1 4 K random roughly **~200 µs → ~55 µs** median with coalescing off; QD32 and large sequential barely changed. They masked the service so upgrades could not flip it back. No link here (third-party hosting tripped a Safe Browsing warning); credit to that project for the fio A/B and the mask-the-unit note.

## Evidence (court / DGX Spark)

Host notes (power sensors, NIC EEE / ASPM): [NVIDIA DGX Spark]({{ '/platform/dgx-spark/' | relative_url }}).

Samsung `MZALC4T0HBL1`, firmware `NXHB202Q`, with coalescing active (DGX OS boot service / shipped default). Twilight’s Kingston had it off. Same Postgres durable face, same select-scatter-64 / OSM shape:

![DGX Spark: NVMe interrupt coalescing on vs off (TPS) — select-scatter-64 and OSM Relations]({{ '/images/nvme-coalescing-compare.png' | relative_url }})

| | Coalescing on (shipped) | Coalescing off |
|--|-------------------------|----------------|
| select-scatter-64 cold c=1 | ~35 TPS | ~100 TPS |
| select-scatter-64 hot c=32 | ~1870 TPS | ~3880 TPS |
| OSM Relations | 13251 s (~1104/s) | 7614 s (~1921/s) |

Relations **~1.75×** faster (overall wall clock also improved; not charted here). Court still trails a similar-class x86 host by about 2× on Relations — not parity, and not claimed to be. Isolation ruled out AIO method, `effective_io_concurrency`, and IRQ pinning as the main lever.

Regenerate: `MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/nvme-coalescing-compare.py`

Full write-up: [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}).
