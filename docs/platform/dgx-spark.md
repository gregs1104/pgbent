---
layout: home
title: NVIDIA DGX Spark
permalink: /platform/dgx-spark/
parent: Platform guides
nav_order: 6
---

# NVIDIA DGX Spark

Lab host **court**: NVIDIA DGX Spark (board **P4242**), Grace CPU, DGX OS (Ubuntu-derived). This page is the Spark-specific checklist. Two platform oddities showed up here — different layers, both farm catches:

1. **[NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }})** — I/O: DGX OS turns feature 8 on at boot; clearing it was ~**1.75×** on OSM Relations.
2. **SELECT client grid / mixed-core off-ratio** — CPU scheduling: a power-of-two-only ladder undersells the box (dip at **16**; fair points at **20** / **40**). See below.

Also apply the shared [Linux standard tuning]({{ '/platform/linux/' | relative_url }}) (`pgbent_tune`: governor, readahead, coalescing clear, TRIM). Set `DISKLIST="nvme0n1"` in `config` or `iostat.csv` stays empty.

## Package power measurement

NVIDIA does not ship a convenient package-watt path that pgbent already knew. Court uses the open **[spark_hwmon](https://github.com/antheas/spark_hwmon)** kernel module (`spbm`), which exports ACPI hwmon rails that `lm-sensors` can read.

Collection (when `SUDODATA=1` and `pgbent_powermon` is installed with NOPASSWD):

```bash
# util/pgbent_powermon on aarch64 — once spbm is loaded:
sensors -u "spbm-*"
```

That 1 Hz stream lands in `power.log`. `metrics2csv` detects the sensors format and runs `util/power-sensors-parse` into `power.csv`. The rails that feed OSM / SELECT power charts are:

| sensors name | role |
|--------------|------|
| `soc_pkg_power2_input` | SoC / package watts (primary compare) |
| `sys_total_power1_input` | System total watts |

Confirm the module is up with `lsmod | grep spbm` and a sample `sensors -u "spbm-*"`. Without it, Grace package energy on the leaderboards is missing — not estimated from somewhere else.

## Network power management

Court’s 10 Gb NIC is Realtek on `enP7s7`. Early on, a **network power-management hang** made the box look dead on the wire. Steady traffic kept it honest — as long as something kept hitting the server, it often stayed reachable. Leaving it **idle for days** is when it found the bad sleep spots. Two runtime knobs fixed that (lab notes / shell history):

```bash
# Energy Efficient Ethernet — disable on the Spark 10Gb port
sudo ethtool --set-eee enP7s7 eee off
ethtool --show-eee enP7s7

# Prefer performance PCIe ASPM policy (avoid link power-down surprises)
echo performance | sudo tee /sys/module/pcie_aspm/parameters/policy
cat /sys/module/pcie_aspm/parameters/policy
```

Neither is durable across reboot unless you add an if-up / systemd unit. After a cold boot, re-check: EEE often returns to **enabled** (may sit **inactive** if the link partner does not advertise EEE), and `pcie_aspm` policy may show `[default]` again. Link-level ASPM on the NIC and NVMe can still read `ASPM Disabled` in `lspci -vv` while the module policy drifts — verify both if multi-day idle hangs return.

Debian `watchdog` ping-to-gateway was left over from that hang era. Keep it **off** on this lab LAN (`run_watchdog=0`); a gateway ARP blip is not a hung Spark. See the farm 10 Gb / ARP notes separately — do not treat missed pings as a reason to reboot.

## SELECT client counts (mixed-core) — second oddity

Court is **20** CPUs: 10× Cortex-X925 + 10× Cortex-A725. Separate from coalescing: a pure power-of-two client ladder (`… 8 16 32 64`) can hit a **classic off-ratio dip** on mixed-core hardware — the published sockets-prepared curve dipped at **16** for that reason. `pgsysinfo` already merges `nproc`, `2×`, and `4×` into `SETCLIENTS` (here **20 / 40 / 80**); the published SELECT ladder stays in the **1–64** window, so the fair fill points are **20** and **40** (set **26**; **10** / **16** re-check in set **27**). Treat a lonely 16-client valley as a scheduling-ratio artifact until the `nproc` points are on the chart — keep the **highest** TPS when piling repeats onto a doubtful cell.

Intel hybrid and Apple mixes show a milder version of the same edge; more mature PG-on-Linux platforms tend to sand it over. Spark is still a relatively raw CPU platform for this workload, so the dip stayed visible enough to catch.

## See also

- [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) — feature 8 / NVIDIA boot service / measured Relations win
- [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}) — full isolation write-up (court vs twilight vs Abbey)
- [Linux standard tuning]({{ '/platform/linux/' | relative_url }}) — post-boot checklist including coalescing clear
- [SELECT performance vs power]({{ '/leaderboards/select-performance-power/' | relative_url }}) — platform sockets/prepared ladder (notes the 16-client dip)
