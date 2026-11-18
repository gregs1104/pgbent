---
layout: home
title: NVIDIA DGX Spark
permalink: /platform/dgx-spark/
parent: Platform guides
nav_order: 6
---

# NVIDIA DGX Spark

Lab host **court**: NVIDIA DGX Spark (board **P4242**), Grace CPU, DGX OS (Ubuntu-derived). This page is the Spark-specific checklist. The biggest I/O footgun on this box is separate:

→ **[NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }})** — DGX OS turns feature 8 on at boot; clearing it was ~**1.75×** on OSM Relations here.

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

## See also

- [NVMe interrupt coalescing]({{ '/platform/nvme-coalescing/' | relative_url }}) — feature 8 / NVIDIA boot service / measured Relations win
- [ARM random read vs x86]({{ '/studies/arm-random-read-vs-x86/' | relative_url }}) — full isolation write-up (court vs twilight vs Abbey)
- [Linux standard tuning]({{ '/platform/linux/' | relative_url }}) — post-boot checklist including coalescing clear
