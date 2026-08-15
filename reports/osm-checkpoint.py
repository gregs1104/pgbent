#!/usr/bin/env python3
"""
Graph OSM checkpoint study results from the PG18 static snapshot.

Plots throughput vs achieved minutes between checkpoints (chkp_mins). Points are
colored by wal_level; lines connect runs on the same CPU when it has multiple
checkpoint settings.

Usage:
  python3 reports/osm-checkpoint.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table
from pg18_style import ANNOTATION_FONTSIZE, SMALL_ANNOTATION_FONTSIZE, use_pg18_style

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-checkpoint.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-checkpoint.png"

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"
WAL_COLORS = {"minimal": NODES_COLOR, "replica": "#c44e32"}
INDEX_WAL_COLORS = {"minimal": INDEX_COLOR, "replica": "#6b8ebf"}


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
    parts = [f"{int(row['max_wal_gb'])}GB WAL"]
    if row["fsync"] == "on":
        parts.append("fsync")
    if row["timeout"] == 5:
        parts.append("5min timeout")
    return ", ".join(parts)


def plain_axis(ax, y: bool = True, x: bool = False) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_checkpoint(df: pd.DataFrame, output: Path, show: bool = False) -> None:
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
            marker="o",
            s=70,
            color=WAL_COLORS[wal_level],
            label=f"{wal_level} total (kNodes/s)",
            zorder=3,
        )
        ax.scatter(
            subset["chkp_mins"],
            subset["index_kips"],
            marker="s",
            s=55,
            color=INDEX_WAL_COLORS[wal_level],
            label=f"{wal_level} index (kNodes/s)",
            zorder=3,
        )

    extremes = df.loc[df.groupby("wal_level")["chkp_mins"].idxmin()]
    extremes = pd.concat([extremes, df.loc[df.groupby("wal_level")["chkp_mins"].idxmax()]])
    for _, row in extremes.drop_duplicates().iterrows():
        ax.annotate(
            f"{row['cpu']}\n{config_label(row)}",
            xy=(row["chkp_mins"], row["nodes_kips"]),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=SMALL_ANNOTATION_FONTSIZE,
            color=WAL_COLORS[row["wal_level"]],
        )

    ax.set_xscale("log")
    x_ticks = [3, 5, 10, 20, 30, 40, 60, 70]
    ax.xaxis.set_major_locator(FixedLocator(x_ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([str(t) for t in x_ticks])
    ax.set_xlabel("Minutes between checkpoints (achieved)")
    ax.set_ylabel("OSM load throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL 18 OSM load: checkpoint tuning\n"
        "Throughput vs achieved checkpoint interval"
    )
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
    plain_axis(ax, x=True)

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
    df = prepare_checkpoint_df(rows)
    plot_checkpoint(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
