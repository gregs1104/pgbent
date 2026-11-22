#!/usr/bin/env python3
"""
OSM peak disk R/W history by stamped CPU across PostgreSQL majors.

Best per (cpu, major) of max(max_write_mbps, max_read_mbps) from host-local
osm2pgsql runs. Same stamped-CPU path and x86 filter as osm-history.py.

Default chart is retrospective (best peak even after the release write-up).
With --rated-ceiling, the fork adds an at-the-moment hardware ceiling: rated
sequential read of the drive that owned each major's published cycle
(docs/platform/disks.md). PG17 pins to Crucial T705 from the Crunchy write-up;
Fury arrived late. Alternate image: docs/images/osm-disk-history-rated.png.
(i9-14900K briefly hit ~11GB/s on T705 in that blog; it is omitted from the
x86 series after leaving the farm, so PG17's drawn peak is the nearby 13600K.)

Usage:
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/osm-disk-history.py
  MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" \\
    .venv-graph/bin/python reports/osm-disk-history.py --rated-ceiling
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
RATED_IMAGE = REPO_ROOT / "docs" / "images" / "osm-disk-history-rated.png"
DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"

_CPU_ALIASES = {
    "R9 7700X": "R7 7700X",
}

_CROSS_HOST = re.compile(
    r"(?i)(\bClient\b|^Server\s+\w+|\bC\s+\w+\s+S\s+\w+|\w+\s+C\s+\w+\s+S\b|"
    r"Two\s+Server)"
)

CPU_COLORS: dict[str, str] = {
    "R9 5950X": "#D4A017",
    "R7 7700X": "#00FFFF",  # matplotlib cyan — distinct from AMD reds
    "R9 9950X": "#ED1C24",
    "R5 9600X": "#FF7F50",
    "i5-13600K": "#0071C5",
}

_SKIP_CPUS = frozenset({"i3-13100", "i9-14900K"})
MARKERS = ("o", "s", "D", "^", "v", "P", "X", "*", "h", "p")

# Manufacturer rated sequential read (MB/s). Keep in sync with docs/platform/disks.md.
# Apple / Spark OEM omitted — no comparable PCIe marketing number for this overlay.
RATED_SEQ_READ_MBPS: dict[str, int] = {
    "Intel 750p": 2500,
    "Inland Performance 2TB": 5000,
    "Sabrent Rocket 4 Plus 2TB": 7100,
    "SK41 2TB": 7000,
    "Remote SK41 2TB": 7000,
    "FireCuda 530 4TB": 7300,
    "SK51 2TB": 14700,
    "Crucial T705": 14500,
    "Crucial T705 2TB": 14500,
    "T705 2TB": 14500,
    "Fury G5 4TB": 14800,
}

RATED_LINE_COLOR = "#444444"

# Published-cycle overrides for the rated ceiling. Late hardware that still ran
# PostgreSQL N must not own that major's disk story when a public write-up
# already named the drive. PG17: Crucial T705
# (https://www.crunchydata.com/blog/loading-the-world-openstreetmap-import-in-under-4-hours);
# Fury G5 arrived only at the end of that cycle.
RATED_CEILING_OVERRIDE: dict[int, str] = {
    17: "Crucial T705 2TB",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot OSM peak disk R/W history by CPU × PG major"
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument(
        "--rated-ceiling",
        action="store_true",
        help="Overlay rated seq. read of the disk that set each major's best peak",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    args = parser.parse_args()
    if args.output is None:
        args.output = RATED_IMAGE if args.rated_ceiling else PUBLIC_IMAGE
    return args


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


def normalize_cpu(raw: object) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None
    return _CPU_ALIASES.get(text, text)


def is_cross_host(batch: str) -> bool:
    return bool(_CROSS_HOST.search(str(batch or "")))


def stamp_cpu(df: pd.DataFrame) -> pd.DataFrame:
    """Label each row from submission.cpu, falling back to server.server_cpu."""
    out = df.copy()
    out["batch"] = out["batch"].fillna("")
    stamped = out["cpu"].map(normalize_cpu)
    fallback = out["server_cpu"].map(normalize_cpu)
    out["cpu_hist"] = stamped.combine_first(fallback).fillna("unknown")
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


def rated_ceiling_by_major(best: pd.DataFrame) -> pd.DataFrame:
    """Rated seq. read of the disk that set each major's best observed peak.

    Uses the same x86 best-per-CPU points as the chart — not every disk that
    merely appeared. Published-cycle overrides in RATED_CEILING_OVERRIDE win
    when late hardware would otherwise rewrite that major's disk story.
    """
    work = best.copy()
    work["disk"] = work["disk"].fillna("").astype(str).str.strip()
    work["rated_mbps"] = work["disk"].map(RATED_SEQ_READ_MBPS)
    work = work.dropna(subset=["rated_mbps", "max_rw_mbps"])
    if work.empty:
        return pd.DataFrame(columns=["major", "rated_mbps", "disk", "max_rw_mbps"])
    # Disk of the winning peak per major (tie-break: higher rating, then name).
    ranked = work.sort_values(
        ["max_rw_mbps", "rated_mbps", "disk"], ascending=[False, False, True]
    )
    top = ranked.groupby("major", as_index=False).first()
    out = top[["major", "rated_mbps", "disk", "max_rw_mbps"]].copy()
    for major, disk in RATED_CEILING_OVERRIDE.items():
        rated = RATED_SEQ_READ_MBPS.get(disk)
        if rated is None:
            continue
        mask = out["major"] == major
        if mask.any():
            out.loc[mask, "disk"] = disk
            out.loc[mask, "rated_mbps"] = rated
        else:
            out = pd.concat(
                [
                    out,
                    pd.DataFrame(
                        [{"major": major, "rated_mbps": rated, "disk": disk, "max_rw_mbps": pd.NA}]
                    ),
                ],
                ignore_index=True,
            )
    return out.sort_values("major").reset_index(drop=True)


def cpu_color(cpu: str) -> str:
    if cpu in CPU_COLORS:
        return CPU_COLORS[cpu]
    if str(cpu)[:1] == "i":
        return "#0071C5"
    if str(cpu)[:1] == "R":
        return "#ED1C24"
    return "#333333"


def plot_history(
    best: pd.DataFrame,
    output: Path,
    *,
    rated: pd.DataFrame | None = None,
    show: bool = False,
) -> None:
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

    if rated is not None and not rated.empty:
        ax.plot(
            rated["major"],
            rated["rated_mbps"],
            color=RATED_LINE_COLOR,
            linestyle="--",
            marker="_",
            markersize=14,
            markeredgewidth=2.5,
            linewidth=2.2,
            label="Rated seq. read (best-peak disk)",
            zorder=2.5,
        )
        # Label the drive at each step change in the ceiling.
        y_max = max(best["max_rw_mbps"].max(), rated["rated_mbps"].max())
        prev_disk = None
        for _, row in rated.iterrows():
            disk = str(row["disk"])
            if disk == prev_disk:
                continue
            prev_disk = disk
            ax.annotate(
                disk,
                xy=(row["major"], row["rated_mbps"]),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                color=RATED_LINE_COLOR,
            )

        # Fixed PCIe-generation labels (axis-label size, not disk-name size).
        axis_fs = float(plt.rcParams["axes.labelsize"])
        rated_y = {int(r.major): float(r.rated_mbps) for r in rated.itertuples()}
        if 15 in rated_y:
            ax.annotate(
                "PCIe 4.0",
                xy=(15, rated_y[15]),
                xytext=(0, 14),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=axis_fs,
                color=RATED_LINE_COLOR,
            )
        if 18 in rated_y:
            ax.annotate(
                "PCIe 5.0",
                xy=(18, rated_y[18]),
                xytext=(0, -14),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=axis_fs,
                color=RATED_LINE_COLOR,
            )
        ax.set_ylim(top=y_max * 1.12)

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
    extra = f", {len(rated)} rated points" if rated is not None and not rated.empty else ""
    print(f"Wrote {output} ({len(cpus)} CPUs, {len(best)} points{extra})")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    use_pg18_style()
    args = parse_args()
    raw = fetch_sql_table(args.sql, args.conn)
    hist = stamp_cpu(raw)
    best = best_by_cpu_major(hist)
    if best.empty:
        raise SystemExit("No points after CPU stamps and filters")
    summary = (
        best.groupby("cpu_hist")["major"]
        .agg(["min", "max", "count"])
        .rename(columns={"min": "first_major", "max": "last_major", "count": "majors"})
    )
    print(summary.to_string())
    print()
    cols = [
        "cpu_hist",
        "major",
        "max_rw_mbps",
        "max_write_mbps",
        "max_read_mbps",
        "disk",
        "server",
        "batch_id",
        "batch",
    ]
    cols = [c for c in cols if c in best.columns]
    print(best[cols].to_string(index=False))

    rated = None
    if args.rated_ceiling:
        rated = rated_ceiling_by_major(best)
        print()
        print("Rated ceiling by major (disk of best observed peak):")
        print(rated.to_string(index=False))

    plot_history(best, args.output, rated=rated, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
