#!/usr/bin/env python3
"""
Graph OSM leaderboard results from the PG18 static snapshot.

Keeps one row per host-local server configuration (cpu, memory, disk) — the best
nodes_kips run for that hardware, regardless of PostgreSQL version or tuning.
Remote-client runs (non-host conn) are excluded.

Usage:
  python3 reports/osm-leaderboard.py
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
from pg18_style import Y_LABEL_FONTSIZE, use_pg18_style

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-leaderboard.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-leaderboard.png"

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM leaderboard")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def config_label(row: pd.Series) -> str:
    disk = str(row["disk"]).strip()
    if len(disk) > 12:
        disk = disk[:10] + "…"
    mem = int(row["mem_gb"])
    return f"{row['cpu']} · {mem}GB · {disk}"


def prepare_leaderboard_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("mem_gb", "nodes_kips", "index_kips", "ver", "hours", "max_wal_gb"):
        if col in df.columns:
            df[col] = numeric(df[col])
    df["disk"] = df["disk"].str.strip()
    df = df[df["conn"].astype(str).str.strip().str.lower() == "host"]

    best = (
        df.sort_values(["nodes_kips", "index_kips"], ascending=False)
        .groupby(["cpu", "mem_gb", "disk"], as_index=False)
        .first()
    )
    best["label"] = best.apply(config_label, axis=1)
    return best.sort_values("nodes_kips", ascending=True).reset_index(drop=True)


def plain_axis(ax, y: bool = False, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_leaderboard(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    height = max(6, 0.35 * len(df) + 1.5)
    fig, ax = plt.subplots(figsize=(10, height))
    y = range(len(df))
    bar_height = 0.35

    ax.barh(
        [i - bar_height / 2 for i in y],
        df["nodes_kips"],
        height=bar_height,
        color=NODES_COLOR,
        label="Total (kNodes/s)",
    )
    ax.barh(
        [i + bar_height / 2 for i in y],
        df["index_kips"],
        height=bar_height,
        color=INDEX_COLOR,
        label="Index (kNodes/s)",
    )

    ax.set_yticks(list(y))
    ax.set_yticklabels(df["label"], fontsize=Y_LABEL_FONTSIZE)
    ax.set_xlabel("OSM load throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL OSM load leaderboard\n"
        "Best host-local run per server configuration"
    )
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
    plain_axis(ax)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(df)} configurations)")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    use_pg18_style()
    args = parse_args()
    rows = load_snapshot_table(args.snapshot)
    if not rows:
        raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_leaderboard_df(rows)
    plot_leaderboard(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
