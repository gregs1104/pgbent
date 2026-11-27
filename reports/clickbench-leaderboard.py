#!/usr/bin/env python3
"""
ClickBench leaderboard starter: Performance vs. Power.

Writes court's best load+query pair (totals, phase breakdown, per-query
table) into docs/leaderboards/clickbench-performance-power.md, plus:
  - load-phase disk avg vs 1s max (OSM-style)
  - query-phase vmstat runnable (`r`) avg vs 1s max — owned stand-in for
    load average / parallelism on this farm

Usage:
    MPLBACKEND=Agg python3 reports/clickbench-leaderboard.py --from-db
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metric_series import (
    fetch_disk_avg_max,
    fetch_metric_avg_max,
    legend_avg_max,
    plot_avg_max,
)
from pg18_style import use_pg18_style
from release_paths import REPO_ROOT

DEFAULT_CONN = "host=localhost dbname=results user=gsmith password=secret"
SQL_PATH = REPO_ROOT / "reports" / "clickbench-leaderboard.sql"
POWER_PAGE = REPO_ROOT / "docs" / "leaderboards" / "clickbench-performance-power.md"
LOAD_DISK_IMAGE = REPO_ROOT / "docs" / "images" / "clickbench-leaderboard-load-disk.png"
QUERY_RUNNABLE_IMAGE = (
    REPO_ROOT / "docs" / "images" / "clickbench-leaderboard-query-runnable.png"
)
BLOCK_BEGIN = "<!-- clickbench-leaderboard:begin -->"
BLOCK_END = "<!-- clickbench-leaderboard:end -->"
# vmstat runnable processes — closest owned second-grain signal to loadavg.
QUERY_PARALLEL_METRIC = "r"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write ClickBench Performance vs. Power leaderboard + traces"
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Query the results DB and update docs/leaderboards/clickbench-performance-power.md",
    )
    parser.add_argument("--sql", type=Path, default=SQL_PATH)
    parser.add_argument("--page", type=Path, default=POWER_PAGE)
    parser.add_argument("--load-disk-image", type=Path, default=LOAD_DISK_IMAGE)
    parser.add_argument("--query-runnable-image", type=Path, default=QUERY_RUNNABLE_IMAGE)
    parser.add_argument("--conn", default=os.environ.get("RESULTS_CONN", DEFAULT_CONN))
    parser.add_argument("--show", action="store_true")
    return parser.parse_args()


def sql_body(path: Path) -> str:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
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


def geomean(values: list[float]) -> float | None:
    vals = [v for v in values if v and v > 0]
    if not vals:
        return None
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def parse_queries(raw) -> list[list[float]]:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return []
    if isinstance(raw, str):
        try:
            queries = json.loads(raw)
        except json.JSONDecodeError:
            return []
    else:
        queries = raw
    if not isinstance(queries, list):
        return []
    out: list[list[float]] = []
    for tries in queries:
        if not isinstance(tries, (list, tuple)) or len(tries) < 3:
            continue
        out.append([float(tries[0]), float(tries[1]), float(tries[2])])
    return out


def cold_hot_from_queries(raw) -> tuple[float | None, float | None]:
    queries = parse_queries(raw)
    if not queries:
        return None, None
    colds = [t[0] for t in queries]
    hots = [min(t[1], t[2]) for t in queries]
    return geomean(colds), geomean(hots)


def query_detail_rows(raw) -> list[dict[str, object]]:
    """One row per ClickBench query: cold try1 + try2/try3 + hot=min(try2,try3)."""
    rows: list[dict[str, object]] = []
    for i, tries in enumerate(parse_queries(raw), start=1):
        hot = min(tries[1], tries[2])
        rows.append(
            {
                "q": i,
                "cold": fmt_float(tries[0], 3),
                "try2": fmt_float(tries[1], 3),
                "try3": fmt_float(tries[2], 3),
                "hot": fmt_float(hot, 3),
            }
        )
    return rows


def markdown_table(rows: list[dict[str, object]], cols: list[str]) -> str:
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def fmt_int(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return f"{int(round(float(v))):,}"


def fmt_float(v, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return f"{float(v):.{digits}f}".rstrip("0").rstrip(".")


def fmt_kj(joules) -> str:
    if joules is None or (isinstance(joules, float) and math.isnan(joules)):
        return ""
    return fmt_float(float(joules) / 1000.0, 1)


def short_version(raw) -> str:
    text = str(raw or "")
    m = re.search(r"PostgreSQL\s+(\d+(?:\.\d+)?)", text)
    if m:
        return m.group(1)
    m = re.match(r"^(\d+(?:\.\d+)?)", text.strip())
    return m.group(1) if m else text


def short_disk(raw) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    # Keep the public short label used on OSM rows when present.
    if text.startswith("Samsung MZAL"):
        return "Samsung MZAL"
    return text


def disk_title(cpu: str, disk: str, mode: str) -> str:
    if not disk:
        return f"{cpu} ClickBench load disk"
    if mode == "combined":
        return f"{cpu} ClickBench load disk · {disk}"
    return f"{cpu} ClickBench load disk · {disk} read+write"


def plot_phase_traces(
    df: pd.DataFrame,
    conn: str,
    load_disk_path: Path,
    query_runnable_path: Path,
    show: bool = False,
) -> tuple[str, str]:
    """Plot load disk + query runnable traces. Returns (disk_label, disk_mode)."""
    load = df[df["phase"] == "load"]
    query = df[df["phase"] == "query"]
    if query.empty:
        raise SystemExit("No query-phase row for ClickBench traces")
    cpu = str(df.iloc[0]["cpu"]).strip()
    server = str(df.iloc[0]["server"]).strip()
    disk_label, disk_mode = "", ""

    if not load.empty:
        load_test = int(load.iloc[0]["test"])
        disk_df, disk_label, disk_mode = fetch_disk_avg_max(conn, server, load_test)
        if disk_df.empty:
            raise SystemExit(f"No disk series for {server} load test {load_test}")
        avg_l, max_l = legend_avg_max(disk_df, "MB/s")
        plot_avg_max(
            disk_df,
            load_disk_path,
            title=disk_title(cpu, disk_label, disk_mode),
            ylabel="MB/s",
            avg_legend=avg_l,
            max_legend=max_l,
            show=show,
        )

    query_test = int(query.iloc[0]["test"])
    run_df = fetch_metric_avg_max(
        conn, server, query_test, QUERY_PARALLEL_METRIC, dbagg="minute"
    )
    if run_df.empty:
        raise SystemExit(
            f"No {QUERY_PARALLEL_METRIC!r} series for {server} query test {query_test}"
        )
    avg_l, max_l = legend_avg_max(run_df, "runnable", digits=1)
    plot_avg_max(
        run_df,
        query_runnable_path,
        title=f"{cpu} ClickBench query · vmstat runnable (r)",
        ylabel="Runnable processes",
        avg_legend=avg_l,
        max_legend=max_l,
        show=show,
    )
    return disk_label, disk_mode


def traces_markdown(disk: str, mode: str) -> str:
    if mode == "combined":
        disk_note = (
            f" Disk is Darwin combined throughput (`{disk}_MB/s`)."
            if disk
            else ""
        )
    else:
        disk_note = (
            f" Disk is combined read+write on data volume `{disk}`."
            if disk
            else ""
        )
    return (
        "**Load disk** — minute buckets of the owned 1-second iostat collectors "
        "on the COPY/`VACUUM` cell. Average is what a minute-grained sample would "
        "report; Maximum is the peak 1-second reading in that minute."
        + disk_note
        + "\n\n"
        "![ClickBench load disk average vs 1-second maximum]"
        "({{ '/images/clickbench-leaderboard-load-disk.png' | relative_url }})\n\n"
        "**Query parallelism** — minute buckets of vmstat **`r`** (runnable "
        "processes) on the 43-query cell. That is the owned second-grain stand-in "
        "for system load average on this farm (we do not yet store "
        "`/proc/loadavg`); it is the familiar signal for whether gather workers "
        "are filling the machine.\n\n"
        "![ClickBench query runnable average vs 1-second maximum]"
        "({{ '/images/clickbench-leaderboard-query-runnable.png' | relative_url }})\n"
    )


def block_markdown(
    df: pd.DataFrame,
    *,
    disk_label: str = "",
    disk_mode: str = "",
) -> str:
    # One host for the starter board (SQL already filters to court).
    server = str(df.iloc[0]["server"])
    cpu = str(df.iloc[0]["cpu"])
    mem_gb = fmt_int(df.iloc[0]["mem_gb"])
    disk = short_disk(df.iloc[0]["disk"])
    ver = short_version(df.iloc[0]["ver"])
    set_id = fmt_int(df.iloc[0]["set"])
    set_info = str(df.iloc[0]["set_info"] or "")

    load = df[df["phase"] == "load"]
    query = df[df["phase"] == "query"]
    if query.empty:
        raise SystemExit("No query-phase row in ClickBench leaderboard result")

    q = query.iloc[0]
    cold_gm, hot_gm = cold_hot_from_queries(q.get("queries"))
    if hot_gm is None and not pd.isna(q.get("hot_geomean")):
        hot_gm = float(q["hot_geomean"])
    cold_score = round(1000.0 / cold_gm) if cold_gm else None
    hot_score = int(round(float(q["tps"]))) if not pd.isna(q.get("tps")) else None

    detail_rows = query_detail_rows(q.get("queries"))
    hot_max = None
    if detail_rows:
        hot_max = max(float(r["hot"]) for r in detail_rows if r["hot"] != "")
    elif not pd.isna(q.get("max_latency")):
        hot_max = float(q["max_latency"])

    summary_cols = [
        "cpu",
        "mem_gb",
        "disk",
        "ver",
        "set",
        "score",
        "cold_score",
        "hot_geomean",
        "max_hot",
        "load_mbs",
        "load_s",
        "data_gb",
        "avg_pkg_q",
        "max_pkg_q",
        "kj_q",
    ]
    summary = {
        "cpu": cpu,
        "mem_gb": mem_gb,
        "disk": disk,
        "ver": ver,
        "set": set_id,
        "score": fmt_int(hot_score),
        "cold_score": fmt_int(cold_score),
        "hot_geomean": fmt_float(hot_gm, 3),
        "max_hot": fmt_float(hot_max, 3),
        "load_mbs": fmt_int(load.iloc[0]["tps"]) if not load.empty else "",
        "load_s": fmt_int(load.iloc[0]["load_time_s"]) if not load.empty else "",
        "data_gb": fmt_float(load.iloc[0]["data_gb"], 2) if not load.empty else "",
        "avg_pkg_q": fmt_float(q.get("avg_pkg"), 1),
        "max_pkg_q": fmt_float(q.get("max_pkg"), 1),
        "kj_q": fmt_kj(q.get("joules")),
    }

    breakdown_cols = [
        "phase",
        "test",
        "tps",
        "meaning",
        "wall_s",
        "avg_pkg",
        "max_pkg",
        "kj",
        "detail",
    ]
    breakdown_rows: list[dict[str, object]] = []
    if not load.empty:
        lr = load.iloc[0]
        breakdown_rows.append(
            {
                "phase": "load",
                "test": fmt_int(lr["test"]),
                "tps": fmt_int(lr["tps"]),
                "meaning": "MB/s",
                "wall_s": fmt_int(lr["wall_s"]),
                "avg_pkg": fmt_float(lr.get("avg_pkg"), 1),
                "max_pkg": fmt_float(lr.get("max_pkg"), 1),
                "kj": fmt_kj(lr.get("joules")),
                "detail": (
                    f"load_time {fmt_int(lr['load_time_s'])}s, "
                    f"data {fmt_float(lr['data_gb'], 2)} GB"
                ),
            }
        )
    breakdown_rows.append(
        {
            "phase": "query",
            "test": fmt_int(q["test"]),
            "tps": fmt_int(q["tps"]),
            "meaning": "1000/geomean(hot)",
            "wall_s": fmt_int(q["wall_s"]),
            "avg_pkg": fmt_float(q.get("avg_pkg"), 1),
            "max_pkg": fmt_float(q.get("max_pkg"), 1),
            "kj": fmt_kj(q.get("joules")),
            "detail": (
                f"hot_geomean {fmt_float(hot_gm, 3)}s"
                + (f", cold_geomean {fmt_float(cold_gm, 3)}s" if cold_gm else "")
                + (f", queries {fmt_int(q.get('query_count'))}" if q.get("query_count") else "")
            ),
        }
    )

    summary_md = markdown_table([summary], summary_cols)
    breakdown_md = markdown_table(breakdown_rows, breakdown_cols)
    detail_md = (
        markdown_table(detail_rows, ["q", "cold", "try2", "try3", "hot"])
        if detail_rows
        else "_No per-query timings in artifacts._"
    )
    traces_md = traces_markdown(disk_label, disk_mode)

    return (
        f"{BLOCK_BEGIN}\n\n"
        f"Starter board from **{server}** ({cpu}"
        + (f", {mem_gb} GB" if mem_gb else "")
        + (f", {disk}" if disk else "")
        + f"), PostgreSQL **{ver}**, set **{set_id}**"
        + (f" — {set_info}" if set_info else "")
        + ". Best finished **query** cell by score "
        f"(**{fmt_int(hot_score)}** = `1000 / geomean(hot)`), paired with the "
        f"**load** sibling in the same set. Package watts are the owned "
        f"1-second collectors (`PkgWatt` / Darwin / Spark `soc_pkg_power2_input`).\n\n"
        f"**Totals**\n\n{summary_md}\n\n"
        f"**Phase breakdown**\n\n{breakdown_md}\n\n"
        f"{traces_md}\n"
        f"**Query runs** (seconds; **cold** = try1, **hot** = min(try2, try3))\n\n"
        f"{detail_md}\n\n"
        f"{BLOCK_END}"
    )


def replace_marked_block(text: str, begin: str, end: str, inner: str) -> str:
    if begin in text and end in text:
        return re.sub(
            re.escape(begin) + r".*?" + re.escape(end),
            inner,
            text,
            count=1,
            flags=re.S,
        )
    raise SystemExit(f"Missing {begin} / {end} markers in {POWER_PAGE.name}")


def main() -> None:
    args = parse_args()
    if not args.from_db:
        raise SystemExit("This starter board is generated with --from-db")

    use_pg18_style()
    df = fetch_sql_table(args.sql, args.conn)
    disk_label, disk_mode = plot_phase_traces(
        df,
        args.conn,
        args.load_disk_image,
        args.query_runnable_image,
        show=args.show,
    )
    inner = block_markdown(df, disk_label=disk_label, disk_mode=disk_mode)
    if not args.page.exists():
        raise SystemExit(f"Missing page {args.page}")
    text = args.page.read_text(encoding="utf-8")
    args.page.write_text(
        replace_marked_block(text, BLOCK_BEGIN, BLOCK_END, inner),
        encoding="utf-8",
    )
    print(f"Updated {args.page}")


if __name__ == "__main__":
    main()
