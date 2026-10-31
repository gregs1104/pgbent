#!/usr/bin/env python3
"""
Graph OSM leaderboard results.

Default: read a release's static snapshot (PG18) and write the matching PNG.

`--from-db` runs `reports/osm-leaderboard.sql` against the results database,
writes the ranked table into `docs/leaderboards.md`, and writes disk/power
traces, score-vs-joules, and the system comparison into
`docs/leaderboards/osm-performance-power.md`. That is the public-page path;
it does not go through Streamlit.

Usage:
  python3 reports/osm-leaderboard.py
  python3 reports/osm-leaderboard.py --pg 19
  python3 reports/osm-leaderboard.py --from-db
"""

from __future__ import annotations

import argparse
import io
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table
from pg18_style import (
    BAR_LABEL_FONTSIZE,
    LEADERBOARD_LEGEND_FONTSIZE,
    LEADERBOARD_Y_LABEL_FONTSIZE,
    use_pg18_style,
)
from release_paths import REPO_ROOT, add_pg_argument, image_path, snapshot_path
from metric_series import fetch_disk_avg_max, fetch_power_avg_max, legend_avg_max, plot_avg_max
from label_layout import LabelOffset, place_point_labels

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"
TOTAL_COLOR = "#f4a261"
ENERGY_COLOR = "#2a9d8f"
BAR_LABEL_INSIDE_COLOR = "#ffffff"
BAR_LABEL_OUTSIDE_COLOR = "#333333"
SCATTER_MARKER_SIZE = 90
LABEL_LINESPACING = 1.7
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "osm-leaderboard.sql"
LEADERBOARD_PAGE = REPO_ROOT / "docs" / "leaderboards.md"
POWER_PAGE = REPO_ROOT / "docs" / "leaderboards" / "osm-performance-power.md"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard.png"
DISK_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-disk.png"
POWER_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-power.png"
EFF_DISK_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-efficiency-disk.png"
EFF_POWER_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-efficiency-power.png"
NVIDIA_DISK_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-nvidia-disk.png"
NVIDIA_POWER_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-nvidia-power.png"
JOULES_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-joules.png"
COMPARE_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard-compare.png"
TABLE_BEGIN = "<!-- osm-leaderboard-table:begin -->"
TABLE_END = "<!-- osm-leaderboard-table:end -->"
TRACE_BEGIN = "<!-- osm-leaderboard-traces:begin -->"
TRACE_END = "<!-- osm-leaderboard-traces:end -->"
JOULES_BEGIN = "<!-- osm-leaderboard-joules:begin -->"
JOULES_END = "<!-- osm-leaderboard-joules:end -->"
COMPARE_BEGIN = "<!-- osm-leaderboard-compare:begin -->"
COMPARE_END = "<!-- osm-leaderboard-compare:end -->"
HIDDEN_TABLE_COLS = ("server", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot OSM leaderboard")
    add_pg_argument(parser)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Run osm-leaderboard.sql and populate the leaderboard and power pages",
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--page", type=Path, default=LEADERBOARD_PAGE)
    parser.add_argument("--power-page", type=Path, default=POWER_PAGE)
    parser.add_argument("--no-page", action="store_true", help="Skip writing the Markdown pages")
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    args = parser.parse_args()
    if args.from_db:
        args.output = args.output or PUBLIC_IMAGE
    else:
        args.snapshot = args.snapshot or snapshot_path(args.pg, "osm-leaderboard")
        args.output = args.output or image_path(args.pg, "osm-leaderboard")
    return args


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def config_label(row: pd.Series) -> str:
    """Two-line label: cpu, then memory - disk."""
    mem = int(row["mem_gb"])
    disk = str(row["disk"]).strip()
    return f"{row['cpu']}\n{mem}GB - {disk}"


def prepare_leaderboard_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in (
        "mem_gb",
        "overall_kips",
        "score_kips",
        "index_kips",
        "rel_ps",
        "ver",
        "hours",
        "max_wal_gb",
        "kj",
    ):
        if col in df.columns:
            df[col] = numeric(df[col])
    df["disk"] = df["disk"].str.strip()
    df = df[df["conn"].astype(str).str.strip().str.lower() == "host"]

    rank_cols = (
        ["score_kips", "overall_kips", "index_kips"]
        if "score_kips" in df.columns
        else ["overall_kips", "index_kips"]
    )
    best = (
        df.sort_values(rank_cols, ascending=False)
        .groupby(["cpu", "mem_gb", "disk"], as_index=False)
        .first()
    )
    best["label"] = best.apply(config_label, axis=1)
    sort_col = "score_kips" if "score_kips" in best.columns else "overall_kips"
    return best.sort_values(sort_col, ascending=True).reset_index(drop=True)


def plain_axis(ax, y: bool = False, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def _marker_x_gap(gap: float = 12) -> float:
    return math.sqrt(SCATTER_MARKER_SIZE / math.pi) + gap


JOULES_LABEL_OVERRIDES = {
    # ~128 Gi board: both x86 peaks sit high-right — label left of marker.
    "i5-13600K": LabelOffset(-_marker_x_gap(), 0, ha="right", va="center"),
    "R9 9950X": LabelOffset(-_marker_x_gap(), 0, ha="right", va="center"),
    "Apple M4 Max Studio": LabelOffset(0, 12, ha="center", va="bottom"),
    "NVIDIA P4242": LabelOffset(_marker_x_gap(), 0, ha="left", va="center"),
}


def cpu_color(cpu: str) -> str:
    name = str(cpu)
    if name.startswith("NVIDIA"):
        return "#76B900"
    if name[:1] == "A":
        return "#000000"
    if name[:1] == "i":
        return "#0071C5"
    if name[:1] == "R":
        return "#ED1C24"
    return "#333333"


def roughly_128gb_ram(df: pd.DataFrame) -> pd.DataFrame:
    """Score-vs-energy board: keep ~128 Gi class, drop fat twilight 188 Gi cells."""
    if "mem_gb" not in df.columns:
        return df
    mem = pd.to_numeric(df["mem_gb"], errors="coerce")
    return df.loc[mem.isna() | (mem <= 140)].copy()


def plot_score_vs_joules(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    """Tiny speed-vs-energy scatter: one point per machine, score against kJ."""
    pts = roughly_128gb_ram(df).dropna(subset=["kj", "score_kips"])
    if pts.empty:
        raise SystemExit("No package_joules on leaderboard rows")
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    colors = [cpu_color(c) for c in pts["cpu"]]
    ax.scatter(pts["kj"], pts["score_kips"], s=SCATTER_MARKER_SIZE, c=colors, zorder=3)
    xmax = float(pts["kj"].max())
    ymax = float(pts["score_kips"].max())
    # Slight left pad so a centered "Apple M4 Max Studio" clears the spine.
    ax.set_xlim(-xmax * 0.04, xmax * 1.14)
    ax.set_ylim(0, ymax * 1.22)
    ax.set_xlabel("Package energy (kJ)")
    ax.set_ylabel("OSM score")
    ax.set_title("OSM Score vs Total Power Use")
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.tick_params(which="major", length=6)
    ax.tick_params(which="minor", length=3)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.grid(True, which="minor", linestyle=":", alpha=0.25)
    plain_axis(ax, y=True)
    fig.tight_layout()
    place_point_labels(
        ax,
        pts["cpu"].astype(str),
        pts["kj"],
        pts["score_kips"],
        colors,
        16,
        overrides=JOULES_LABEL_OVERRIDES,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(pts)} systems)")
    if show:
        plt.show()
    plt.close(fig)


def joules_takeaway(df: pd.DataFrame) -> str:
    """Fastest x86 vs cheapest ARM on the ~128 Gi one-point-per-machine board."""
    pts = roughly_128gb_ram(df).dropna(subset=["kj", "score_kips"])
    if pts.empty:
        return ""
    cpu = pts["cpu"].astype(str)
    x86 = pts[cpu.str.match(r"^[Ri]")]
    apple = pts[cpu.str.contains("Apple", case=False, regex=False)]
    nvidia = pts[cpu.str.contains("NVIDIA", case=False, regex=False)]
    if x86.empty or apple.empty:
        return ""
    fast = x86.sort_values("score_kips", ascending=False).iloc[0]
    arm = apple.sort_values("kj", ascending=True).iloc[0]
    score_x = float(fast["score_kips"]) / float(arm["score_kips"])
    joule_x = float(fast["kj"]) / float(arm["kj"])
    bits = [
        "You can potentially triple the score running on the fastest x86 instead of ARM, "
        "but it costs 4–5× as much energy to juice up the processors to do it. "
        f"**{fast['cpu']}** scores **{format_markdown_cell(fast['score_kips'])}** at "
        f"**{format_markdown_cell(fast['kj'])} kJ**; **{arm['cpu']}** scores "
        f"**{format_markdown_cell(arm['score_kips'])}** at "
        f"**{format_markdown_cell(arm['kj'])} kJ** "
        f"(**{score_x:.1f}×** score, **{joule_x:.1f}×** joules)."
    ]
    if not nvidia.empty:
        nv = nvidia.sort_values("score_kips", ascending=False).iloc[0]
        nv_x = float(fast["score_kips"]) / float(nv["score_kips"])
        bits.append(
            f"Versus NVIDIA Grace the score ratio is **{nv_x:.1f}×** "
            f"({format_markdown_cell(fast['score_kips'])} vs "
            f"{format_markdown_cell(nv['score_kips'])})."
        )
    return " ".join(bits)


def joules_markdown(df: pd.DataFrame) -> str:
    takeaway = joules_takeaway(df)
    body = (
        "Speed vs energy for the best run on each machine at ~128GB RAM. **Score** is "
        "OSM kNodes/s; **kJ** is total package energy (joules, shown as kilojoules) from "
        "the 1-second power integral over the test window. NVIDIA DGX Spark package watts "
        "come from the open [spark_hwmon](https://github.com/antheas/spark_hwmon) module, "
        "not an NVIDIA-shipped sensor path."
    )
    if takeaway:
        body = f"{body}\n\n{takeaway}"
    return (
        f"{JOULES_BEGIN}\n\n"
        "![OSM score vs package energy]"
        "({{ '/images/osm-leaderboard-joules.png' | relative_url }})\n\n"
        f"{body}\n\n"
        f"{JOULES_END}"
    )


def compare_markdown() -> str:
    return (
        f"{COMPARE_BEGIN}\n\n"
        "One chart for the same best-score run on each machine, sorted by OSM score. "
        "Bar length is relative to the lead system, on that metric "
        "(**100%** = that system's value). "
        "Labels are the raw values. A longer **kJ** bar means more energy used, not more efficiency.\n\n"
        "![osm2pgsql Load Time - System Comparison]"
        "({{ '/images/osm-leaderboard-compare.png' | relative_url }})\n\n"
        f"{COMPARE_END}"
    )


def _contrast_text_color(hex_color: str) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return BAR_LABEL_INSIDE_COLOR
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return BAR_LABEL_INSIDE_COLOR if luminance < 0.55 else BAR_LABEL_OUTSIDE_COLOR


def _text_width_data(ax, text: str, fontsize: float, renderer) -> float:
    probe = ax.text(0, 0, text, fontsize=fontsize, alpha=0.0)
    ax.figure.canvas.draw()
    bbox = probe.get_window_extent(renderer)
    probe.remove()
    x0, _ = ax.transData.inverted().transform((bbox.x0, bbox.y0))
    x1, _ = ax.transData.inverted().transform((bbox.x1, bbox.y1))
    return abs(x1 - x0)


def _format_hours(hours: float | None) -> str:
    if hours is None or not math.isfinite(hours) or hours <= 0:
        return ""
    rounded = round(hours, 2)
    if abs(rounded - round(rounded, 1)) < 1e-9:
        return f"{rounded:.1f}h"
    return f"{rounded:.2f}h"


def _index_phase_hours(
    hours: float, overall_kips: float, index_kips: float
) -> float | None:
    """Wall-clock of polygon+line+point+roads, inverted from index_kips.

    index_kips is node_count/4 over the four index-table seconds, so
    index_hours = hours * overall_kips / (4 * index_kips).
    """
    if any(
        not math.isfinite(value) or value <= 0
        for value in (hours, overall_kips, index_kips)
    ):
        return None
    return hours * overall_kips / (4.0 * index_kips)


def _label_barh_values(
    ax,
    items: list[tuple],
    fontsize: float = BAR_LABEL_FONTSIZE,
) -> None:
    """Inside-bar contrast labels when they fit; otherwise outside-right.

    Optional 5th item is a hours suffix, always drawn to the right of the bar
    (or combined with an outside rate label so the two do not stack).
    """
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    xmax = max(item[1] for item in items)
    pad = max(xmax * 0.02, 2)
    inner_pad = max(xmax * 0.015, 1.5)
    max_x = xmax
    for item in items:
        yi, width, color, label = item[:4]
        hours = item[4] if len(item) > 4 else ""
        text_width = _text_width_data(ax, label, fontsize, renderer)
        if text_width + inner_pad * 2 <= width:
            ax.text(
                width - inner_pad,
                yi,
                label,
                va="center",
                ha="right",
                fontsize=fontsize,
                color=_contrast_text_color(color),
                clip_on=True,
            )
            max_x = max(max_x, width)
            if hours:
                hx = width + pad
                hour_width = _text_width_data(ax, hours, fontsize, renderer)
                ax.text(
                    hx,
                    yi,
                    hours,
                    va="center",
                    ha="left",
                    fontsize=fontsize,
                    color=BAR_LABEL_OUTSIDE_COLOR,
                    clip_on=True,
                )
                max_x = max(max_x, hx + hour_width)
        else:
            outside = f"{label} · {hours}" if hours else label
            x = width + pad
            outside_width = _text_width_data(ax, outside, fontsize, renderer)
            ax.text(
                x,
                yi,
                outside,
                va="center",
                ha="left",
                fontsize=fontsize,
                color=BAR_LABEL_OUTSIDE_COLOR,
                clip_on=True,
            )
            max_x = max(max_x, x + outside_width)
    ax.set_xlim(0, max_x + pad)


def _pct_of_leader(series: pd.Series, leader_value: float) -> pd.Series:
    if leader_value is None or leader_value <= 0:
        return series * 0
    return series / leader_value * 100.0


def plot_system_compare(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    plot_df = df.dropna(subset=["score_kips", "rel_ps", "kj"]).copy()
    plot_df = plot_df.sort_values("score_kips", ascending=True).reset_index(drop=True)
    if plot_df.empty:
        raise SystemExit("No rows with score, relations/s, and kJ for the comparison chart")

    leader = plot_df.loc[plot_df["score_kips"].idxmax()]
    score_pct = _pct_of_leader(plot_df["score_kips"], float(leader["score_kips"]))
    rel_pct = _pct_of_leader(plot_df["rel_ps"], float(leader["rel_ps"]))
    kj_pct = _pct_of_leader(plot_df["kj"], float(leader["kj"]))
    n = len(plot_df)
    y = list(range(n))
    bar_h = 0.24
    series = (
        (score_pct, [i + bar_h for i in y], NODES_COLOR, "OSM score", plot_df["score_kips"], "{:,.0f}"),
        (rel_pct, y, INDEX_COLOR, "Relations/s", plot_df["rel_ps"], "{:,.0f}/s"),
        (kj_pct, [i - bar_h for i in y], ENERGY_COLOR, "kJ used", plot_df["kj"], "{:,.0f} kJ"),
    )

    fig, ax = plt.subplots(figsize=(11, max(5.5, 1.35 * n + 1.6)))
    items: list[tuple[float, float, str, str]] = []
    for widths, ys, color, label, raw, fmt in series:
        ax.barh(ys, widths, height=bar_h, color=color, label=label)
        for yi, width, value in zip(ys, widths, raw):
            items.append((yi, float(width), color, fmt.format(float(value))))

    ax.set_yticks(y)
    ax.set_yticklabels(
        plot_df["label"],
        fontsize=LEADERBOARD_Y_LABEL_FONTSIZE,
        linespacing=LABEL_LINESPACING,
    )
    ax.set_xlabel("% Relative to the lead system, on that metric")
    ax.set_title("osm2pgsql Load Time - System Comparison")
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.grid(True, axis="x", which="major", linestyle="--", alpha=0.4)
    ax.grid(True, axis="x", which="minor", linestyle=":", alpha=0.25)
    plain_axis(ax)

    _label_barh_values(ax, items)
    ax.legend(
        loc="lower right",
        ncol=1,
        fontsize=LEADERBOARD_LEGEND_FONTSIZE,
        framealpha=0.92,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({n} systems)")
    if show:
        plt.show()
    plt.close(fig)


def plot_leaderboard(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    n = len(df)
    y = list(range(n))
    bar_h = 0.24
    # PG18 snapshot predates score_kips; live board has all three.
    series: list[tuple] = []
    if "score_kips" in df.columns:
        series.append(
            (df["score_kips"], [i + bar_h for i in y], NODES_COLOR, "OSM score (kN/s)", None)
        )
    series.extend(
        (
            (df["overall_kips"], y, TOTAL_COLOR, "Total (kN/s)", "total"),
            (df["index_kips"], [i - bar_h for i in y], INDEX_COLOR, "Index (kN/s)", "index"),
        )
    )

    fig, ax = plt.subplots(figsize=(10, max(6, 1.15 * n + 1.8)))
    items: list[tuple] = []
    for widths, ys, color, label, phase in series:
        ax.barh(ys, widths, height=bar_h, color=color, label=label)
        for i, (yi, width) in enumerate(zip(ys, widths)):
            item: tuple = (yi, float(width), color, f"{float(width):,.0f}")
            if phase == "total" and "hours" in df.columns:
                hours_text = _format_hours(float(df.iloc[i]["hours"]))
                if hours_text:
                    item = (*item, hours_text)
            elif phase == "index" and "hours" in df.columns:
                index_hours = _index_phase_hours(
                    float(df.iloc[i]["hours"]),
                    float(df.iloc[i]["overall_kips"]),
                    float(df.iloc[i]["index_kips"]),
                )
                hours_text = _format_hours(index_hours)
                if hours_text:
                    item = (*item, hours_text)
            items.append(item)

    ax.set_yticks(y)
    ax.set_yticklabels(
        df["label"],
        fontsize=LEADERBOARD_Y_LABEL_FONTSIZE,
        linespacing=LABEL_LINESPACING,
    )
    ax.set_xlabel("Throughput (kNodes/s)")
    ax.set_title("PostgreSQL OSM load leaderboard")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    plain_axis(ax)
    _label_barh_values(ax, items)
    ax.legend(
        loc="lower right",
        fontsize=LEADERBOARD_LEGEND_FONTSIZE,
        framealpha=0.92,
        markerscale=0.75,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({n} configurations)")
    if show:
        plt.show()
    plt.close(fig)


def sql_body(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip().rstrip(";")


def fetch_sql_table(sql_path: Path, conn: str) -> pd.DataFrame:
    query = sql_body(sql_path)
    proc = subprocess.run(
        ["psql", conn, "-v", "ON_ERROR_STOP=1", "-c", f"COPY ({query}) TO STDOUT WITH CSV HEADER"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"psql failed ({proc.returncode})")
    df = pd.read_csv(io.StringIO(proc.stdout))
    if df.empty:
        raise SystemExit(f"No rows from {sql_path}")
    return df


def format_markdown_cell(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return f"{val:g}"
    text = str(val)
    if text in ("nan", "NaN", "<NA>"):
        return ""
    return text.replace("|", "\\|")


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        cells = [format_markdown_cell(val) for val in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def records_from_frame(df: pd.DataFrame) -> list[dict[str, str]]:
    filled = df.where(pd.notnull(df), "")
    return [{str(k): str(v) for k, v in row.items()} for row in filled.to_dict(orient="records")]


def public_table(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in HIDDEN_TABLE_COLS if c in df.columns]
    return df.drop(columns=drop)


def disk_caption(disk: str, mode: str) -> str:
    if not disk:
        return ""
    if mode == "combined":
        return (
            f" Disk is Darwin combined throughput (`{disk}_MB/s`); "
            "there is no read/write split."
        )
    return f" Disk is combined read+write on data volume `{disk}`."


def traces_markdown(
    score_row: pd.Series,
    score_disk: str,
    score_mode: str,
    eff_row: pd.Series | None = None,
    eff_disk: str = "",
    eff_mode: str = "",
    nvidia_row: pd.Series | None = None,
    nvidia_disk: str = "",
    nvidia_mode: str = "",
) -> str:
    def intro(row: pd.Series, role: str) -> str:
        cpu = str(row["cpu"]).strip()
        ver = format_markdown_cell(row["ver"])
        fsync = str(row["fsync"]).strip()
        score = format_markdown_cell(row["score_kips"])
        if role == "score":
            return (
                f"The board leader is **{cpu}** (PostgreSQL {ver}, `fsync={fsync}`, "
                f"OSM score **{score}**)."
            )
        if role == "nvidia":
            hours = format_markdown_cell(row["hours"])
            overall = format_markdown_cell(row["overall_kips"])
            return (
                f"**NVIDIA Spark** (court, **{cpu}**) rounds out the set "
                f"(PostgreSQL {ver}, `fsync={fsync}`, OSM score **{score}**, "
                f"**{overall}** kNodes/s total, **{hours}h**)."
            )
        watts = format_markdown_cell(row["score_per_watt"])
        return (
            f"The power-efficiency leader is **{cpu}** (PostgreSQL {ver}, "
            f"`fsync={fsync}`, **{watts}** score/W, OSM score **{score}**)."
        )

    blocks = [
        intro(score_row, "score")
        + " Both traces are minute buckets of the owned **1-second** collectors "
        "on that run: Average is what a minute-grained sample would report; "
        "Maximum is the peak 1-second reading in that minute — the cliffs a "
        "delegated 60-second poll never stored."
        + disk_caption(score_disk, score_mode),
        "![OSM leader disk average vs 1-second maximum]"
        "({{ '/images/osm-leaderboard-disk.png' | relative_url }})",
        "![OSM leader package power average vs 1-second maximum]"
        "({{ '/images/osm-leaderboard-power.png' | relative_url }})",
    ]
    if eff_row is not None:
        blocks.extend(
            [
                intro(eff_row, "efficiency") + disk_caption(eff_disk, eff_mode),
                "![OSM efficiency-leader disk average vs 1-second maximum]"
                "({{ '/images/osm-leaderboard-efficiency-disk.png' | relative_url }})",
                "![OSM efficiency-leader package power average vs 1-second maximum]"
                "({{ '/images/osm-leaderboard-efficiency-power.png' | relative_url }})",
            ]
        )
    if nvidia_row is not None:
        blocks.extend(
            [
                intro(nvidia_row, "nvidia") + disk_caption(nvidia_disk, nvidia_mode),
                "![OSM NVIDIA Spark disk average vs 1-second maximum]"
                "({{ '/images/osm-leaderboard-nvidia-disk.png' | relative_url }})",
                "![OSM NVIDIA Spark package power average vs 1-second maximum]"
                "({{ '/images/osm-leaderboard-nvidia-power.png' | relative_url }})",
            ]
        )
    return f"{TRACE_BEGIN}\n\n" + "\n\n".join(blocks) + f"\n\n{TRACE_END}"


def replace_marked_block(text: str, begin: str, end: str, inner: str) -> str:
    if begin in text and end in text:
        return re.sub(
            re.escape(begin) + r".*?" + re.escape(end),
            inner,
            text,
            count=1,
            flags=re.S,
        )
    raise SystemExit(f"Missing {begin} / {end} markers in leaderboard page")


def write_leaderboard_page(page: Path, table_md: str, n_rows: int) -> None:
    text = page.read_text(encoding="utf-8")
    table_inner = f"{TABLE_BEGIN}\n\n_Query returned {n_rows} rows._\n\n{table_md}\n\n{TABLE_END}"
    text = replace_marked_block(text, TABLE_BEGIN, TABLE_END, table_inner)
    page.write_text(text, encoding="utf-8")
    print(f"Wrote {n_rows} rows into {page}")


def write_power_page(
    page: Path,
    traces_md: str | None = None,
    joules_md: str | None = None,
    compare_md: str | None = None,
) -> None:
    text = page.read_text(encoding="utf-8")
    if traces_md is not None:
        text = replace_marked_block(text, TRACE_BEGIN, TRACE_END, traces_md)
    if joules_md is not None:
        text = replace_marked_block(text, JOULES_BEGIN, JOULES_END, joules_md)
    if compare_md is not None:
        text = replace_marked_block(text, COMPARE_BEGIN, COMPARE_END, compare_md)
    page.write_text(text, encoding="utf-8")
    print(f"Wrote disk/power detail into {page}")


def same_run(a: pd.Series, b: pd.Series) -> bool:
    return str(a["server"]).strip() == str(b["server"]).strip() and int(a["test"]) == int(
        b["test"]
    )


def efficiency_row(table: pd.DataFrame, score_row: pd.Series) -> pd.Series | None:
    if "score_per_watt" not in table.columns:
        return None
    ranked = table.copy()
    ranked["score_per_watt"] = pd.to_numeric(ranked["score_per_watt"], errors="coerce")
    ranked = ranked.dropna(subset=["score_per_watt"]).sort_values(
        "score_per_watt", ascending=False
    )
    if ranked.empty:
        return None
    best = ranked.iloc[0]
    if same_run(best, score_row):
        return None
    return best


def nvidia_row(
    table: pd.DataFrame, score_row: pd.Series, eff_row: pd.Series | None
) -> pd.Series | None:
    """Best-score NVIDIA / Grace Spark cell for the mid-board court traces."""
    nvidia = table[table["cpu"].astype(str).str.startswith("NVIDIA")].copy()
    if nvidia.empty:
        return None
    nvidia["score_kips"] = pd.to_numeric(nvidia["score_kips"], errors="coerce")
    nvidia = nvidia.dropna(subset=["score_kips"]).sort_values(
        "score_kips", ascending=False
    )
    for _, row in nvidia.iterrows():
        if same_run(row, score_row):
            continue
        if eff_row is not None and same_run(row, eff_row):
            continue
        return row
    return None


def disk_title(cpu: str, disk: str, mode: str) -> str:
    if not disk:
        return f"{cpu} disk"
    if mode == "combined":
        return f"{cpu} disk · {disk}"
    return f"{cpu} disk · {disk} read+write"


def plot_leader_traces(
    row: pd.Series,
    conn: str,
    disk_path: Path,
    power_path: Path,
    show: bool = False,
) -> tuple[str, str]:
    server = str(row["server"]).strip()
    test = int(row["test"])
    cpu = str(row["cpu"]).strip()
    disk_df, disk, mode = fetch_disk_avg_max(conn, server, test)
    power_df = fetch_power_avg_max(conn, server, test)
    if disk_df.empty:
        raise SystemExit(f"No disk series for {server} test {test}")
    if power_df.empty:
        raise SystemExit(f"No power series for {server} test {test}")
    avg_l, max_l = legend_avg_max(disk_df, "MB/s")
    plot_avg_max(
        disk_df,
        disk_path,
        title=disk_title(cpu, disk, mode),
        ylabel="MB/s",
        avg_legend=avg_l,
        max_legend=max_l,
        show=show,
    )
    avg_l, max_l = legend_avg_max(power_df, "W")
    plot_avg_max(
        power_df,
        power_path,
        title=f"{cpu} package power",
        ylabel="Watts",
        avg_legend=avg_l,
        max_legend=max_l,
        show=show,
    )
    return disk, mode


def main() -> int:
    use_pg18_style()
    args = parse_args()
    table = None
    traces_md = None
    if args.from_db:
        table = fetch_sql_table(args.sql, args.conn)
        if "server" in table.columns and "test" in table.columns:
            top = table.iloc[0]
            disk, mode = plot_leader_traces(
                top, args.conn, DISK_IMAGE, POWER_IMAGE, show=args.show
            )
            eff = efficiency_row(table, top)
            eff_disk, eff_mode = "", ""
            if eff is not None:
                eff_disk, eff_mode = plot_leader_traces(
                    eff,
                    args.conn,
                    EFF_DISK_IMAGE,
                    EFF_POWER_IMAGE,
                    show=args.show,
                )
            nvidia = nvidia_row(table, top, eff)
            nvidia_disk, nvidia_mode = "", ""
            if nvidia is not None:
                nvidia_disk, nvidia_mode = plot_leader_traces(
                    nvidia,
                    args.conn,
                    NVIDIA_DISK_IMAGE,
                    NVIDIA_POWER_IMAGE,
                    show=args.show,
                )
            traces_md = traces_markdown(
                top,
                disk,
                mode,
                eff,
                eff_disk,
                eff_mode,
                nvidia,
                nvidia_disk,
                nvidia_mode,
            )
        rows = records_from_frame(table)
    else:
        rows = load_snapshot_table(args.snapshot)
        if not rows:
            raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_leaderboard_df(rows)
    plot_leaderboard(df, args.output, show=args.show)
    joules_md = None
    compare_md = None
    if args.from_db and "kj" in df.columns and df["kj"].notna().any():
        plot_score_vs_joules(df, JOULES_IMAGE, show=args.show)
        joules_md = joules_markdown(df)
    if (
        args.from_db
        and "kj" in df.columns
        and "rel_ps" in df.columns
        and df["kj"].notna().any()
        and df["rel_ps"].notna().any()
    ):
        plot_system_compare(df, COMPARE_IMAGE, show=args.show)
        compare_md = compare_markdown()
    if args.from_db and table is not None and not args.no_page:
        write_leaderboard_page(
            args.page,
            dataframe_to_markdown(public_table(table)),
            len(table),
        )
        if traces_md or joules_md or compare_md:
            write_power_page(args.power_page, traces_md, joules_md, compare_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
