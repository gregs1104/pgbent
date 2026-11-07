#!/usr/bin/env python3
"""
Starter pgbench SELECT leaderboard from siren PG19 rc1.

Graphs TPS and transactions/joule vs clients for the four conn_method
faces (sockets vs localhost TCP, prepared vs simple), a cross-platform
energy comparison for the four reference systems, and writes both into
docs/leaderboards/select-performance-power.md.

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
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import (
    BAR_LABEL_FONTSIZE,
    LEADERBOARD_LEGEND_FONTSIZE,
    LEADERBOARD_Y_LABEL_FONTSIZE,
    use_pg18_style,
)
from release_paths import REPO_ROOT

DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "select-leaderboard.sql"
PLATFORM_SQL_PATH = REPO_ROOT / "reports" / "select-platform.sql"
POWER_PAGE = REPO_ROOT / "docs" / "leaderboards" / "select-performance-power.md"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "select-leaderboard.png"
JOULES_IMAGE = REPO_ROOT / "docs" / "images" / "select-leaderboard-joules.png"
COMPARE_IMAGE = REPO_ROOT / "docs" / "images" / "select-leaderboard-compare.png"
BLOCK_BEGIN = "<!-- select-leaderboard:begin -->"
BLOCK_END = "<!-- select-leaderboard:end -->"
COMPARE_BEGIN = "<!-- select-platform-compare:begin -->"
COMPARE_END = "<!-- select-platform-compare:end -->"

TPS_COLOR = "#e4572e"
TPS1_COLOR = "#f4a261"
EFF_COLOR = "#4c78a8"
ENERGY_COLOR = "#2a9d8f"
BAR_LABEL_INSIDE_COLOR = "#ffffff"
BAR_LABEL_OUTSIDE_COLOR = "#333333"

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
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Query the results DB and update docs/leaderboards/select-performance-power.md",
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--platform-sql", type=Path, default=PLATFORM_SQL_PATH)
    parser.add_argument("--page", type=Path, default=POWER_PAGE)
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
    raise SystemExit(f"Missing {begin} / {end} markers in select performance-power page")


def plain_axis(ax, y: bool = False, x: bool = True) -> None:
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    if y:
        ax.yaxis.set_major_formatter(formatter)
    if x:
        ax.xaxis.set_major_formatter(formatter)


def _contrast_text_color(hex_color: str) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return BAR_LABEL_INSIDE_COLOR
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return BAR_LABEL_INSIDE_COLOR if luminance < 0.55 else BAR_LABEL_OUTSIDE_COLOR


def _text_width_data(ax, text: str, fontsize: float, renderer) -> float:
    probe = ax.text(0, 0, text, fontsize=fontsize, alpha=0.0)
    ax.figure.canvas.draw()
    bbox = probe.get_window_extent(renderer)
    probe.remove()
    x0, _ = ax.transData.inverted().transform((bbox.x0, bbox.y0))
    x1, _ = ax.transData.inverted().transform((bbox.x1, bbox.y1))
    return abs(x1 - x0)


def _label_barh_values(ax, items: list[tuple], fontsize: float = BAR_LABEL_FONTSIZE) -> None:
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    xmax = max(item[1] for item in items)
    pad = max(xmax * 0.02, 2)
    inner_pad = max(xmax * 0.015, 1.5)
    max_x = xmax
    for yi, width, color, label in items:
        text_width = _text_width_data(ax, label, fontsize, renderer)
        if text_width + inner_pad * 2 <= width:
            ax.text(
                width - inner_pad,
                yi,
                label,
                va="center",
                ha="right",
                fontsize=fontsize,
                color=_contrast_text_color(color),
                clip_on=True,
            )
            max_x = max(max_x, width)
        else:
            x = width + pad
            outside_width = _text_width_data(ax, label, fontsize, renderer)
            ax.text(
                x,
                yi,
                label,
                va="center",
                ha="left",
                fontsize=fontsize,
                color=BAR_LABEL_OUTSIDE_COLOR,
                clip_on=True,
            )
            max_x = max(max_x, x + outside_width)
    ax.set_xlim(0, max_x + pad)


def _pct_of_leader(series: pd.Series, leader_value: float) -> pd.Series:
    if leader_value is None or leader_value <= 0:
        return series * 0
    return series / leader_value * 100.0


def platform_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["cpu", "tps_1", "txn_j_1", "tps_32", "txn_j_32", "kj_32"]
    out = df[cols].copy()
    out = out.rename(
        columns={
            "tps_1": "tps_1",
            "txn_j_1": "txn_j_1",
            "tps_32": "tps_32",
            "txn_j_32": "txn_j_32",
            "kj_32": "kJ_32",
        }
    )
    return out


def platform_dataframe_to_markdown(df: pd.DataFrame) -> str:
    display = df.copy()
    for col in ("tps_1", "txn_j_1", "tps_32", "txn_j_32"):
        display[col] = display[col].map(format_tps)
    display["kJ_32"] = display["kJ_32"].map(
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


def plot_platform_compare(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    plot_df = df.dropna(subset=["tps_1", "tps_32", "txn_j_32", "kj_32"]).copy()
    plot_df = plot_df.sort_values("tps_32", ascending=True).reset_index(drop=True)
    if plot_df.empty:
        raise SystemExit("No platform rows for the SELECT comparison chart")

    leader = plot_df.loc[plot_df["tps_32"].idxmax()]
    tps32_pct = _pct_of_leader(plot_df["tps_32"], float(leader["tps_32"]))
    tps1_pct = _pct_of_leader(plot_df["tps_1"], float(leader["tps_1"]))
    txn_pct = _pct_of_leader(plot_df["txn_j_32"], float(leader["txn_j_32"]))
    kj_pct = _pct_of_leader(plot_df["kj_32"], float(leader["kj_32"]))
    n = len(plot_df)
    y = list(range(n))
    bar_h = 0.18
    # Single-client first, then the three @32 metrics together in legend + bars.
    series = (
        (tps1_pct, [i + 1.5 * bar_h for i in y], TPS1_COLOR, "TPS @ 1", plot_df["tps_1"], "{:,.0f}"),
        (tps32_pct, [i + 0.5 * bar_h for i in y], TPS_COLOR, "TPS @ 32", plot_df["tps_32"], "{:,.0f}"),
        (txn_pct, [i - 0.5 * bar_h for i in y], EFF_COLOR, "txn/J @ 32", plot_df["txn_j_32"], "{:,.0f}/J"),
        (kj_pct, [i - 1.5 * bar_h for i in y], ENERGY_COLOR, "kJ @ 32", plot_df["kj_32"], "{:,.1f} kJ"),
    )

    use_pg18_style()
    fig, ax = plt.subplots(figsize=(11, max(5.5, 1.55 * n + 1.8)))
    items: list[tuple[float, float, str, str]] = []
    for widths, ys, color, label, raw, fmt in series:
        ax.barh(ys, widths, height=bar_h, color=color, label=label)
        for yi, width, value in zip(ys, widths, raw):
            items.append((yi, float(width), color, fmt.format(float(value))))

    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["cpu"], fontsize=LEADERBOARD_Y_LABEL_FONTSIZE)
    ax.set_xlabel("% Relative to the lead system, on that metric")
    ax.set_title("pgbench SELECT - Platform energy comparison")
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.grid(True, axis="x", which="major", linestyle="--", alpha=0.4)
    ax.grid(True, axis="x", which="minor", linestyle=":", alpha=0.25)
    plain_axis(ax)
    _label_barh_values(ax, items)
    ax.legend(
        loc="lower right",
        ncol=1,
        fontsize=LEADERBOARD_LEGEND_FONTSIZE,
        framealpha=0.92,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({n} systems)")
    if show:
        plt.show()
    plt.close(fig)


def compare_markdown(table_md: str, n_systems: int) -> str:
    abbey_note = ""
    if n_systems < 4:
        abbey_note = (
            "**Apple M4 Max Studio** (abbey) is waiting on its PG18 SELECT pin — "
            "the chart grows when that cell lands.\n\n"
        )
    return (
        f"{COMPARE_BEGIN}\n\n"
        "One chart for the best **sockets prepared** run on each machine at "
        "**1** and **32** clients. Bar length is relative to the lead system on "
        "that metric (**100%** = that system's value). Labels are the raw "
        "values. A longer **kJ** bar means more energy used, not more "
        "efficiency. **txn/J** is transactions per joule on the same 32-client "
        "run — total transactions over total package joules.\n\n"
        f"{abbey_note}"
        "![pgbench SELECT - Platform energy comparison]"
        "({{ '/images/select-leaderboard-compare.png' | relative_url }})\n\n"
        f"{table_md}\n\n"
        f"{COMPARE_END}"
    )


def block_markdown(table_md: str, n_faces: int) -> str:
    # Chart-first layout matches docs/leaderboards/select-performance-power.md
    return (
        f"{BLOCK_BEGIN}\n\n"
        "![pgbench SELECT - Siren 9950X]({{ '/images/select-leaderboard.png' | relative_url }})\n\n"
        "Starter board from **siren** (R9 9950X), PostgreSQL **19rc1** "
        "(rc1 2026-10-15, catalog 20261006), scale 100, 90s. Same box, four faces "
        "of the connection sweep: unix sockets vs localhost TCP, simple vs "
        "`-M prepared`. Peak is **32 clients**, sockets prepared (**2.06M TPS**). "
        "Localhost TCP prepared sits at **1.52M** (~26% below sockets). Package "
        "watts: 1-client is ~**62 W**; from 16 clients up the 9950X sits on the "
        "**~200 W PPT** rail (RAPL avg **199.6**, not a copied 200).\n\n"
        "Package power sits on the same row as TPS on the **sockets** face (one "
        "machine, complete accounting). Combining client and server watts across "
        "boxes is out of scope—that's the harder to observe data center shaped "
        "problem. **Transactions per joule** is the energy-efficiency number for "
        "each client count — the same 1-second `PkgWatt` integral as OSM kJ. "
        "Better performance is also more work per watt-second; the PG community "
        "cares about that as a virtuous side effect of code improvements, so this "
        "lab publishes it.\n\n"
        "At 32 clients every face burns ~**17.8 kJ** in 90s — the sum of the 200W "
        "PPT rail. Sockets prepared does **10,406** txn/J; localhost TCP simple "
        "does **5,040**. Same joules, twice the work. Energy efficiency is the "
        "other side of the protocol fan. Better performance spends the same "
        "watt-seconds on more useful work.\n\n"
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

    platform = fetch_sql_table(args.platform_sql, args.conn)
    for col in ("tps_1", "tps_32", "txn_j_1", "txn_j_32", "kj_32", "joules_1", "joules_32"):
        if col in platform.columns:
            platform[col] = pd.to_numeric(platform[col])
    plot_platform_compare(platform, COMPARE_IMAGE, show=args.show)
    platform_md = platform_dataframe_to_markdown(platform_table(platform))
    compare_inner = compare_markdown(platform_md, n_systems=len(platform))

    text = args.page.read_text(encoding="utf-8")
    text = replace_marked_block(text, BLOCK_BEGIN, BLOCK_END, block_markdown(table_md, n_faces=len(ranking)))
    text = replace_marked_block(text, COMPARE_BEGIN, COMPARE_END, compare_inner)
    args.page.write_text(text, encoding="utf-8")
    print(f"Wrote {len(ranking)} faces + {len(platform)} platforms into {args.page}")


if __name__ == "__main__":
    main()
