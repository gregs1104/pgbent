#!/usr/bin/env python3
"""
Graph OSM relation power efficiency from the PG18 osm-power snapshot.

Generates:
  - Horizontal bar chart of relations per average watt
  - Scatter plot of relation count vs average watts

Usage:
  python3 reports/osm-relation-power.py
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_table import load_snapshot_table
from label_layout import LabelOffset, place_label_at_grid_bottom, place_point_labels
from pg18_style import BAR_LABEL_FONTSIZE, POINT_LABEL_FONTSIZE, use_pg18_style

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/results-summary/pg18/osm-power.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs/images/pg18-osm-relation-power.png"
DEFAULT_SCATTER = REPO_ROOT / "docs/images/pg18-osm-relation-scatter.png"
RELATION_HEADING = "## Relation power efficiency"

DEFAULT_POINT_COLOR = "#333333"
SCATTER_MARKER_SIZE = 80
BAR_LABEL_INSIDE_COLOR = "#ffffff"
BAR_LABEL_OUTSIDE_COLOR = "#333333"


def _marker_x_gap(gap: float = 12) -> float:
    return math.sqrt(SCATTER_MARKER_SIZE / math.pi) + gap


RELATION_SCATTER_LABEL_OVERRIDES: dict[str, LabelOffset] = {
    "Apple M4 Max": LabelOffset(_marker_x_gap(), 0, ha="left", va="center"),
    "Apple M4 Max Studio": LabelOffset(_marker_x_gap(), 0, ha="left", va="center"),
    "AMD R5 9600X": LabelOffset(-_marker_x_gap(), 0, ha="right", va="center"),
    "AMD R9 9950X": LabelOffset(-_marker_x_gap(), 0, ha="right", va="center"),
    "Intel i5-13600K": LabelOffset(_marker_x_gap(), 0, ha="left", va="center"),
}


def row_color(row: pd.Series) -> str:
    return str(row.get("cpu_c", "")).strip() or DEFAULT_POINT_COLOR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PG18 OSM relation power efficiency")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scatter-output", type=Path, default=DEFAULT_SCATTER)
    parser.add_argument("--show", action="store_true", help="Display interactively")
    return parser.parse_args()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_relation_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("rel", "avg_watts", "rel_per_watt"):
        if col in df.columns:
            df[col] = numeric(df[col])
    return df.dropna(subset=["cpu", "rel", "avg_watts", "rel_per_watt"]).reset_index(drop=True)


def plain_axis(ax, y: bool = True, x: bool = True) -> None:
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


def _bar_value_label(row: pd.Series) -> str:
    return f"{int(row['rel']):,} rel · {int(row['avg_watts'])} W avg"


def plot_relation_efficiency(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    plot_df = df.sort_values("rel_per_watt", ascending=True).reset_index(drop=True)
    y = range(len(plot_df))

    colors = [row_color(row) for _, row in plot_df.iterrows()]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(list(y), plot_df["rel_per_watt"], color=colors)
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["cpu"])
    for tick, color in zip(ax.get_yticklabels(), colors):
        tick.set_color(color)
    ax.set_xlabel("Relations per average watt (rel / W)")
    ax.set_title("PostgreSQL 16-17 OSM load: relation phase efficiency")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    xmax = plot_df["rel_per_watt"].max()
    pad = max(xmax * 0.02, 3)
    inner_pad = max(xmax * 0.015, 2)
    max_x = xmax

    for i, (_, row) in enumerate(plot_df.iterrows()):
        bar_width = row["rel_per_watt"]
        label = _bar_value_label(row)
        text_width = _text_width_data(ax, label, BAR_LABEL_FONTSIZE, renderer)
        bar_color = colors[i]

        if text_width + inner_pad * 2 <= bar_width:
            ax.text(
                bar_width - inner_pad,
                i,
                label,
                va="center",
                ha="right",
                fontsize=BAR_LABEL_FONTSIZE,
                color=_contrast_text_color(bar_color),
                clip_on=True,
            )
            max_x = max(max_x, bar_width)
        else:
            x = bar_width + pad
            ax.text(
                x,
                i,
                label,
                va="center",
                ha="left",
                fontsize=BAR_LABEL_FONTSIZE,
                color=BAR_LABEL_OUTSIDE_COLOR,
                clip_on=True,
            )
            max_x = max(max_x, x + text_width)

    ax.set_xlim(0, max_x + pad)
    plain_axis(ax, y=False)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def plot_relation_scatter(df: pd.DataFrame, output: Path, show: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))

    for _, row in df.iterrows():
        color = row_color(row)
        ax.scatter(
            row["avg_watts"],
            row["rel"],
            s=SCATTER_MARKER_SIZE,
            color=color,
            zorder=3,
        )

    ax.set_xlabel("Average package power (W)")
    ax.set_ylabel("Relations")
    ax.set_title("PostgreSQL 16-18 OSM load: relation throughput vs average power")
    ax.grid(True, linestyle="--", alpha=0.4)
    plain_axis(ax)

    fig.tight_layout()
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + (ymax - ymin) * 0.06)
    label_df = df[df["cpu"] != "NVIDIA P4242"]
    place_point_labels(
        ax,
        label_df["cpu"],
        label_df["avg_watts"],
        label_df["rel"],
        [row_color(row) for _, row in label_df.iterrows()],
        POINT_LABEL_FONTSIZE,
        overrides=RELATION_SCATTER_LABEL_OVERRIDES,
    )
    nvidia = df[df["cpu"] == "NVIDIA P4242"]
    if not nvidia.empty:
        row = nvidia.iloc[0]
        place_label_at_grid_bottom(
            ax,
            row["avg_watts"],
            row["rel"],
            row["cpu"],
            row_color(row),
            POINT_LABEL_FONTSIZE,
            x_gap_points=_marker_x_gap(),
            align_fraction=0.14,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    print(f"Wrote {output}")
    if show:
        plt.show()
    plt.close(fig)


def main() -> int:
    use_pg18_style()
    args = parse_args()
    rows = load_snapshot_table(args.snapshot, heading=RELATION_HEADING)
    if not rows:
        raise SystemExit(f"No relation table found under {RELATION_HEADING!r} in {args.snapshot}")
    df = prepare_relation_df(rows)
    if df.empty:
        raise SystemExit("Relation table has no plottable rows")
    plot_relation_efficiency(df, args.output, show=args.show)
    plot_relation_scatter(df, args.scatter_output, show=args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
