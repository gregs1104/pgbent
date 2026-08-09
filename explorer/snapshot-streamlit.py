#!/usr/bin/env python3
"""
Snapshot tables from the live Streamlit results explorer into static Markdown.

Use when the published results database is no longer available. The script walks
the live app the same way a reader would: select each study radio button, wait
for the query, then save the full result table.

How it works
------------
- Loads the Streamlit Cloud app in headless Chromium (app runs inside an iframe).
- Clicks each of the seven study radio options in order.
- Pulls the complete table via Streamlit's "Download data as CSV" button. The
  on-screen dataframe is virtualized and only shows ~12 rows; the CSV has all.

Output
------
Writes one Markdown file per study under docs/results-summary/pg<N>/:

  osm-power, osm-leaderboard, osm-network, osm-checkpoint, osm-dirty-memory,
  pgbench-build, pgbench-select

Also refreshes docs/results-summary/pg<N>/index.md.

Rerun (first time or later)
---------------------------
Install once:

  pip install -r explorer/requirements-snapshot.txt
  playwright install chromium

Capture PG 18 (or change --pg for a new major version when Streamlit publishes it):

  python3 explorer/snapshot-streamlit.py --pg 18

Optional flags:

  --url URL       Streamlit app (default: https://pgbent.streamlit.app/)
  --output DIR    Override output directory
  --no-headless   Show the browser window while capturing (debugging)

After a successful run, review the generated .md files, commit them, and link
from getbent.io. Re-run whenever a release cycle ends and Streamlit has final
results—before optionally pausing Streamlit Cloud hosting until the next cycle.

Requires network access to the Streamlit host. See docs/plans/results-snapshot.md
for the full workflow and the optional database export path (archive-results.py).
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from datetime import date

# Study labels must match st.radio options in submission-explore.py (in order).
STUDIES: list[tuple[str, str, str]] = [
    ("osm-power", "OSM Power", "OSM load throughput vs package power draw."),
    ("osm-leaderboard", "OSM Leaderboard", "Best OSM planet load per CPU/configuration."),
    ("osm-network", "OSM Network", "OSM load speed: server vs remote client."),
    ("osm-checkpoint", "OSM Checkpoint", "Checkpoint tuning during OSM load."),
    ("osm-dirty-memory", "OSM Dirty Memory", "Linux dirty memory limits during OSM load."),
    ("pgbench-build", "pgbench Build Time", "pgbench initialization (:-i) submissions."),
    ("pgbench-select", "pgbench SELECT", "Standard pgbench SELECT grid submissions."),
]

DEFAULT_URL = "https://pgbent.streamlit.app/"


def parse_args() -> argparse.Namespace:
    epilog = """\
examples:
  pip install -r explorer/requirements-snapshot.txt
  playwright install chromium
  python3 explorer/snapshot-streamlit.py --pg 18

Re-run after each PostgreSQL release cycle when Streamlit has final results.
Output: docs/results-summary/pg<N>/*.md
"""
    parser = argparse.ArgumentParser(
        description="Snapshot live Streamlit study tables to Markdown",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Streamlit app URL")
    parser.add_argument("--pg", default="18", help="PostgreSQL major version label for output path")
    parser.add_argument(
        "--output",
        help="Output directory (default: docs/results-summary/pg<N>)",
    )
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    return parser.parse_args()


def frontmatter(study_id: str, title: str, description: str, pg_major: str, nav_order: int) -> str:
    return f"""---
layout: home
title: {title}
permalink: /results-summary/pg{pg_major}/{study_id}/
parent: PostgreSQL {pg_major}
nav_order: {nav_order}
---

# {title}

{description}

_Snapshot of the [Streamlit results explorer](https://pgbent.streamlit.app/) ({title}) on {date.today().isoformat()}._
_Captured by `explorer/snapshot-streamlit.py` from the live site._

"""


def html_table_to_markdown(html: str) -> str:
    """Best-effort conversion of a single HTML table to GitHub-flavored markdown."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    if not rows:
        return "_No table found._"

    md_rows: list[list[str]] = []
    for row in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.DOTALL | re.IGNORECASE)
        cleaned = []
        for cell in cells:
            text = re.sub(r"<[^>]+>", "", cell)
            text = re.sub(r"\s+", " ", text).strip()
            text = text.replace("|", "\\|")
            cleaned.append(text)
        if cleaned:
            md_rows.append(cleaned)

    if not md_rows:
        return "_No table found._"

    width = max(len(r) for r in md_rows)
    md_rows = [r + [""] * (width - len(r)) for r in md_rows]

    lines = [
        "| " + " | ".join(md_rows[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in md_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def app_frame(page):
    """Streamlit Cloud embeds the app in an iframe."""
    if page.locator('iframe[title="streamlitApp"]').count() > 0:
        return page.frame_locator('iframe[title="streamlitApp"]')
    if page.locator("iframe").count() > 0:
        return page.frame_locator("iframe").first
    return page


def click_study(page, label: str, first: bool = False) -> None:
    frame = app_frame(page)
    if not first:
        radio = frame.get_by_role("radio", name=label)
        try:
            radio.click(force=True, timeout=5000)
        except Exception:
            # Overlays (toolbar, dataframe) often intercept pointer events; JS click works.
            radio.evaluate("el => el.click()")
    page.wait_for_timeout(3000)
    try:
        app_frame(page).locator("text=Query returned").wait_for(timeout=60000)
    except Exception:
        page.wait_for_timeout(3000)


def csv_to_markdown(csv_text: str) -> str:
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return "_No table found._"

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]

    def esc(cell: str) -> str:
        return cell.replace("|", "\\|")

    lines = [
        "| " + " | ".join(esc(c) for c in rows[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(esc(c) for c in row) + " |")
    return "\n".join(lines)


def query_status(page) -> str | None:
    frame = app_frame(page)
    for el in frame.locator("[data-testid='stMarkdownContainer']").all():
        text = el.inner_text().strip()
        if text.startswith("Query returned"):
            return text
    return None


def extract_table_via_download(page) -> str | None:
    """Use Streamlit's CSV download button for the full result set."""
    frame = app_frame(page)
    btn = frame.get_by_role("button", name="Download data as CSV")
    try:
        btn.wait_for(timeout=60000)
    except Exception:
        return None
    if btn.count() == 0:
        return None

    with page.expect_download(timeout=60000) as download_info:
        try:
            btn.click(force=True, timeout=5000)
        except Exception:
            btn.evaluate("el => el.click()")
    download = download_info.value
    csv_path = download.path()
    if not csv_path:
        return None
    with open(csv_path, encoding="utf-8") as f:
        return csv_to_markdown(f.read())


def extract_table_from_dom(page) -> str:
    """Fallback: scrape visible DOM rows (virtualized; often incomplete)."""
    frame = app_frame(page)
    df_frame = frame.locator("[data-testid='stDataFrame']")
    if df_frame.count() > 0:
        html = df_frame.first.locator("table").inner_html()
        return html_table_to_markdown(f"<table>{html}</table>")

    for el in frame.locator("[data-testid='stMarkdownContainer'] table").all():
        html = el.inner_html()
        table = html_table_to_markdown(f"<table>{html}</table>")
        if table != "_No table found._":
            return table

    return "_No table found._"


def extract_table(page) -> tuple[str, str | None]:
    """Return markdown table and optional 'Query returned N rows' status line."""
    status = query_status(page)
    table_md = extract_table_via_download(page)
    if table_md is None:
        table_md = extract_table_from_dom(page)
    return table_md, status


def write_pg_index(output_dir: str, pg_major: str, study_ids: list[str]) -> None:
    lines = [
        "---",
        "layout: home",
        f"title: PostgreSQL {pg_major}",
        f"permalink: /results-summary/pg{pg_major}/",
        "parent: Results summary",
        "nav_order: 1",
        "has_children: true",
        "---",
        "",
        f"# PostgreSQL {pg_major} results",
        "",
        "Snapshots captured from the live [Streamlit results explorer](https://pgbent.streamlit.app/).",
        "",
        "## Studies",
        "",
    ]
    titles = {sid: title for sid, title, _ in STUDIES}
    for sid in study_ids:
        title = titles.get(sid, sid)
        lines.append(
            f"- [{title}]({{{{ '/results-summary/pg{pg_major}/{sid}/' | relative_url }}}})"
        )
    lines.append("")
    path = os.path.join(output_dir, "index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    args = parse_args()
    output_dir = args.output or os.path.join("docs", "results-summary", f"pg{args.pg}")
    os.makedirs(output_dir, exist_ok=True)

    written: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        print(f"Loading {args.url}")
        page.goto(args.url, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(5000)

        for nav_order, (study_id, label, description) in enumerate(STUDIES, start=1):
            print(f"Capturing: {label}")
            click_study(page, label, first=(nav_order == 1))
            table_md, status = extract_table(page)

            body = frontmatter(study_id, label, description, args.pg, nav_order)
            if status:
                body += f"\n_{status}._\n\n"
            body += table_md + "\n"

            out_path = os.path.join(output_dir, f"{study_id}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(body)
            print(f"  Wrote {out_path}")
            written.append(study_id)

        browser.close()

    write_pg_index(output_dir, args.pg, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
