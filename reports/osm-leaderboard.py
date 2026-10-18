#!/usr/bin/env python3
"""
Graph OSM leaderboard results.

Default: read a release's static snapshot (PG18) and write the matching PNG.

`--from-db` runs `reports/osm-leaderboard.sql` against the results database,
writes the ranked table into `docs/leaderboards.md`, and plots
`docs/images/osm-leaderboard.png`. That is the public-page path; it does not
go through Streamlit.

Usage:
  python3 reports/osm-leaderboard.py
  python3 reports/osm-leaderboard.py --pg 19
  python3 reports/osm-leaderboard.py --from-db
"""

from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, LEADERBOARD_Y_LABEL_FONTSIZE, use_pg18_style
from release_paths import REPO_ROOT, add_pg_argument, image_path, snapshot_path

NODES_COLOR = "#e4572e"
INDEX_COLOR = "#4c78a8"
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "osm-leaderboard.sql"
LEADERBOARD_PAGE = REPO_ROOT / "docs" / "leaderboards.md"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "osm-leaderboard.png"
TABLE_BEGIN = "<!-- osm-leaderboard-table:begin -->"
TABLE_END = "<!-- osm-leaderboard-table:end -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot OSM leaderboard")
    add_pg_argument(parser)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Run osm-leaderboard.sql and populate docs/leaderboards.md",
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--page", type=Path, default=LEADERBOARD_PAGE)
    parser.add_argument("--no-page", action="store_true", help="Skip writing the Markdown page")
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    args = parser.parse_args()
    if args.from_db:
        args.output = args.output or PUBLIC_IMAGE
    else:
        args.snapshot = args.snapshot or snapshot_path(args.pg, "osm-leaderboard")
        args.output = args.output or image_path(args.pg, "osm-leaderboard")
    return args


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def config_label(row: pd.Series) -> str:
    """Two-line label: cpu and memory, then disk on its own line."""
    mem = int(row["mem_gb"])
    disk = str(row["disk"]).strip()
    return f"{row['cpu']} · {mem}GB\n{disk}"


def prepare_leaderboard_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("mem_gb", "overall_kips", "score_kips", "index_kips", "ver", "hours", "max_wal_gb"):
        if col in df.columns:
            df[col] = numeric(df[col])
    df["disk"] = df["disk"].str.strip()
    df = df[df["conn"].astype(str).str.strip().str.lower() == "host"]

    rank_cols = (
        ["score_kips", "overall_kips", "index_kips"]
        if "score_kips" in df.columns
        else ["overall_kips", "index_kips"]
    )
    best = (
        df.sort_values(rank_cols, ascending=False)
        .groupby(["cpu", "mem_gb", "disk"], as_index=False)
        .first()
    )
    best["label"] = best.apply(config_label, axis=1)
    sort_col = "score_kips" if "score_kips" in best.columns else "overall_kips"
    return best.sort_values(sort_col, ascending=True).reset_index(drop=True)


def plain_axis(ax, y: bool = False, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def plot_leaderboard(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    height = max(6, 0.52 * len(df) + 1.5)
    fig, ax = plt.subplots(figsize=(10, height))
    y = range(len(df))
    bar_height = 0.35

    ax.barh(
        [i - bar_height / 2 for i in y],
        df["overall_kips"],
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
    ax.set_yticklabels(
        df["label"],
        fontsize=LEADERBOARD_Y_LABEL_FONTSIZE,
        linespacing=0.95,
    )
    ax.set_xlabel("OSM load throughput (kNodes/s)")
    ax.set_title("PostgreSQL OSM load leaderboard")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", fontsize=LEADERBOARD_LEGEND_FONTSIZE, markerscale=0.75)
    plain_axis(ax)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(df)} configurations)")
    if show:
        plt.show()
    plt.close(fig)


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


def format_markdown_cell(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return f"{val:g}"
    text = str(val)
    if text in ("nan", "NaN", "<NA>"):
        return ""
    return text.replace("|", "\\|")


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        cells = [format_markdown_cell(val) for val in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def records_from_frame(df: pd.DataFrame) -> list[dict[str, str]]:
    filled = df.where(pd.notnull(df), "")
    return [{str(k): str(v) for k, v in row.items()} for row in filled.to_dict(orient="records")]


def write_leaderboard_page(page: Path, table_md: str, n_rows: int) -> None:
    text = page.read_text(encoding="utf-8")
    inner = f"{TABLE_BEGIN}\n\n_Query returned {n_rows} rows._\n\n{table_md}\n\n{TABLE_END}"
    if TABLE_BEGIN in text and TABLE_END in text:
        text = re.sub(
            re.escape(TABLE_BEGIN) + r".*?" + re.escape(TABLE_END),
            inner,
            text,
            count=1,
            flags=re.S,
        )
    else:
        raise SystemExit(f"Missing {TABLE_BEGIN} / {TABLE_END} markers in {page}")
    page.write_text(text, encoding="utf-8")
    print(f"Wrote {n_rows} rows into {page}")


def main() -> int:
    use_pg18_style()
    args = parse_args()
    if args.from_db:
        table = fetch_sql_table(args.sql, args.conn)
        if not args.no_page:
            write_leaderboard_page(args.page, dataframe_to_markdown(table), len(table))
        rows = records_from_frame(table)
    else:
        rows = load_snapshot_table(args.snapshot)
        if not rows:
            raise SystemExit(f"No table found in {args.snapshot}")
    df = prepare_leaderboard_df(rows)
    plot_leaderboard(df, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
