#!/usr/bin/env python3
"""
pgbench SELECT TPS history by CPU across PostgreSQL majors.

Only the sockets-prepared face — matching the public leaderboard cell.
Face comes from tests.conn_method when present, else from set/batch names
(older archives had no conn column). CPU labels reuse the OSM history
reconstruction rules. SQL reads tests/testset directly (after ./download);
a submission rebuild is not required for this chart.

Usage:
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/select-history.py
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
import matplotlib.ticker as mticker
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg18_style import LEADERBOARD_LEGEND_FONTSIZE, use_pg18_style
from release_paths import REPO_ROOT

SQL_PATH = REPO_ROOT / "reports" / "select-history.sql"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "select-history.png"
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"

_BATCH_CPU_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\b9950X\b"), "R9 9950X"),
    (re.compile(r"(?i)\b9700X\b"), "R9 9700X"),
    (re.compile(r"(?i)\b7700X\b"), "R9 7700X"),
    (re.compile(r"(?i)\b9600X\b"), "R5 9600X"),
    (re.compile(r"(?i)\b5950X\b"), "R9 5950X"),
    (re.compile(r"(?i)\b3950X\b"), "R9 3950X"),
    (re.compile(r"(?i)\bi?9-?14900K\b"), "i9-14900K"),
    (re.compile(r"(?i)\b14900K\b"), "i9-14900K"),
    (re.compile(r"(?i)\bi?5-?13600K\b"), "i5-13600K"),
    (re.compile(r"(?i)\b13600K\b"), "i5-13600K"),
    (re.compile(r"(?i)\bi?3-?13100K?\b"), "i3-13100"),
    (re.compile(r"(?i)\b13100K\b"), "i3-13100"),
]

_CROSS_HOST = re.compile(
    r"(?i)(\bClient\b|^Server\s+\w+|\bC\s+\w+\s+S\s+\w+|\w+\s+C\s+\w+\s+S\b|"
    r"Two\s+Server)"
)
_SOCKETS_PREPARED = re.compile(r"(?i)Sockets\s+Prepared")
_BATCH_MAJOR = re.compile(r"(?i)\bPG\s*([0-9]+)")

CPU_COLORS: dict[str, str] = {
    "R9 3950X": "#A0522D",
    "R9 5950X": "#D4A017",
    "R9 7700X": "#C44E52",
    "R9 9700X": "#8B0000",
    "R9 9950X": "#ED1C24",
    "R5 9600X": "#FF7F50",
    "i9-14900K": "#003D7A",
    "i5-13600K": "#0071C5",
    "i3-13100": "#5BA3D9",
}

MARKERS = ("o", "s", "D", "^", "v", "P", "X", "*", "h", "p")

# Optional provisional points if a cpu × major cell is still missing from
# results (or was dropped via SKIP). Empty once fair DB rows cover the series.
PLACEHOLDER_POINTS: list[dict] = []

# Omit from the published higher-highs chart (archives kept; see Leaderboards note).
SKIP_CPU_MAJOR: set[tuple[str, int]] = {
    ("R9 5950X", 15),  # log_min_duration_statement=0 false negative
    ("i9-14900K", 16),  # suspect archive
    ("i5-13600K", 15),  # orphan twilight; not a priority to four-face map
    ("i5-13600K", 19),  # single rc1 face peak; wait for a 9950X-style series
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot sockets-prepared SELECT TPS history by CPU × PG major"
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--output", type=Path, default=PUBLIC_IMAGE)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
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


def parse_cpu_from_batch(batch: str) -> str | None:
    text = str(batch or "")
    for pattern, label in _BATCH_CPU_PATTERNS:
        if pattern.search(text):
            return label
    return None


def normalize_cpu(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    from_batch = parse_cpu_from_batch(text)
    if from_batch:
        return from_batch
    return text


def is_cross_host(batch: str) -> bool:
    return bool(_CROSS_HOST.search(str(batch or "")))


def is_sockets_prepared(conn: str, batch: str) -> bool:
    c = str(conn or "").strip().lower()
    if c == "sockets prepared":
        return True
    # Older archives: face only in the set name.
    return bool(_SOCKETS_PREPARED.search(str(batch or "")))


def batch_major(batch: str) -> int | None:
    m = _BATCH_MAJOR.search(str(batch or ""))
    if not m:
        return None
    return int(m.group(1))


def reconstruct_cpu(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["batch"] = out["batch"].fillna("")
    out["cpu"] = out["cpu"].fillna("").astype(str).str.strip()
    out["server_cpu"] = out["server_cpu"].fillna("").astype(str).str.strip()
    out["conn"] = out["conn"].fillna("").astype(str).str.strip()
    out = out.sort_values(["server", "run", "batch_id", "test"]).reset_index(drop=True)

    hist: list[str] = []
    carried: dict[str, str] = {}
    for row in out.itertuples(index=False):
        server = str(row.server)
        from_batch = parse_cpu_from_batch(row.batch)
        stamped = normalize_cpu(row.cpu)
        server_fb = normalize_cpu(row.server_cpu)

        # Prefer an explicit set-name chip, then the stamped cpu on the row.
        # Do not let an older carry (e.g. siren 7700X SELECT sets) override a
        # later stamped identity on the same chassis.
        if from_batch:
            cpu = from_batch
            if not is_cross_host(row.batch):
                carried[server] = cpu
        elif stamped:
            cpu = stamped
            carried[server] = cpu
        elif server in carried:
            cpu = carried[server]
        elif server_fb:
            cpu = server_fb
            carried[server] = cpu
        else:
            cpu = "unknown"
        hist.append(cpu)

    out["cpu_hist"] = hist
    return out


def is_x86(cpu: str) -> bool:
    name = str(cpu or "")
    return name.startswith("R") or name.startswith("i")


def best_by_cpu_major(df: pd.DataFrame) -> pd.DataFrame:
    work = df[~df["batch"].map(is_cross_host)].copy()
    work = work[work.apply(lambda r: is_sockets_prepared(r["conn"], r["batch"]), axis=1)]
    work = work[work["cpu_hist"] != "unknown"]
    work = work[work["cpu_hist"].map(is_x86)]

    # Prefer server_ver major. When conn was blank, a PG## in the set name is
    # the better pin label (rising PG14.8 prepared sat in a 15.3 server_ver).
    work["major"] = pd.to_numeric(work["major"], errors="coerce")
    blank_conn = work["conn"].fillna("").astype(str).str.strip() == ""
    named = work["batch"].map(batch_major)
    work.loc[blank_conn & named.notna(), "major"] = named[blank_conn & named.notna()]
    work["tps"] = pd.to_numeric(work["tps"], errors="coerce")
    work = work.dropna(subset=["major", "tps"])
    work["major"] = work["major"].astype(int)

    best = (
        work.sort_values("tps", ascending=False)
        .groupby(["cpu_hist", "major"], as_index=False)
        .first()
    )
    best = drop_skipped(best)
    return apply_placeholders(best)


def drop_skipped(best: pd.DataFrame) -> pd.DataFrame:
    if best.empty or not SKIP_CPU_MAJOR:
        return best
    mask = []
    for row in best.itertuples(index=False):
        key = (row.cpu_hist, int(row.major))
        if key in SKIP_CPU_MAJOR:
            print(
                f"skip: {row.cpu_hist} PG{int(row.major)} "
                f"{float(row.tps):,.0f} TPS (omitted from chart)"
            )
            mask.append(False)
        else:
            mask.append(True)
    return best.loc[mask].reset_index(drop=True)


def apply_placeholders(best: pd.DataFrame) -> pd.DataFrame:
    """Fill missing cpu × major cells from PLACEHOLDER_POINTS; replace DB only when higher."""
    if not PLACEHOLDER_POINTS:
        return best.sort_values(["cpu_hist", "major"]).reset_index(drop=True)
    out = best.copy()
    for ph in PLACEHOLDER_POINTS:
        key_m = (out["cpu_hist"] == ph["cpu_hist"]) & (out["major"].astype(int) == int(ph["major"]))
        if key_m.any():
            cur = float(out.loc[key_m, "tps"].iloc[0])
            if float(ph["tps"]) <= cur:
                continue
            out = out.loc[~key_m].reset_index(drop=True)
            print(
                f"placeholder: {ph['cpu_hist']} PG{ph['major']} "
                f"{float(ph['tps']):,.0f} TPS replaces {cur:,.0f} "
                f"({ph.get('batch', 'provisional')})"
            )
        else:
            print(
                f"placeholder: {ph['cpu_hist']} PG{ph['major']} "
                f"{float(ph['tps']):,.0f} TPS ({ph.get('batch', 'provisional')})"
            )
        out = pd.concat([out, pd.DataFrame([ph])], ignore_index=True, sort=False)
    return out.sort_values(["cpu_hist", "major"]).reset_index(drop=True)


def cpu_color(cpu: str) -> str:
    if cpu in CPU_COLORS:
        return CPU_COLORS[cpu]
    if str(cpu)[:1] == "i":
        return "#0071C5"
    if str(cpu)[:1] == "R":
        return "#ED1C24"
    return "#333333"


def plot_history(best: pd.DataFrame, output: Path, show: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(11, 7))
    cpus = sorted(
        best["cpu_hist"].unique(),
        key=lambda c: (-best.loc[best["cpu_hist"] == c, "tps"].max(), c),
    )
    for i, cpu in enumerate(cpus):
        pts = best[best["cpu_hist"] == cpu].sort_values("major")
        ax.plot(
            pts["major"],
            pts["tps"],
            color=cpu_color(cpu),
            marker=MARKERS[i % len(MARKERS)],
            linewidth=2.0,
            markersize=9,
            label=cpu,
        )

    majors = sorted(best["major"].unique())
    ax.set_xticks(majors)
    ax.set_xlabel("PostgreSQL major")
    ax.set_ylabel("Best SELECT TPS (sockets prepared)")
    ax.set_title("pgbench SELECT by x86 CPU across PostgreSQL releases")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _pos: f"{x/1e6:.2f}M" if x >= 1e6 else f"{x/1e3:.0f}k"))
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax.legend(
        loc="upper left",
        fontsize=LEADERBOARD_LEGEND_FONTSIZE,
        framealpha=0.92,
        ncol=1,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output} ({len(cpus)} CPUs, {len(best)} points)")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    use_pg18_style()
    args = parse_args()
    raw = fetch_sql_table(args.sql, args.conn)
    hist = reconstruct_cpu(raw)
    best = best_by_cpu_major(hist)
    if best.empty:
        raise SystemExit("No sockets-prepared SELECT points after filters")
    summary = (
        best.groupby("cpu_hist")["major"]
        .agg(["min", "max", "count"])
        .rename(columns={"min": "first_major", "max": "last_major", "count": "majors"})
    )
    print(summary.to_string())
    print()
    print(
        best[["cpu_hist", "major", "tps", "server", "batch_id", "batch", "conn"]]
        .assign(tps=lambda d: d["tps"].map(lambda v: f"{float(v):,.0f}"))
        .to_string(index=False)
    )
    plot_history(best, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
