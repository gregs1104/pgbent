#!/usr/bin/env python3
"""
Graph the twilight set-98 shared_buffers OSM sweep (PG16.3).

Durable (fsync=on / wal_level=replica) points are the fair A/B; fast
(minimal / fsync=off) cells are shown faintly for context. Conclusions still
apply on later majors — the lab standardized on 48GB after this study.

Usage:
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/shared-buffers.py
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
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, use_pg18_style

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "shared-buffers.sql"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "shared-buffers-osm.png"

DURABLE_COLOR = "#4c78a8"
FAST_COLOR = "#e4572e"
MEDIAN_COLOR = "#333333"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot shared_buffers OSM sweep")
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
    for col in ("shared_gb", "hours", "overall_kips"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["shared_gb", "overall_kips"])
    out = out[out["face"].isin(["durable", "fast"])].copy()
    return out.sort_values(["shared_gb", "face", "overall_kips"]).reset_index(drop=True)


def plot_shared_buffers(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    use_pg18_style()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))

    durable = df[df["face"] == "durable"]
    fast = df[df["face"] == "fast"]

    # Slight x jitter so overlapping runs at the same SB stay visible.
    durable_x = durable["shared_gb"].to_numpy(dtype=float).copy()
    for gb in durable["shared_gb"].unique():
        idx = durable["shared_gb"].to_numpy() == gb
        n = int(idx.sum())
        if n > 1:
            durable_x[idx] += (pd.Series(range(n)) - (n - 1) / 2.0).to_numpy() * 0.55
    ax.scatter(
        durable_x,
        durable["overall_kips"],
        s=90,
        c=DURABLE_COLOR,
        zorder=3,
        label="Durable (replica / fsync=on)",
    )
    if not fast.empty:
        ax.scatter(
            fast["shared_gb"],
            fast["overall_kips"],
            s=70,
            c=FAST_COLOR,
            marker="^",
            alpha=0.55,
            zorder=2,
            label="Fast (minimal / fsync=off)",
        )

    med = (
        durable.groupby("shared_gb", as_index=False)["overall_kips"]
        .median()
        .sort_values("shared_gb")
    )
    ax.plot(
        med["shared_gb"],
        med["overall_kips"],
        color=MEDIAN_COLOR,
        linewidth=2,
        marker="D",
        markersize=7,
        zorder=4,
        label="Durable median",
    )

    ax.set_xticks([1, 32, 48])
    ax.set_xlabel("shared_buffers (GB)")
    ax.set_ylabel("OSM total (kNodes/s)")
    ax.set_title("OSM load vs shared_buffers")
    ax.set_xlim(-2, 54)
    y0 = float(df["overall_kips"].min())
    y1 = float(df["overall_kips"].max())
    ax.set_ylim(y0 * 0.92, y1 * 1.08)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)
    ax.legend(loc="lower right", fontsize=LEADERBOARD_LEGEND_FONTSIZE, framealpha=0.92)
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(df)} runs, twilight set 98)")
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    args = parse_args()
    df = prepare_df(fetch_sql_table(args.sql, args.conn))
    plot_shared_buffers(df, args.output, show=args.show)


if __name__ == "__main__":
    main()
