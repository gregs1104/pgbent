"""Per-release snapshot and image paths for PostgreSQL results graphs."""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PG = "18"


def add_pg_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pg",
        default=DEFAULT_PG,
        metavar="MAJOR",
        help=f"PostgreSQL release cycle for default paths and titles (default: {DEFAULT_PG})",
    )


def snapshot_path(pg: str, study_id: str) -> Path:
    return REPO_ROOT / f"docs/results-summary/pg{pg}/{study_id}.md"


def image_path(pg: str, name: str) -> Path:
    return REPO_ROOT / f"docs/images/pg{pg}-{name}.png"
