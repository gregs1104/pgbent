#!/usr/bin/env python3
"""
Expanded PG19 rc1 SELECT faces on siren: four conn_method SELECTs plus
sockets nothing (;) and constant (SELECT 1). TPS vs clients — the ranking
board’s fan with the fantasy scripts that prove taking the executor out
nearly doubles the rate.

Usage:
    MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \
      .venv-graph/bin/python reports/select-components.py --from-db
"""

from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, use_pg18_style
from release_paths import REPO_ROOT

DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "select-components.sql"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "select-components.png"

# Top-to-bottom by 32-client peak. Prepared = solid, simple = dashed.
# SELECT keeps the leaderboard orange/blue; fantasy scripts get their own hues.
SERIES = (
    ("nothing", "sockets", "#54a24b", "--", "; sockets"),
    ("nothing", "sockets prepared", "#54a24b", "-", "; sockets prepared"),
    ("constant", "sockets prepared", "#b279a2", "-", "SELECT 1 sockets prepared"),
    ("constant", "sockets", "#b279a2", "--", "SELECT 1 sockets"),
    ("select", "sockets prepared", "#e4572e", "-", "SELECT sockets prepared"),
    ("select", "host prepared", "#4c78a8", "-", "SELECT localhost TCP prepared"),
    ("select", "sockets", "#e4572e", "--", "SELECT sockets"),
    ("select", "host", "#4c78a8", "--", "SELECT localhost TCP"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot expanded SELECT / constant / nothing faces (siren PG19 rc1)"
    )
    parser.add_argument("--from-db", action="store_true", help="Query the results DB")
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--output", type=Path, default=PUBLIC_IMAGE)
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    parser.add_argument("--show", action="store_true")
    return parser.parse_args()


def sql_body(path: Path) -> str:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--")]
    return "\n".join(lines).strip().rstrip(";")


def fetch_sql_table(sql_path: Path, conn: str) -> pd.DataFrame:
    query = sql_body(sql_path)
    proc = subprocess.run(
        ["psql", conn, "-v", "ON_ERROR_STOP=1", "-c", f"COPY ({query}) TO STDOUT WITH CSV HEADER"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"psql failed ({proc.returncode})")
    df = pd.read_csv(io.StringIO(proc.stdout))
    if df.empty:
        raise SystemExit(f"No rows from {sql_path}")
    return df


def plot_components(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    use_pg18_style()
    fig, ax = plt.subplots(figsize=(11, 7))
    plotted = 0
    for script, conn, color, style, label in SERIES:
        face = df[(df["script"] == script) & (df["conn"] == conn)].sort_values("clients")
        if face.empty:
            continue
        ax.plot(
            face["clients"],
            face["tps"],
            color=color,
            linestyle=style,
            marker="o",
            linewidth=2.4,
            markersize=7,
            label=label,
        )
        plotted += 1
    if plotted == 0:
        raise SystemExit("No series to plot")

    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(df["clients"].unique()))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlabel("Clients")
    ax.set_ylabel("TPS")
    ax.set_title("pgbench SELECT components - Siren 9950X")
    ax.grid(True, which="major", linestyle=":", alpha=0.5)
    ax.legend(
        loc="upper left",
        fontsize=max(9, LEADERBOARD_LEGEND_FONTSIZE - 2),
        framealpha=0.92,
        ncol=1,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({plotted} series)")
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if not args.from_db:
        raise SystemExit("Generate with --from-db")
    df = fetch_sql_table(args.sql, args.conn)
    df["clients"] = pd.to_numeric(df["clients"])
    df["tps"] = pd.to_numeric(df["tps"])
    plot_components(df, args.output, show=args.show)


if __name__ == "__main__":
    main()
