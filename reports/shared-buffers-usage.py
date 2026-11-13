#!/usr/bin/env python3
"""
Graph rising set-65 buffercache usagecount vs pgbench database size.

When the hot index fits in shared_buffers (~48GB here), usagecount stays
near the clock maximum (5). As the working set outgrows the cache, both
whole-cache and pgbench_accounts_pkey usage fall — validating avg_usage
as a compact effectiveness signal.

Usage:
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/shared-buffers-usage.py
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
from pg18_style import use_pg18_style

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "shared-buffers-usage.sql"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "shared-buffers-usage.png"

CACHE_COLOR = "#4c78a8"
PKEY_COLOR = "#f58518"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot buffercache usagecount vs pgbench DB size"
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--output", type=Path, default=PUBLIC_IMAGE)
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    parser.add_argument("--show", action="store_true")
    return parser.parse_args()


def sql_body(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip().rstrip(";")


def fetch_sql_table(sql_path: Path, conn: str) -> pd.DataFrame:
    query = sql_body(sql_path)
    proc = subprocess.run(
        [
            "psql",
            conn,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f"COPY ({query}) TO STDOUT WITH CSV HEADER",
        ],
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


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("db_gb", "avg_usage", "pkey_usage"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["db_gb", "avg_usage", "pkey_usage"])
    return out.sort_values("db_gb").reset_index(drop=True)


def plot_usage(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    use_pg18_style()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))

    # Plot pkey first so legend (and visual top-of-stack) lists it above whole cache.
    ax.plot(
        df["db_gb"],
        df["pkey_usage"],
        color=PKEY_COLOR,
        linewidth=2.2,
        marker="D",
        markersize=7,
        label="pgbench_accounts_pkey",
        zorder=4,
    )
    ax.plot(
        df["db_gb"],
        df["avg_usage"],
        color=CACHE_COLOR,
        linewidth=2.2,
        marker="o",
        markersize=8,
        label="Whole cache",
        zorder=3,
    )

    ax.axvline(48, color="#666666", linestyle=":", linewidth=1.4, zorder=1)
    ax.text(
        580,
        2.85,
        "shared_buffers=48GB",
        ha="center",
        va="center",
        fontsize=14,
        color="#444444",
        clip_on=False,
    )

    ax.set_xlabel("Database size (GB)")
    ax.set_ylabel("Average usage count")
    ax.set_title("Buffer cache usage count vs working-set size")
    ax.set_ylim(0, 5.4)
    ax.set_xlim(left=0)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", framealpha=0.92)
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(df)} scales, rising set 65 @ 128 clients)")
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    args = parse_args()
    df = prepare_df(fetch_sql_table(args.sql, args.conn))
    plot_usage(df, args.output, show=args.show)


if __name__ == "__main__":
    main()
