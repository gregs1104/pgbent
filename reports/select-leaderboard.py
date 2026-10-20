#!/usr/bin/env python3
"""
Starter pgbench SELECT leaderboard from siren PG19 rc1.

Graphs TPS and transactions/joule vs clients for the four conn_method
faces (sockets vs localhost TCP, prepared vs simple) and writes a compact
1-client / 32-client table into docs/leaderboards.md.

Usage:
    python3 reports/select-leaderboard.py --from-db
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, use_pg18_style
from release_paths import REPO_ROOT

DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "select-leaderboard.sql"
LEADERBOARD_PAGE = REPO_ROOT / "docs" / "leaderboards.md"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "select-leaderboard.png"
JOULES_IMAGE = REPO_ROOT / "docs" / "images" / "select-leaderboard-joules.png"
BLOCK_BEGIN = "<!-- select-leaderboard:begin -->"
BLOCK_END = "<!-- select-leaderboard:end -->"

# Prepared = solid, simple = dashed. Sockets vs TCP by color.
SERIES = (
    ("sockets prepared", "#e4572e", "-"),
    ("host prepared", "#4c78a8", "-"),
    ("sockets", "#e4572e", "--"),
    ("host", "#4c78a8", "--"),
)
CONN_LABEL = {
    "sockets prepared": "sockets prepared",
    "host prepared": "localhost TCP prepared",
    "sockets": "sockets",
    "host": "localhost TCP",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot starter pgbench SELECT leaderboard")
    parser.add_argument("--from-db", action="store_true", help="Query the results DB and update docs/leaderboards.md")
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--page", type=Path, default=LEADERBOARD_PAGE)
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


def format_tps(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return f"{int(round(float(val))):,}"


def ranking_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for conn, _, _ in SERIES:
        face = df[df["conn"] == conn]
        if face.empty:
            continue
        one = face.loc[face["clients"] == 1]
        peak = face.loc[face["clients"] == 32]
        if one.empty or peak.empty:
            continue
        rows.append(
            {
                "conn": CONN_LABEL.get(conn, conn),
                "tps_1": int(one.iloc[0]["tps"]),
                "pkg_1": one.iloc[0]["avg_pkg"],
                "txn_j_1": one.iloc[0]["txn_per_j"],
                "tps_32": int(peak.iloc[0]["tps"]),
                "pkg_32": peak.iloc[0]["avg_pkg"],
                "txn_j_32": peak.iloc[0]["txn_per_j"],
            }
        )
    out = pd.DataFrame(rows).sort_values("tps_32", ascending=False)
    return out


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    display = df.copy()
    for col in ("tps_1", "tps_32", "txn_j_1", "txn_j_32"):
        display[col] = display[col].map(format_tps)
    for col in ("pkg_1", "pkg_32"):
        display[col] = display[col].map(
            lambda v: "" if pd.isna(v) else f"{float(v):.1f}".rstrip("0").rstrip(".")
        )
    cols = [str(c) for c in display.columns]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def plot_select(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    use_pg18_style()
    fig, ax = plt.subplots(figsize=(11, 6.5))
    plotted = 0
    for conn, color, style in SERIES:
        face = df[df["conn"] == conn].sort_values("clients")
        if face.empty:
            continue
        ax.plot(
            face["clients"],
            face["tps"],
            color=color,
            linestyle=style,
            marker="o",
            linewidth=2.4,
            markersize=8,
            label=CONN_LABEL.get(conn, conn),
        )
        plotted += 1
    if plotted == 0:
        raise SystemExit("No conn_method series to plot")
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(df["clients"].unique()))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlabel("Clients")
    ax.set_ylabel("TPS")
    ax.set_title("pgbench SELECT - Siren 9950X")
    ax.grid(True, which="major", linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", fontsize=LEADERBOARD_LEGEND_FONTSIZE, framealpha=0.92)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def plot_txn_per_joule(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    use_pg18_style()
    fig, ax = plt.subplots(figsize=(11, 6.5))
    plotted = 0
    for conn, color, style in SERIES:
        face = df[df["conn"] == conn].sort_values("clients")
        if face.empty or face["txn_per_j"].isna().all():
            continue
        ax.plot(
            face["clients"],
            face["txn_per_j"],
            color=color,
            linestyle=style,
            marker="o",
            linewidth=2.4,
            markersize=8,
            label=CONN_LABEL.get(conn, conn),
        )
        plotted += 1
    if plotted == 0:
        raise SystemExit("No txn/joule series to plot")
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(df["clients"].unique()))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_xlabel("Clients")
    ax.set_ylabel("Transactions / joule")
    ax.set_title("pgbench SELECT - Siren 9950X energy")
    ax.grid(True, which="major", linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=LEADERBOARD_LEGEND_FONTSIZE, framealpha=0.92)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def replace_marked_block(text: str, begin: str, end: str, inner: str) -> str:
    if begin in text and end in text:
        return re.sub(
            re.escape(begin) + r".*?" + re.escape(end),
            inner,
            text,
            count=1,
            flags=re.S,
        )
    raise SystemExit(f"Missing {begin} / {end} markers in leaderboard page")


def block_markdown(table_md: str, n_faces: int) -> str:
    return (
        f"{BLOCK_BEGIN}\n\n"
        "Starter board from **siren** (R9 9950X), PostgreSQL **19rc1** "
        "(published **2026-10-20**, the day after the rc1 catalog bump), scale 100, "
        "90s. Same box, four faces of the connection sweep (PG18 study, kept as a "
        "code exercise): unix sockets vs localhost TCP, simple vs `-M prepared`. "
        "Peak is **32 clients**, sockets prepared (**2.06M TPS**). Localhost TCP "
        "prepared sits at **1.52M** (~26% below sockets). Package watts: 1-client "
        "is ~**62 W**; from 16 clients up the 9950X sits on the **~200 W PPT** "
        "rail (RAPL avg **199.6**, not a copied 200).\n\n"
        "![pgbench SELECT - Siren 9950X]({{ '/images/select-leaderboard.png' | relative_url }})\n\n"
        "**Transactions per joule** uses the same 1-second `PkgWatt` integral as OSM "
        "kJ. At 32 clients every face burns ~**17.8 kJ** in 90s — the PPT rail. "
        "Sockets prepared does **10,406** txn/J; localhost TCP simple does **5,040**. "
        "Same joules, twice the work. Energy efficiency is the other side of the "
        "protocol fan: better performance spends the same watt-seconds on more "
        "useful work.\n\n"
        "![pgbench SELECT - transactions per joule]({{ '/images/select-leaderboard-joules.png' | relative_url }})\n\n"
        f"Mean across repeats ({n_faces} faces). **tps_1** is the old single-core cell; "
        "**tps_32** is the max on this chip. **pkg_*** is average package watts; "
        "**txn_j_*** is transactions per joule on those same runs.\n\n"
        f"{table_md}\n\n"
        f"{BLOCK_END}"
    )


def main() -> None:
    args = parse_args()
    if not args.from_db:
        raise SystemExit("This starter board is generated with --from-db")
    df = fetch_sql_table(args.sql, args.conn)
    df["clients"] = pd.to_numeric(df["clients"])
    df["tps"] = pd.to_numeric(df["tps"])
    df["txn_per_j"] = pd.to_numeric(df["txn_per_j"])
    plot_select(df, args.output, show=args.show)
    plot_txn_per_joule(df, JOULES_IMAGE, show=args.show)
    ranking = ranking_table(df)
    table_md = dataframe_to_markdown(ranking)
    text = args.page.read_text(encoding="utf-8")
    inner = block_markdown(table_md, n_faces=len(ranking))
    args.page.write_text(replace_marked_block(text, BLOCK_BEGIN, BLOCK_END, inner), encoding="utf-8")
    print(f"Wrote {len(ranking)} faces into {args.page}")


if __name__ == "__main__":
    main()
