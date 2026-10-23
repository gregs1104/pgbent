#!/usr/bin/env python3
"""
OSM peak disk R/W history by reconstructed CPU across PostgreSQL majors.

Best per (cpu, major) of max(max_write_mbps, max_read_mbps) from host-local
osm2pgsql runs. Same CPU reconstruction and x86 filter as osm-history.py.

Usage:
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/osm-disk-history.py
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

SQL_PATH = REPO_ROOT / "reports" / "osm-disk-history.sql"
PUBLIC_IMAGE = REPO_ROOT / "docs" / "images" / "osm-disk-history.png"
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

CPU_COLORS: dict[str, str] = {
    "R9 5950X": "#D4A017",
    "R9 7700X": "#C44E52",
    "R9 9700X": "#8B0000",
    "R9 9950X": "#ED1C24",
    "R5 9600X": "#FF7F50",
    "i5-13600K": "#0071C5",
}

_SKIP_CPUS = frozenset({"i3-13100", "i9-14900K"})
MARKERS = ("o", "s", "D", "^", "v", "P", "X", "*", "h", "p")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot OSM peak disk R/W history by CPU × PG major"
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


def reconstruct_cpu(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["batch"] = out["batch"].fillna("")
    out["cpu"] = out["cpu"].fillna("").astype(str).str.strip()
    out["server_cpu"] = out["server_cpu"].fillna("").astype(str).str.strip()
    out = out.sort_values(["server", "run", "batch_id", "test"]).reset_index(drop=True)

    hist: list[str] = []
    carried: dict[str, str] = {}
    for row in out.itertuples(index=False):
        server = str(row.server)
        from_batch = parse_cpu_from_batch(row.batch)
        stamped = normalize_cpu(row.cpu)
        server_fb = normalize_cpu(row.server_cpu)

        if from_batch:
            cpu = from_batch
            if not is_cross_host(row.batch):
                carried[server] = cpu
        elif server in carried:
            cpu = carried[server]
        elif stamped and (stamped.startswith("i") or stamped.startswith("R5")):
            cpu = stamped
            carried[server] = cpu
        elif server_fb:
            cpu = server_fb
            carried[server] = cpu
        elif stamped:
            cpu = stamped
            carried[server] = cpu
        else:
            cpu = "unknown"
        hist.append(cpu)

    out["cpu_hist"] = hist
    return out


def is_x86(cpu: str) -> bool:
    name = str(cpu or "")
    if name in _SKIP_CPUS:
        return False
    return name.startswith("R") or name.startswith("i")


def best_by_cpu_major(df: pd.DataFrame) -> pd.DataFrame:
    work = df[~df["batch"].map(is_cross_host)].copy()
    work = work[work["cpu_hist"] != "unknown"]
    work = work[work["cpu_hist"].map(is_x86)]
    work["major"] = pd.to_numeric(work["major"], errors="coerce")
    work["max_rw_mbps"] = pd.to_numeric(work["max_rw_mbps"], errors="coerce")
    work = work.dropna(subset=["major", "max_rw_mbps"])
    work = work[work["max_rw_mbps"] > 0]
    work["major"] = work["major"].astype(int)
    best = (
        work.sort_values("max_rw_mbps", ascending=False)
        .groupby(["cpu_hist", "major"], as_index=False)
        .first()
    )
    return best.sort_values(["cpu_hist", "major"]).reset_index(drop=True)


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
        key=lambda c: (-best.loc[best["cpu_hist"] == c, "max_rw_mbps"].max(), c),
    )
    for i, cpu in enumerate(cpus):
        pts = best[best["cpu_hist"] == cpu].sort_values("major")
        ax.plot(
            pts["major"],
            pts["max_rw_mbps"],
            color=cpu_color(cpu),
            marker=MARKERS[i % len(MARKERS)],
            linewidth=2.0,
            markersize=9,
            label=cpu,
        )

    majors = sorted(best["major"].unique())
    ax.set_xticks(majors)
    ax.set_xlabel("PostgreSQL major")
    ax.set_ylabel("Best peak disk R/W (MB/s)")
    ax.set_title("OSM load peak disk throughput by x86 CPU across PostgreSQL releases")
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
        raise SystemExit("No points after CPU reconstruction and filters")
    summary = (
        best.groupby("cpu_hist")["major"]
        .agg(["min", "max", "count"])
        .rename(columns={"min": "first_major", "max": "last_major", "count": "majors"})
    )
    print(summary.to_string())
    print()
    cols = ["cpu_hist", "major", "max_rw_mbps", "max_write_mbps", "max_read_mbps", "server", "batch_id", "batch"]
    print(best[cols].to_string(index=False))
    plot_history(best, args.output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
