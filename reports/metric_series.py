"""Multi-line avg/max time series from test_metrics_data.

metview.py still emits one PNG per metric and plots only the average.
This helper is the first overlay of Average vs Maximum on a shared axis —
the pattern stacked CPU/memory groups and webreport setting-grid overlays
will reuse. Minute buckets of 1-second samples keep the peak line honest:
the max in each minute is a real collector reading, not a smoothed guess.
"""

from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter

AVG_COLOR = "#4c78a8"
MAX_COLOR = "#e4572e"
_SAFE_SERVER = re.compile(r"^[A-Za-z0-9._-]+$")


def fetch_copy(conn: str, sql: str) -> pd.DataFrame:
    proc = subprocess.run(
        ["psql", conn, "-v", "ON_ERROR_STOP=1", "-c", f"COPY ({sql}) TO STDOUT WITH CSV HEADER"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"psql failed ({proc.returncode})")
    if not proc.stdout.strip():
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(proc.stdout))


def _ident_server(server: str) -> str:
    if not _SAFE_SERVER.match(server):
        raise SystemExit(f"Unsafe server name: {server!r}")
    return server


def _ident_test(test: int | str) -> int:
    return int(test)


def pick_data_disk(conn: str, server: str, test: int | str) -> tuple[str, str]:
    """Busiest volume and how it was captured.

    Linux iostat is a read/write pair (`*_rMB/s` + `*_wMB/s`). Darwin iostat
    is a single combined series (`diskN_MB/s`) with no r/w split.
    """
    server = _ident_server(server)
    test = _ident_test(test)
    sql = f"""
SELECT metric
FROM test_metrics_data
WHERE server = '{server}' AND test = {test}
  AND (metric LIKE '%wMB/s' OR metric ~ '^disk[0-9]+_MB/s$')
GROUP BY 1
ORDER BY max(value) DESC
LIMIT 1
"""
    df = fetch_copy(conn, sql)
    if df.empty:
        return "", ""
    metric = str(df.iloc[0]["metric"])
    if metric.endswith("_wMB/s"):
        return metric[: -len("_wMB/s")], "rw"
    if metric.endswith("_MB/s"):
        return metric[: -len("_MB/s")], "combined"
    return metric, "combined"


def fetch_disk_avg_max(
    conn: str, server: str, test: int | str, dbagg: str = "minute"
) -> tuple[pd.DataFrame, str, str]:
    """Disk MB/s on the busiest volume: per-bucket avg and 1s max.

    Returns (frame, disk_label, mode) where mode is ``rw`` or ``combined``.
    """
    server = _ident_server(server)
    test = _ident_test(test)
    disk, mode = pick_data_disk(conn, server, test)
    if not disk:
        return pd.DataFrame(), "", ""
    if not _SAFE_SERVER.match(disk):
        raise SystemExit(f"Unsafe disk name: {disk!r}")
    if dbagg not in ("second", "minute", "hour"):
        raise SystemExit(f"Unsupported dbagg: {dbagg!r}")
    if mode == "combined":
        metric_pred = f"d.metric = '{disk}_MB/s'"
        mbps_expr = "max(d.value)"
    else:
        metric_pred = f"(d.metric = '{disk}_rMB/s' OR d.metric = '{disk}_wMB/s')"
        mbps_expr = "sum(d.value)"
    sql = f"""
SELECT
  extract(epoch from date_trunc('{dbagg}', sec.collected) - t.start_time) / 3600.0 AS hours,
  avg(sec.mbps) AS avg,
  max(sec.mbps) AS max
FROM (
  SELECT d.collected, {mbps_expr} AS mbps
  FROM test_metrics_data d
  WHERE d.server = '{server}' AND d.test = {test} AND {metric_pred}
  GROUP BY d.collected
) sec
JOIN tests t ON t.server = '{server}' AND t.test = {test}
GROUP BY date_trunc('{dbagg}', sec.collected), t.start_time
ORDER BY 1
"""
    return fetch_copy(conn, sql), disk, mode


def fetch_power_avg_max(
    conn: str, server: str, test: int | str, dbagg: str = "minute"
) -> pd.DataFrame:
    """Package watts: per-bucket average and 1-second maximum."""
    server = _ident_server(server)
    test = _ident_test(test)
    if dbagg not in ("second", "minute", "hour"):
        raise SystemExit(f"Unsupported dbagg: {dbagg!r}")
    sql = f"""
SELECT
  extract(epoch from date_trunc('{dbagg}', d.collected) - t.start_time) / 3600.0 AS hours,
  avg(CASE WHEN d.metric = 'Combined_Power_mW' THEN d.value * 0.001 ELSE d.value END) AS avg,
  max(CASE WHEN d.metric = 'Combined_Power_mW' THEN d.value * 0.001 ELSE d.value END) AS max
FROM test_metrics_data d
JOIN tests t ON t.server = d.server AND t.test = d.test
WHERE d.server = '{server}' AND d.test = {test}
  AND d.metric IN ('PkgWatt', 'Combined_Power_mW', 'soc_pkg_power2_input')
GROUP BY date_trunc('{dbagg}', d.collected), t.start_time
ORDER BY 1
"""
    return fetch_copy(conn, sql)


def plot_avg_max(
    df: pd.DataFrame,
    output: Path,
    *,
    title: str,
    ylabel: str,
    avg_legend: str,
    max_legend: str,
    legend_loc: str = "upper left",
    show: bool = False,
) -> None:
    """Two lines on one axes: Average and Maximum. Shared x is elapsed hours."""
    if df.empty:
        raise SystemExit(f"No series to plot for {output}")
    fig, ax = plt.subplots(figsize=(10, 4.2))
    hours = pd.to_numeric(df["hours"], errors="coerce")
    avg = pd.to_numeric(df["avg"], errors="coerce")
    mx = pd.to_numeric(df["max"], errors="coerce")
    ax.fill_between(hours, avg, mx, color=MAX_COLOR, alpha=0.12, linewidth=0)
    ax.plot(hours, avg, color=AVG_COLOR, linewidth=2.2, label=avg_legend)
    ax.plot(hours, mx, color=MAX_COLOR, linewidth=1.4, label=max_legend)
    ax.set_xlabel("Hours")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xlim(left=0)
    peak = float(mx.max())
    ax.set_ylim(0, peak * 1.08 if peak > 0 else 1)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.tick_params(which="major", length=6)
    ax.tick_params(which="minor", length=3)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.grid(True, which="minor", linestyle=":", alpha=0.25)
    ax.legend(loc=legend_loc, framealpha=0.92, fontsize=14)
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(df)} buckets)")
    if show:
        plt.show()
    plt.close(fig)


def legend_avg_max(df: pd.DataFrame, unit: str, digits: int = 0) -> tuple[str, str]:
    avg = float(pd.to_numeric(df["avg"]).mean())
    peak = float(pd.to_numeric(df["max"]).max())
    if digits == 0:
        return f"Average ({avg:.0f} {unit})", f"Maximum ({peak:.0f} {unit})"
    return f"Average ({avg:.{digits}f} {unit})", f"Maximum ({peak:.{digits}f} {unit})"
