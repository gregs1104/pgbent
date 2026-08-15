"""Shared Matplotlib typography for PG18 snapshot graphs (2× default sizes)."""

from __future__ import annotations

import matplotlib.pyplot as plt

# Explicit overrides for annotations beyond rcParams defaults.
POINT_LABEL_FONTSIZE = 22
BAR_LABEL_FONTSIZE = 16
ANNOTATION_FONTSIZE = 18
SMALL_ANNOTATION_FONTSIZE = 14
Y_LABEL_FONTSIZE = 18
LEGEND_MARKER_SIZE = 16


def use_pg18_style() -> None:
    """Apply doubled font sizes for titles, axes, ticks, legends, and base text."""
    plt.rcParams.update(
        {
            "font.size": 20,
            "axes.titlesize": 24,
            "axes.labelsize": 20,
            "xtick.labelsize": 20,
            "ytick.labelsize": 20,
            "legend.fontsize": 20,
        }
    )
