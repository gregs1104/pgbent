#!/usr/bin/env python3
"""
Graph OSM power study results from the PG18 static snapshot.

Generates:
  - Throughput (nodes and index) vs maximum package watts
  - Throughput per watt (efficiency) by CPU

Usage:
  python3 reports/osm-power.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-power.md"
DEFAULT_THROUGHPUT = REPO_ROOT / "docs/images/pg18-osm-power.png"
DEFAULT_EFFICIENCY = REPO_ROOT / "docs/images/pg18-osm-power-efficiency.png"

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"


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
        ax.plot(
            [row["max_pkg"], row["max_pkg"]],
            [row["index_kips"], row["nodes_kips"]],
            color="#999999",
            linewidth=1.5,
            alpha=0.6,
            zorder=1,
        )

    ax.scatter(
        df["max_pkg"],
        df["nodes_kips"],
        marker="o",
        s=70,
        color=NODES_COLOR,
        label="Nodes (kNodes/s)",
        zorder=3,
    )
    ax.scatter(
        df["max_pkg"],
        df["index_kips"],
        marker="s",
        s=70,
        color=INDEX_COLOR,
        label="Index (kNodes/s)",
        zorder=3,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["cpu"],
            xy=(row["max_pkg"], row["nodes_kips"]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=NODES_COLOR,
        )

    ax.set_xlabel("Maximum package power (W)")
    ax.set_ylabel("OSM load throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL 18 OSM load: throughput vs package power\n"
        "Vertical bars connect index and node speed at each CPU"
    )
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper left")
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

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([i - height / 2 for i in y], plot_df["nodes_per_watt"], height=height, color=NODES_COLOR, label="Nodes / W")
    ax.barh([i + height / 2 for i in y], plot_df["index_per_watt"], height=height, color=INDEX_COLOR, label="Index / W")
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["cpu"])
    ax.set_xlabel("Throughput per maximum package watt (kNodes/s per W)")
    ax.set_title("PostgreSQL 18 OSM load: efficiency vs package power envelope")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
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
