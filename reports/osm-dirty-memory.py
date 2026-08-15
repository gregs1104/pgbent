#!/usr/bin/env python3
"""
Graph OSM dirty memory study results from the PG18 static snapshot.

Plots nodes vs index load throughput against peak dirty memory observed during
each run—same layout as osm-network-speed.py.

Usage:
  python3 reports/osm-dirty-memory.py
  python3 reports/osm-dirty-memory.py --output docs/images/pg18-osm-dirty-memory.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import ScalarFormatter
from matplotlib.transforms import offset_copy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import ANNOTATION_FONTSIZE, LEADERBOARD_LEGEND_FONTSIZE, use_pg18_style
from snapshot_table import load_snapshot_table

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-dirty-memory.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-dirty-memory.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM dirty memory study")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def format_dirty_label(bytes_val: float) -> str:
    gb = bytes_val / (1024**3)
    if gb >= 1:
        return f"{gb:.1f}GB"
    mb = bytes_val / (1024**2)
    return f"{mb:.0f}MB"


def prepare_dirty_memory_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("hours", "nodes", "nodes_kips", "index_kips", "max_dirty", "wal_mbps", "avg_write_mbps", "max_write_mbps"):
        df[col] = numeric(df[col])

    df = (
        df.groupby("batch", as_index=False)
        .agg(
            max_dirty=("max_dirty", "max"),
            nodes_kips=("nodes_kips", "mean"),
            index_kips=("index_kips", "mean"),
            hours=("hours", "mean"),
        )
        .sort_values("max_dirty")
    )
    df["dirty_label"] = df["max_dirty"].map(format_dirty_label)
    return df


def plot_dirty_memory(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    default = df.loc[df["max_dirty"].idxmax()]
    smallest = df.loc[df["max_dirty"].idxmin()]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        df["max_dirty"],
        df["nodes_kips"],
        marker="o",
        linewidth=2,
        color="#e4572e",
        label="Total (kNodes/s)",
    )
    ax.plot(
        df["max_dirty"],
        df["index_kips"],
        marker="s",
        linewidth=2,
        color="#4c78a8",
        label="Index (kNodes/s)",
    )

    ax.set_xscale("log")
    y_top = float(df["nodes_kips"].max())
    ax.set_ylim(200, y_top * 1.32)

    xmin = df["max_dirty"].min()
    ax.annotate(
        f"Smallest limit ({smallest['dirty_label']}) total ({int(smallest['nodes_kips'])} kNodes/s)",
        xy=(xmin, smallest["nodes_kips"]),
        xytext=(8, -22),
        textcoords="offset points",
        ha="left",
        fontsize=ANNOTATION_FONTSIZE,
        color="#e4572e",
        clip_on=True,
    )
    ax.annotate(
        f"Smallest limit ({smallest['dirty_label']}) index ({int(smallest['index_kips'])} kNodes/s)",
        xy=(xmin, smallest["index_kips"]),
        xytext=(8, 10),
        textcoords="offset points",
        ha="left",
        fontsize=ANNOTATION_FONTSIZE,
        color="#4c78a8",
        clip_on=True,
    )
    total_label_trans = offset_copy(ax.transData, fig=fig, x=-8, y=10, units="points")
    ax.text(
        default["max_dirty"],
        default["nodes_kips"],
        f"Default ({default['dirty_label']}) total ({int(default['nodes_kips'])} kNodes/s)",
        transform=total_label_trans,
        ha="right",
        va="bottom",
        fontsize=ANNOTATION_FONTSIZE,
        color="#e4572e",
        clip_on=True,
    )
    index_label_trans = offset_copy(
        ax.get_yaxis_transform(), fig=fig, x=-4, y=-10, units="points"
    )
    ax.text(
        1.0,
        default["index_kips"],
        f"Default ({default['dirty_label']}) index ({int(default['index_kips'])} kNodes/s)",
        transform=index_label_trans,
        ha="right",
        va="top",
        fontsize=ANNOTATION_FONTSIZE,
        color="#4c78a8",
        clip_on=True,
    )

    ax.set_xlabel("Peak dirty memory during run")
    ax.set_ylabel("Throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL 17 OSM load: Linux dirty memory limits\n"
        "Throughput vs peak dirty memory"
    )
    ax.set_xticks(df["max_dirty"])
    ax.set_xticklabels(df["dirty_label"], rotation=35, ha="right")
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.legend(loc="center right", fontsize=LEADERBOARD_LEGEND_FONTSIZE, markerscale=0.75)

    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)

    fig.tight_layout()
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
    df = prepare_dirty_memory_df(rows)
    plot_dirty_memory(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
