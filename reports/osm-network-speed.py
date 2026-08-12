#!/usr/bin/env python3
"""
Graph OSM network study results from the PG18 static snapshot.

Shows how remote-client load speed falls as link rate drops on a fixed server
(i5-13600K), with i5 host-local runs as the on-server baseline. Cross-CPU
host-local comparisons need matched hardware or bidirectional tests.

Usage:
  python3 reports/osm-network-speed.py
  python3 reports/osm-network-speed.py --output docs/images/pg18-osm-network-speed.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import conn_mbps, load_snapshot_table

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-network.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-network-speed.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM network connection speed study")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_network_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("nodes_kips", "index_kips", "wal_mbps"):
        df[col] = numeric(df[col])
    df["conn_mbps"] = df["conn"].map(conn_mbps)
    return df


def plot_connection_speed(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    remote = df[
        (df["server"] == "i5-13600K")
        & df["client"].str.contains("R9 9950X", na=False)
        & df["conn_mbps"].notna()
    ].sort_values("conn_mbps")

    i5_host = df[(df["server"] == "i5-13600K") & (df["conn"] == "host")].iloc[0]
    at_10g = remote.loc[remote["conn_mbps"] == 10000].iloc[0]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        remote["conn_mbps"],
        remote["nodes_kips"],
        marker="o",
        linewidth=2,
        color="#e4572e",
        label="Total (kNodes/s)",
    )
    ax.plot(
        remote["conn_mbps"],
        remote["index_kips"],
        marker="s",
        linewidth=2,
        color="#4c78a8",
        label="Index (kNodes/s)",
    )

    ax.axhline(i5_host["nodes_kips"], color="#e4572e", linestyle=":", alpha=0.5)
    ax.axhline(i5_host["index_kips"], color="#4c78a8", linestyle=":", alpha=0.5)

    ax.annotate(
        f"i5 host-local total ({int(i5_host['nodes_kips'])} kNodes/s)",
        xy=(remote["conn_mbps"].max(), i5_host["nodes_kips"]),
        xytext=(8, -14),
        textcoords="offset points",
        fontsize=9,
        color="#e4572e",
    )
    ax.annotate(
        f"i5 host-local index ({int(i5_host['index_kips'])} kNodes/s)",
        xy=(remote["conn_mbps"].max(), i5_host["index_kips"]),
        xytext=(8, 6),
        textcoords="offset points",
        fontsize=9,
        color="#4c78a8",
    )
    ax.annotate(
        f"10Gb/s remote total ({int(at_10g['nodes_kips'])} kNodes/s)",
        xy=(10000, at_10g["nodes_kips"]),
        xytext=(-120, -18),
        textcoords="offset points",
        fontsize=9,
        color="#e4572e",
        arrowprops={"arrowstyle": "->", "color": "#e4572e", "lw": 1},
    )
    ax.annotate(
        f"10Gb/s remote index ({int(at_10g['index_kips'])} kNodes/s)",
        xy=(10000, at_10g["index_kips"]),
        xytext=(-120, 12),
        textcoords="offset points",
        fontsize=9,
        color="#4c78a8",
        arrowprops={"arrowstyle": "->", "color": "#4c78a8", "lw": 1},
    )

    ax.set_xscale("log")
    ax.set_xlabel("Client–server link rate (Mb/s)")
    ax.set_ylabel("OSM load throughput (kNodes/s)")
    ax.set_title(
        "PostgreSQL 18 OSM load: R9 9950X client on i5-13600K server\n"
        "Throughput vs client–server link rate"
    )
    ax.set_xticks(remote["conn_mbps"])
    ax.set_xticklabels([f"{int(v / 1000)}Gb/s" if v >= 1000 else f"{int(v)}Mb/s" for v in remote["conn_mbps"]])
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")

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
    args = parse_args()
    rows = load_snapshot_table(args.snapshot)
    if not rows:
        raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_network_df(rows)
    plot_connection_speed(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
