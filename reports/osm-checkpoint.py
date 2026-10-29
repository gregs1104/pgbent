#!/usr/bin/env python3
"""
Graph OSM checkpoint study results from a release's static snapshot (default PG18).

Two charts share the same points and CPU filter:
  - total load throughput vs achieved checkpoint minutes
  - average checkpoint write rate (GB/h from chkp_mbph) vs the same x

One series for all durability faces; wal_level / max_wal_size detail stays in
the published table. Lines connect runs on the same CPU.

Usage:
  python3 reports/osm-checkpoint.py
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
    parser.add_argument("--output", type=Path, help="Throughput chart path")
    parser.add_argument(
        "--write-output",
        type=Path,
        help="Checkpoint write-rate chart path",
    )
    parser.add_argument("--show", action="store_true", help="Display interactively")
    args = parser.parse_args()
    args.snapshot = args.snapshot or snapshot_path(args.pg, "osm-checkpoint")
    args.output = args.output or image_path(args.pg, "osm-checkpoint")
    args.write_output = args.write_output or image_path(args.pg, "osm-checkpoint-write")
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
    df = df.sort_values(["cpu", "chkp_mins"]).reset_index(drop=True)
    df["chkp_gbph"] = df["chkp_mbph"] / 1024.0
    return df


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


def plot_checkpoint_xy(
    df: pd.DataFrame,
    *,
    y_col: str,
    ylabel: str,
    title: str,
    output: Path,
    y_min: float | None,
    label_dy: dict[str, float],
    label_mode: dict[str, str] | None = None,
    label_dx: dict[str, float] | None = None,
    label_xy: dict[str, tuple[float, float]] | None = None,
    show: bool = False,
) -> None:
    df = df[~df["cpu"].isin(DROP_CPUS)].copy()
    fig, ax = plt.subplots(figsize=(10, 6))

    for cpu, group in df.groupby("cpu"):
        group = group.sort_values("chkp_mins")
        color = cpu_color(str(cpu))
        if len(group) >= 2:
            ax.plot(
                group["chkp_mins"],
                group[y_col],
                color=color,
                alpha=0.3,
                linewidth=1.5,
                zorder=1,
            )
        ax.scatter(
            group["chkp_mins"],
            group[y_col],
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
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    y_top = float(df[y_col].max())
    bottom = 0.0 if y_min is None else y_min
    ax.set_ylim(bottom, y_top * 1.12)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    plain_axis(ax, x=True)

    fig.tight_layout()

    modes = label_mode or {}
    dxs = label_dx or {}
    xys = label_xy or {}
    for _, row in tuned_end_labels(df).iterrows():
        cpu = str(row["cpu"])
        dy = label_dy.get(cpu)
        if dy is None:
            continue
        mode = modes.get(cpu, "right_spine")
        if mode == "data":
            x, y = xys[cpu]
            ax.text(
                x,
                y,
                cpu,
                ha="center",
                va="center",
                fontsize=SMALL_ANNOTATION_FONTSIZE,
                color=cpu_color(cpu),
                clip_on=True,
            )
            continue
        if mode == "left_of_point":
            ax.annotate(
                cpu,
                xy=(float(row["chkp_mins"]), float(row[y_col])),
                xytext=(dxs.get(cpu, -10), dy),
                textcoords="offset points",
                ha="right",
                va="bottom",
                fontsize=SMALL_ANNOTATION_FONTSIZE,
                color=cpu_color(cpu),
                clip_on=True,
            )
            continue
        trans = offset_copy(
            ax.get_yaxis_transform(), fig=fig, x=-4, y=dy, units="points"
        )
        ax.text(
            1.0,
            float(row[y_col]),
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


def plot_throughput(df: pd.DataFrame, output: Path, pg: str, show: bool = False) -> None:
    plot_checkpoint_xy(
        df,
        y_col="overall_kips",
        ylabel="Throughput (kNodes/s)",
        title=f"PG{pg} OSM Checkpoint Interval vs Throughput",
        output=output,
        y_min=500,
        label_dy={
            "i5-13600K": -(12 + SMALL_ANNOTATION_FONTSIZE),
            "R5 9600X": -(12 + SMALL_ANNOTATION_FONTSIZE / 2),
        },
        show=show,
    )


def plot_write_rate(df: pd.DataFrame, output: Path, pg: str, show: bool = False) -> None:
    # Custom label anchors: i5 into the empty band left of its cliff bottom;
    # R5 right-flush and above its end point.
    plot_checkpoint_xy(
        df,
        y_col="chkp_gbph",
        ylabel="Checkpoint write rate (GB/h)",
        title=f"PG{pg} OSM Checkpoint Interval vs Write Rate",
        output=output,
        y_min=0,
        label_dy={
            # Just left + above the tuned-end marker so it stays near the series.
            "i5-13600K": 28 - SMALL_ANNOTATION_FONTSIZE,
            "R5 9600X": 100 - 4 * SMALL_ANNOTATION_FONTSIZE,
        },
        label_mode={
            "i5-13600K": "left_of_point",
            "R5 9600X": "right_spine",
        },
        label_dx={
            # ~8 character widths left of the tuned-end marker.
            "i5-13600K": -18 - int(8 * SMALL_ANNOTATION_FONTSIZE * 0.6),
        },
        show=show,
    )


def main() -> int:
    use_pg18_style()
    args = parse_args()
    rows = load_snapshot_table(args.snapshot)
    if not rows:
        raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_checkpoint_df(rows)
    plot_throughput(df, args.output, args.pg, show=args.show)
    plot_write_rate(df, args.write_output, args.pg, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
