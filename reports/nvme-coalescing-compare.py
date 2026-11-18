#!/usr/bin/env python3
"""Court NVMe coalescing on/off comparison bars for the platform guide."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pg18_style import BAR_LABEL_FONTSIZE, use_pg18_style

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "images" / "nvme-coalescing-compare.png"

# Evidence table on docs/platform/nvme-coalescing.md (ignore OSM overall).
PANELS = (
    ("select-scatter\ncold c=1", 35, 100),
    ("select-scatter\nhot c=32", 1870, 3880),
    ("OSM Relations", 1104, 1921),
)

ON_COLOR = "#8A8A8A"
OFF_COLOR = "#76B900"  # NVIDIA green — court / Spark


def _fmt(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    return f"{v:g}"


def main() -> int:
    use_pg18_style()
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 7.2))
    x = np.arange(2)
    width = 0.62

    for ax, (title, on_v, off_v) in zip(axes, PANELS):
        vals = [on_v, off_v]
        colors = [ON_COLOR, OFF_COLOR]
        bars = ax.bar(x, vals, width=width, color=colors, edgecolor="none")
        ax.set_xticks(x, ["On\n(shipped)", "Off"])
        ax.set_title(title, fontsize=18, pad=10)
        ax.set_ylim(0, max(vals) * 1.18)
        ax.yaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                _fmt(val),
                ha="center",
                va="bottom",
                fontsize=BAR_LABEL_FONTSIZE,
            )

    # One blank line under the figure title; give the rest to the bars.
    fig.suptitle(
        "Court (DGX Spark): NVMe interrupt coalescing on vs off",
        fontsize=22,
        y=0.98,
    )
    fig.subplots_adjust(left=0.03, right=0.99, bottom=0.10, top=0.78, wspace=0.28)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160)
    print(f"Wrote {OUT}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
