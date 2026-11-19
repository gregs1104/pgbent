---
layout: home
title: Platform guides
permalink: /platform/
nav_order: 21
has_children: true
---

# Platform guides

The [Tuning Model]({{ '/model/' | relative_url }}) covers PostgreSQL GUCs that respond predictably to pgbent workloads. **Platform guides** cover the layer underneath: OS I/O class, device read-ahead, NVMe firmware defaults, and how the server process is started. Those knobs are easy to leave at desktop or SAN defaults and then blame on Postgres.

Think of vendor NAS runbooks (EMC and friends) that publish database-oriented storage settings — except here the evidence is public, measured on named hosts, with scripts you can re-run. Isolation write-ups that feed this section live under [Studies]({{ '/studies/' | relative_url }}).

## Start here

- [Linux standard tuning]({{ '/platform/linux/' | relative_url }}) — what `pgbent_tune` applies after every boot, and why
- [Linux pdflush / writeback]({{ '/platform/linux-pdflush/' | relative_url }}) — page-cache writeback theory (historical pdflush → flusher threads)
- [Linux dirty memory]({{ '/platform/linux-dirty-memory/' | relative_url }}) — measured impact of `vm.dirty_*` on OSM load
- [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) — free latency win when OEM firmware left coalescing on
- [macOS / Darwin]({{ '/platform/darwin/' | relative_url }}) — Homebrew `brew services` LaunchAgent I/O clamp
- [NVIDIA DGX Spark]({{ '/platform/dgx-spark/' | relative_url }}) — court: coalescing + mixed-core SELECT grid (two oddities), power (`spark_hwmon` / spbm), NIC EEE / ASPM

The full ARM miss isolation case (select-scatter-64, Relations, court vs twilight vs Abbey) is the [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}) study.
