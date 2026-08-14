#!/usr/bin/env python3
"""
Graph OSM relation power efficiency from the PG18 osm-power snapshot.

Reads the "Relation power efficiency" table in docs/results-summary/pg18/osm-power.md
and charts relations per average watt by CPU.

Usage:
  python3 reports/osm-relation-power.py
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
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-relation-power.png"
RELATION_HEADING = "## Relation power efficiency"

BAR_COLOR = "#72b7b2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM relation power efficiency")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_relation_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("rel", "avg_watts", "rel_per_watt"):
        if col in df.columns:
            df[col] = numeric(df[col])
    return df.dropna(subset=["cpu", "rel", "avg_watts", "rel_per_watt"]).reset_index(drop=True)


def plain_axis(ax, y: bool = True, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_relation_efficiency(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    plot_df = df.sort_values("rel_per_watt", ascending=True).reset_index(drop=True)
    y = range(len(plot_df))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(list(y), plot_df["rel_per_watt"], color=BAR_COLOR)
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["cpu"])
    ax.set_xlabel("Relations per average watt (rel / W)")
    ax.set_title(
        "PostgreSQL 18 OSM load: relation phase efficiency\n"
        "Average package power over the full planet load"
    )
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)

    xmax = plot_df["rel_per_watt"].max()
    pad = max(xmax * 0.02, 3)
    for i, row in plot_df.iterrows():
        ax.text(
            row["rel_per_watt"] + pad,
            i,
            f"{int(row['rel']):,} rel · {int(row['avg_watts'])} W avg",
            va="center",
            fontsize=8,
            color="#333333",
        )

    ax.set_xlim(0, xmax + pad * 8)
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
    rows = load_snapshot_table(args.snapshot, heading=RELATION_HEADING)
    if not rows:
        raise SystemExit(f"No relation table found under {RELATION_HEADING!r} in {args.snapshot}")
    df = prepare_relation_df(rows)
    if df.empty:
        raise SystemExit("Relation table has no plottable rows")
    plot_relation_efficiency(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
