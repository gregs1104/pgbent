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

- [Farm disks]({{ '/platform/disks/' | relative_url }}) — PCIe generation and rated sequential speeds for drives used on the farm
- [Linux standard OS tuning]({{ '/platform/linux/' | relative_url }}) — what `pgbent_tune` applies after every boot, and why
  - [dirty memory]({{ '/platform/linux-dirty-memory/' | relative_url }}) and [pdflush / writeback]({{ '/platform/linux-pdflush/' | relative_url }})
- [NVIDIA DGX Spark]({{ '/platform/dgx-spark/' | relative_url }}) platform review — court: coalescing + mixed-core SELECT grid, power (`spark_hwmon` / spbm), NIC EEE / ASPM
  - [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }})
- [macOS LaunchAgent I/O class]({{ '/platform/darwin/' | relative_url }}) — Homebrew `brew services` utility clamp

The full ARM miss isolation case (select-scatter-64, Relations, court vs twilight vs Abbey) is the [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}) study.
