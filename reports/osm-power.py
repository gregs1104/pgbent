#!/usr/bin/env python3
"""
Graph OSM power study results from the PG18 static snapshot.

Generates:
  - Throughput (total and index) vs maximum package watts
  - Throughput per watt (efficiency) by CPU

Usage:
  python3 reports/osm-power.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-power.md"
DEFAULT_THROUGHPUT = REPO_ROOT / "docs/images/pg18-osm-power.png"
DEFAULT_EFFICIENCY = REPO_ROOT / "docs/images/pg18-osm-power-efficiency.png"

DEFAULT_POINT_COLOR = "#333333"
INDEX_BAR_ALPHA = 0.45
POINT_LABEL_FONTSIZE = 11


def row_color(row: pd.Series) -> str:
    return str(row.get("cpu_c", "")).strip() or DEFAULT_POINT_COLOR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM power study")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--throughput-output", type=Path, default=DEFAULT_THROUGHPUT)
    parser.add_argument("--efficiency-output", type=Path, default=DEFAULT_EFFICIENCY)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_power_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("mem_gb", "nodes_kips", "index_kips", "max_pkg", "avg_pkg", "wal", "avg_write", "max_write", "avg_read", "max_read"):
        if col in df.columns:
            df[col] = numeric(df[col])
    df = df.sort_values("max_pkg").reset_index(drop=True)
    df["nodes_per_watt"] = df["nodes_kips"] / df["max_pkg"]
    df["index_per_watt"] = df["index_kips"] / df["max_pkg"]
    return df


def plain_axis(ax, y: bool = True, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_throughput_vs_power(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))

    for _, row in df.iterrows():
        color = row_color(row)
        ax.plot(
            [row["max_pkg"], row["max_pkg"]],
            [row["index_kips"], row["nodes_kips"]],
            color=color,
            linewidth=1.5,
            alpha=0.45,
            zorder=1,
        )
        ax.scatter(
            row["max_pkg"],
            row["nodes_kips"],
            marker="o",
            s=70,
            color=color,
            zorder=3,
        )
        ax.scatter(
            row["max_pkg"],
            row["index_kips"],
            marker="s",
            s=70,
            color=color,
            zorder=3,
        )
        ax.annotate(
            row["cpu"],
            xy=(row["max_pkg"], row["nodes_kips"]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=POINT_LABEL_FONTSIZE,
            color=color,
        )

    ax.set_xlabel("Maximum package power (W)")
    ax.set_ylabel("OSM load throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL 18 OSM load: throughput vs package power\n"
        "Vertical bars connect index and total speed at each CPU"
    )
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#666666", markersize=8, label="Total (kNodes/s)"),
            Line2D([0], [0], marker="s", color="w", markerfacecolor="#666666", markersize=8, label="Index (kNodes/s)"),
        ],
        loc="upper left",
    )
    plain_axis(ax)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def plot_efficiency(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    plot_df = df.sort_values("nodes_per_watt", ascending=True).reset_index(drop=True)
    y = range(len(plot_df))
    height = 0.35
    colors = [row_color(row) for _, row in plot_df.iterrows()]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([i - height / 2 for i in y], plot_df["nodes_per_watt"], height=height, color=colors)
    ax.barh(
        [i + height / 2 for i in y],
        plot_df["index_per_watt"],
        height=height,
        color=colors,
        alpha=INDEX_BAR_ALPHA,
    )
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["cpu"], fontsize=POINT_LABEL_FONTSIZE)
    for tick, color in zip(ax.get_yticklabels(), colors):
        tick.set_color(color)
    ax.set_xlabel("Throughput per maximum package watt (kNodes/s per W)")
    ax.set_title("PostgreSQL 18 OSM load: efficiency vs package power envelope")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.legend(
        handles=[
            Patch(facecolor="#666666", alpha=INDEX_BAR_ALPHA, label="Index / W"),
            Patch(facecolor="#666666", label="Total / W"),
        ],
        loc="lower right",
    )
    plain_axis(ax, y=False)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    args = parse_args()
    rows = load_snapshot_table(args.snapshot)
    if not rows:
        raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_power_df(rows)
    plot_throughput_vs_power(df, args.throughput_output, show=args.show)
    plot_efficiency(df, args.efficiency_output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
