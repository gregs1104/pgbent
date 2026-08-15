#!/usr/bin/env python3
"""
Graph OSM checkpoint study results from the PG18 static snapshot.

Plots throughput vs achieved minutes between checkpoints (chkp_mins). Points are
colored by wal_level; lines connect runs on the same CPU when it has multiple
checkpoint settings.

Usage:
  python3 reports/osm-checkpoint.py
  python3 reports/osm-checkpoint.py --output docs/images/pg18-osm-checkpoint.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter
from matplotlib.transforms import offset_copy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from label_layout import LabelOffset, place_label_at_grid_bottom, place_point_labels
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, SMALL_ANNOTATION_FONTSIZE, use_pg18_style
from snapshot_table import load_snapshot_table

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-checkpoint.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-checkpoint.png"

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"
WAL_COLORS = {"minimal": NODES_COLOR, "replica": "#c44e32"}
INDEX_WAL_COLORS = {"minimal": INDEX_COLOR, "replica": "#6b8ebf"}
TOTAL_MARKERS = {"minimal": "o", "replica": "^"}
INDEX_MARKERS = {"minimal": "s", "replica": "v"}


DROP_CPUS = {
    "Apple M1 Pro",
    "Apple M4 Max",
    "Apple M4 Max Studio",
    "NVIDIA P4242",
}

CHECKPOINT_LABEL_OVERRIDES = {
    "i5-13600K\n100GB": LabelOffset(11, 5, ha="left", va="top"),
    "i3-13100": LabelOffset(8, 0, ha="left", va="center"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM checkpoint study")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_checkpoint_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in (
        "nodes_kips",
        "index_kips",
        "max_wal_gb",
        "timeout",
        "chkp_mins",
        "timed_pct",
        "chkp_mbph",
    ):
        if col in df.columns:
            df[col] = numeric(df[col])
    return df.sort_values(["wal_level", "cpu", "chkp_mins"]).reset_index(drop=True)


def config_label(row: pd.Series) -> str:
    if row["max_wal_gb"] != 256:
        return f"{int(row['max_wal_gb'])}GB"
    return ""


def series_label(row: pd.Series, kind: str) -> str:
    name = str(row["cpu"])
    if kind == "index":
        return f"{name} index"
    config = config_label(row)
    if config:
        return f"{name}\n{config}"
    return name


def labeled_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Keep isolated CPUs and the shortest/longest checkpoint run on each CPU."""
    keep: list[int] = []
    for _, group in df.groupby("cpu"):
        if len(group) == 1:
            keep.extend(group.index.tolist())
            continue
        keep.append(int(group["chkp_mins"].idxmin()))
        keep.append(int(group["chkp_mins"].idxmax()))
    return df.loc[sorted(set(keep))]


def plain_axis(ax, y: bool = True, x: bool = False) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_checkpoint(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    df = df[~df["cpu"].isin(DROP_CPUS)].copy()
    fig, ax = plt.subplots(figsize=(10, 6))

    for (cpu, wal_level), group in df.groupby(["cpu", "wal_level"]):
        if len(group) < 2:
            continue
        group = group.sort_values("chkp_mins")
        ax.plot(
            group["chkp_mins"],
            group["nodes_kips"],
            color=WAL_COLORS[wal_level],
            alpha=0.25,
            linewidth=1.5,
            zorder=1,
        )
        ax.plot(
            group["chkp_mins"],
            group["index_kips"],
            color=INDEX_WAL_COLORS[wal_level],
            alpha=0.25,
            linewidth=1.5,
            zorder=1,
        )

    for wal_level in ("minimal", "replica"):
        subset = df[df["wal_level"] == wal_level]
        ax.scatter(
            subset["chkp_mins"],
            subset["nodes_kips"],
            marker=TOTAL_MARKERS[wal_level],
            s=70,
            color=WAL_COLORS[wal_level],
            label=f"{wal_level} total (kNodes/s)",
            zorder=3,
        )
        ax.scatter(
            subset["chkp_mins"],
            subset["index_kips"],
            marker=INDEX_MARKERS[wal_level],
            s=70 if wal_level == "replica" else 55,
            color=INDEX_WAL_COLORS[wal_level],
            label=f"{wal_level} index (kNodes/s)",
            zorder=3,
        )

    ax.set_xscale("log")
    x_ticks = [3, 5, 10, 20, 30, 40, 60, 70]
    ax.xaxis.set_major_locator(FixedLocator(x_ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([str(t) for t in x_ticks])
    ax.set_xlabel("Minutes between checkpoints (achieved)")
    ax.set_ylabel("Throughput (kNodes/s)")
    ax.set_title(
        "PG18 OSM load:  achieved checkpoint interval\n"
        "Tuned values 256GB WAL / 60 min interval"
    )
    y_top = float(df["nodes_kips"].max())
    ax.set_ylim(140, y_top * 1.18)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.legend(
        loc="center left",
        bbox_to_anchor=(0.0, 0.35),
        fontsize=LEADERBOARD_LEGEND_FONTSIZE,
        markerscale=0.75,
    )
    plain_axis(ax, x=True)

    fig.tight_layout()

    label_df = labeled_runs(df)
    labels: list[str] = []
    xs: list[float] = []
    ys: list[float] = []
    colors: list[str] = []
    for _, row in label_df.iterrows():
        skip_i5_right = row["cpu"] == "i5-13600K" and float(row["chkp_mins"]) > 50
        if not skip_i5_right:
            labels.append(series_label(row, "total"))
            xs.append(float(row["chkp_mins"]))
            ys.append(float(row["nodes_kips"]))
            colors.append(WAL_COLORS[row["wal_level"]])
        if row["cpu"] == "R9 9950X":
            continue
        if row["cpu"] == "i3-13100":
            continue
        if row["cpu"] == "R5 9600X" and float(row["chkp_mins"]) > 50:
            continue
        if row["cpu"] == "i5-13600K":
            continue
        labels.append(series_label(row, "index"))
        xs.append(float(row["chkp_mins"]))
        ys.append(float(row["index_kips"]))
        colors.append(INDEX_WAL_COLORS[row["wal_level"]])
    place_point_labels(
        ax,
        labels,
        xs,
        ys,
        colors,
        SMALL_ANNOTATION_FONTSIZE,
        overrides=CHECKPOINT_LABEL_OVERRIDES,
    )

    i3_left = df[df["cpu"] == "i3-13100"].sort_values("chkp_mins").iloc[0]
    place_label_at_grid_bottom(
        ax,
        float(i3_left["chkp_mins"]),
        float(i3_left["index_kips"]),
        series_label(i3_left, "index"),
        INDEX_WAL_COLORS[i3_left["wal_level"]],
        SMALL_ANNOTATION_FONTSIZE,
        x_gap_points=-6,
        align_fraction=0.04,
    )

    r9 = df[df["cpu"] == "R9 9950X"].iloc[0]
    r9_index_trans = offset_copy(
        ax.get_yaxis_transform(), fig=fig, x=-4, y=10, units="points"
    )
    ax.text(
        1.0,
        float(r9["index_kips"]),
        series_label(r9, "index"),
        transform=r9_index_trans,
        ha="right",
        va="bottom",
        fontsize=SMALL_ANNOTATION_FONTSIZE,
        color=INDEX_WAL_COLORS[r9["wal_level"]],
        clip_on=True,
    )

    r5_right = df[df["cpu"] == "R5 9600X"].sort_values("chkp_mins").iloc[-1]
    ax.annotate(
        series_label(r5_right, "index"),
        xy=(float(r5_right["chkp_mins"]), float(r5_right["index_kips"])),
        xytext=(0, -22),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=SMALL_ANNOTATION_FONTSIZE,
        color=INDEX_WAL_COLORS[r5_right["wal_level"]],
        clip_on=True,
    )

    i5_left = df[df["cpu"] == "i5-13600K"].sort_values("chkp_mins").iloc[0]
    ax.annotate(
        series_label(i5_left, "index"),
        xy=(float(i5_left["chkp_mins"]), float(i5_left["index_kips"])),
        xytext=(0, -6),
        textcoords="offset points",
        ha="center",
        va="top",
        fontsize=SMALL_ANNOTATION_FONTSIZE,
        color=INDEX_WAL_COLORS[i5_left["wal_level"]],
        clip_on=True,
    )

    i5_right = df[df["cpu"] == "i5-13600K"].sort_values("chkp_mins").iloc[-1]
    i5_total_trans = offset_copy(
        ax.get_yaxis_transform(), fig=fig, x=-4, y=-15, units="points"
    )
    ax.text(
        1.0,
        float(i5_right["nodes_kips"]),
        series_label(i5_right, "total"),
        transform=i5_total_trans,
        ha="right",
        va="center",
        fontsize=SMALL_ANNOTATION_FONTSIZE,
        color=WAL_COLORS[i5_right["wal_level"]],
        clip_on=True,
    )
    ax.annotate(
        series_label(i5_right, "index"),
        xy=(float(i5_right["chkp_mins"]), float(i5_right["index_kips"])),
        xytext=(18, 8),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=SMALL_ANNOTATION_FONTSIZE,
        color=INDEX_WAL_COLORS[i5_right["wal_level"]],
        clip_on=True,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    use_pg18_style()
    args = parse_args()
    rows = load_snapshot_table(args.snapshot)
    if not rows:
        raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_checkpoint_df(rows)
    plot_checkpoint(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
