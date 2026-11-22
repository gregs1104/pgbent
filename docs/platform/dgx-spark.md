---
layout: home
title: NVIDIA DGX Spark
permalink: /platform/dgx-spark/
parent: Platform guides
nav_order: 2
has_children: true
---

# NVIDIA DGX Spark

Lab host **court**: NVIDIA DGX Spark (board **P4242**), Grace CPU, DGX OS (Ubuntu-derived). This page is the Spark-specific checklist. Two platform oddities showed up here — different layers, both farm catches:

1. **[NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }})** — I/O: DGX OS turns feature 8 on at boot; clearing it was ~**1.75×** on OSM Relations.
2. **SELECT client grid / mixed-core off-ratio** — CPU scheduling: a power-of-two-only ladder undersells the box (and mildly favors AMD chips that land on **16** / **32**); fair points at **20** / **40**. See below.

Also apply the shared [Linux standard OS tuning]({{ '/platform/linux/' | relative_url }}) (`pgbent_tune`: governor, readahead, coalescing clear, TRIM). Set `DISKLIST="nvme0n1"` in `config` or `iostat.csv` stays empty.

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

Court is **20** CPUs: 10× Cortex-X925 + 10× Cortex-A725. Separate from coalescing: a pure power-of-two client ladder (`… 8 16 32 64`) is not a fair cross-vendor grid on this farm — it gives a **mild advantage to the current AMD set** (9950X hits **16** / **32** cleanly) and can hit a **classic off-ratio dip** on mixed-core hardware. Filled sockets-prepared points (sets **26** / **27**, highest TPS): **~485k** at **10** and **16**, **~960k** at **20** (`nproc`), **~533k** at **32**, **~547k** at **40**. The cliff is matching the core count, not “16 is mysteriously slow.” `pgsysinfo` already merges `nproc`, `2×`, and `4×` into `SETCLIENTS` (here **20 / 40 / 80**); the published SELECT ladder stays in the **1–64** window with fair fills at **10 / 20 / 40**.

Twilight’s **13600K** shows a milder version of the same edge. Once other pending farm work finishes, its SELECT grid will add the `pgsysinfo` thread points (**20** / **40** / **80**) so pgbench can pin better to cores and threads — the same fairness fix court needed. Apple is milder still; more mature PG-on-Linux platforms tend to sand it over. After the **14900K** left the farm, AMD chips moved onto the top of the SELECT board. Spark is still a relatively raw CPU platform for this workload, so the dip stayed visible enough to catch.

## Residual vs x86 (clock)

After coalescing is off and the client grid is fair, court still sits behind the farm’s fast x86 boxes on SELECT / Relations-shaped work. The Grace parts here run around **2.8 GHz**; the desktop x86 SKUs sit in **~5.7 GHz** territory. That is roughly a **2×** clock gap, and the remaining platform gap looks **proportional to that** — a working hypothesis, not a claim that every residual is pure MHz. Full x86 parity is not expected on this clock envelope.

## See also

- [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) — feature 8 / NVIDIA boot service / measured Relations win
- [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}) — full isolation write-up (court vs twilight vs Abbey)
- [Linux standard OS tuning]({{ '/platform/linux/' | relative_url }}) — post-boot checklist including coalescing clear
- [SELECT performance vs power]({{ '/leaderboards/select-performance-power/' | relative_url }}) — platform sockets/prepared ladder (notes the 16-client dip)
