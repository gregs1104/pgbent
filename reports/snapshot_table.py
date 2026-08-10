#!/usr/bin/env python3
"""Parse Markdown table snapshots under docs/results-summary/."""

from __future__ import annotations

import re
from pathlib import Path


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    """Return row dicts from the first GitHub-flavored markdown table in text."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            lines.append(stripped)

    if len(lines) < 2:
        return []

    def split_row(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip("|").split("|")]

    header = split_row(lines[0])
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        if re.match(r"^\|\s*-+", line):
            continue
        values = split_row(line)
        if len(values) != len(header):
            continue
        rows.append(dict(zip(header, values)))
    return rows


def load_snapshot_table(path: str | Path) -> list[dict[str, str]]:
    return parse_markdown_table(Path(path).read_text(encoding="utf-8"))


def conn_mbps(conn: str) -> float | None:
    """Map conn column to Mbps; host/local paths return None."""
    if conn.lower() == "host":
        return None
    try:
        return float(conn)
    except ValueError:
        return None
