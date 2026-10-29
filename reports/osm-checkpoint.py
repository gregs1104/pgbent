#!/usr/bin/env python3
"""
Graph OSM checkpoint study results from a release's static snapshot (default PG18).

Plots total load throughput vs achieved minutes between checkpoints. One series
for all durability faces; wal_level / max_wal_size detail stays in the published
table. Lines connect runs on the same CPU.

Usage:
  python3 reports/osm-checkpoint.py
  python3 reports/osm-checkpoint.py --output docs/images/pg18-osm-checkpoint.png
  python3 reports/osm-checkpoint.py --pg 19
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
from pg18_style import SMALL_ANNOTATION_FONTSIZE, use_pg18_style
from release_paths import add_pg_argument, image_path, snapshot_path
from snapshot_table import load_snapshot_table

# Match leaderboard / history: Intel blue, AMD red.
INTEL_COLOR = "#0071C5"
AMD_COLOR = "#ED1C24"

DROP_CPUS = {
    "Apple M1 Pro",
    "Apple M4 Max",
    "Apple M4 Max Studio",
    "NVIDIA P4242",
    "i3-13100",
    "R9 9950X",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot OSM checkpoint study")
    add_pg_argument(parser)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    args = parser.parse_args()
    args.snapshot = args.snapshot or snapshot_path(args.pg, "osm-checkpoint")
    args.output = args.output or image_path(args.pg, "osm-checkpoint")
    return args


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_checkpoint_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in (
        "overall_kips",
        "index_kips",
        "max_wal_gb",
        "timeout",
        "chkp_mins",
        "timed_pct",
        "chkp_mbph",
    ):
        if col in df.columns:
            df[col] = numeric(df[col])
    return df.sort_values(["cpu", "chkp_mins"]).reset_index(drop=True)


def cpu_color(cpu: str) -> str:
    name = str(cpu)
    if name[:1] == "i":
        return INTEL_COLOR
    if name[:1] == "R":
        return AMD_COLOR
    return "#333333"


def plain_axis(ax, y: bool = True, x: bool = False) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def tuned_end_labels(df: pd.DataFrame) -> pd.DataFrame:
    """One label per CPU at its longest achieved checkpoint interval."""
    keep = [int(group["chkp_mins"].idxmax()) for _, group in df.groupby("cpu")]
    return df.loc[sorted(keep)]


def plot_checkpoint(df: pd.DataFrame, output: Path, pg: str, show: bool = False) -> None:
    df = df[~df["cpu"].isin(DROP_CPUS)].copy()
    fig, ax = plt.subplots(figsize=(10, 6))

    for cpu, group in df.groupby("cpu"):
        group = group.sort_values("chkp_mins")
        color = cpu_color(str(cpu))
        if len(group) >= 2:
            ax.plot(
                group["chkp_mins"],
                group["overall_kips"],
                color=color,
                alpha=0.3,
                linewidth=1.5,
                zorder=1,
            )
        ax.scatter(
            group["chkp_mins"],
            group["overall_kips"],
            marker="o",
            s=70,
            color=color,
            zorder=3,
        )

    ax.set_xscale("log")
    x_ticks = [3, 5, 10, 20, 30, 40, 60, 70]
    ax.xaxis.set_major_locator(FixedLocator(x_ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([str(t) for t in x_ticks])
    ax.set_xlabel("Minutes between checkpoints (achieved)")
    ax.set_ylabel("Throughput (kNodes/s)")
    ax.set_title(f"PG{pg} OSM load vs checkpoint interval")
    y_top = float(df["overall_kips"].max())
    ax.set_ylim(500, y_top * 1.12)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    plain_axis(ax, x=True)

    fig.tight_layout()

    # Both CPU labels flush to the right spine; i5 one font below its point,
    # R5 half that amount.
    label_df = tuned_end_labels(df)
    right_label_dy = {
        "i5-13600K": -(12 + SMALL_ANNOTATION_FONTSIZE),
        "R5 9600X": -(12 + SMALL_ANNOTATION_FONTSIZE / 2),
    }
    for _, row in label_df.iterrows():
        cpu = str(row["cpu"])
        dy = right_label_dy.get(cpu)
        if dy is None:
            continue
        trans = offset_copy(
            ax.get_yaxis_transform(), fig=fig, x=-4, y=dy, units="points"
        )
        ax.text(
            1.0,
            float(row["overall_kips"]),
            cpu,
            transform=trans,
            ha="right",
            va="center",
            fontsize=SMALL_ANNOTATION_FONTSIZE,
            color=cpu_color(cpu),
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
    plot_checkpoint(df, args.output, args.pg, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
