#!/usr/bin/env python3
"""Parse Markdown table snapshots under docs/results-summary/."""

from __future__ import annotations

import re
from pathlib import Path


def _table_from_pipe_lines(lines: list[str]) -> list[dict[str, str]]:
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


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    """Return row dicts from the first GitHub-flavored markdown table in text."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            lines.append(stripped)
        elif lines:
            break
    return _table_from_pipe_lines(lines)


def parse_markdown_tables(text: str) -> list[list[dict[str, str]]]:
    """Return row dicts for every GitHub-flavored markdown table in text."""
    tables: list[list[dict[str, str]]] = []
    block: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            block.append(stripped)
            continue
        if block:
            table = _table_from_pipe_lines(block)
            if table:
                tables.append(table)
            block = []
    if block:
        table = _table_from_pipe_lines(block)
        if table:
            tables.append(table)
    return tables


def load_snapshot_table(path: str | Path, *, heading: str | None = None) -> list[dict[str, str]]:
    text = Path(path).read_text(encoding="utf-8")
    if heading is None:
        return parse_markdown_table(text)
    idx = text.find(heading)
    if idx < 0:
        return []
    return parse_markdown_table(text[idx:])


def conn_mbps(conn: str) -> float | None:
    """Map conn column to Mbps; host/local paths return None."""
    if conn.lower() == "host":
        return None
    try:
        return float(conn)
    except ValueError:
        return None
