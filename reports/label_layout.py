"""Scatter label placement with overlap avoidance inside the plot grid."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox

OUTSIDE_PLOT_PENALTY = 1e12


@dataclass(frozen=True)
class LabelOffset:
    dx: float
    dy: float
    ha: str = "left"
    va: str = "bottom"


def candidate_offsets(fontsize: float) -> list[LabelOffset]:
    """Modest offsets that stay near the marker inside the plot grid."""
    step = max(fontsize * 0.45, 8)
    return [
        LabelOffset(step, step),
        LabelOffset(step, -step, va="top"),
        LabelOffset(-step, step, ha="right"),
        LabelOffset(-step, -step, ha="right", va="top"),
        LabelOffset(0, step * 1.1, ha="center"),
        LabelOffset(0, -step * 1.1, ha="center", va="top"),
        LabelOffset(step * 1.1, 0, va="center"),
        LabelOffset(-step * 1.1, 0, ha="right", va="center"),
        LabelOffset(step * 1.4, step * 0.5),
        LabelOffset(-step * 1.4, step * 0.5, ha="right"),
        LabelOffset(step * 1.4, -step * 0.5, va="top"),
        LabelOffset(-step * 1.4, -step * 0.5, ha="right", va="top"),
    ]


def _plot_area_bbox(ax: Axes, renderer, inset: float = 6) -> Bbox:
    bbox = ax.patch.get_window_extent(renderer)
    return Bbox.from_extents(
        bbox.x0 + inset,
        bbox.y0 + inset,
        bbox.x1 - inset,
        bbox.y1 - inset,
    )


def _point_bbox(ax: Axes, x: float, y: float, radius: float = 14) -> Bbox:
    px, py = ax.transData.transform((x, y))
    return Bbox.from_extents(px - radius, py - radius, px + radius, py + radius)


def _expanded_bbox(annotation: Annotation, renderer, pad: float = 1.05) -> Bbox:
    return annotation.get_window_extent(renderer).expanded(pad, pad)


def _overlap_area(a: Bbox, b: Bbox) -> float:
    if not a.overlaps(b):
        return 0.0
    x0 = max(a.x0, b.x0)
    y0 = max(a.y0, b.y0)
    x1 = min(a.x1, b.x1)
    y1 = min(a.y1, b.y1)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _inside_plot(label_bbox: Bbox, plot_bbox: Bbox) -> bool:
    return (
        plot_bbox.x0 <= label_bbox.x0
        and plot_bbox.y0 <= label_bbox.y0
        and label_bbox.x1 <= plot_bbox.x1
        and label_bbox.y1 <= plot_bbox.y1
    )


def _outside_plot_penalty(label_bbox: Bbox, plot_bbox: Bbox) -> float:
    if _inside_plot(label_bbox, plot_bbox):
        return 0.0
    return OUTSIDE_PLOT_PENALTY


def _score_offset(
    annotation: Annotation,
    renderer,
    plot_bbox: Bbox,
    placed_bboxes: Sequence[Bbox],
    point_bboxes: Sequence[Bbox],
) -> float:
    label_bbox = _expanded_bbox(annotation, renderer)
    score = _outside_plot_penalty(label_bbox, plot_bbox)
    if score:
        return score
    for bbox in placed_bboxes:
        score += _overlap_area(label_bbox, bbox) * 4.0
    for bbox in point_bboxes:
        score += _overlap_area(label_bbox, bbox) * 2.0
    return score


def place_point_labels(
    ax: Axes,
    labels: Iterable[str],
    xs: Iterable[float],
    ys: Iterable[float],
    colors: Iterable[str],
    fontsize: float,
    *,
    overrides: Mapping[str, LabelOffset] | None = None,
) -> list[Annotation]:
    """Place scatter labels inside the plot grid, minimizing overlap."""
    label_list = list(labels)
    x_list = list(xs)
    y_list = list(ys)
    color_list = list(colors)
    if not (len(label_list) == len(x_list) == len(y_list) == len(color_list)):
        raise ValueError("labels, xs, ys, and colors must have the same length")

    density = []
    for i in range(len(label_list)):
        neighbors = sum(
            1
            for j in range(len(label_list))
            if i != j
            and abs(x_list[i] - x_list[j]) < max(abs(x_list[i]), 1) * 0.08
            and abs(y_list[i] - y_list[j]) < max(abs(y_list[i]), 1) * 0.08
        )
        density.append((neighbors, i))
    order = [i for _, i in sorted(density, reverse=True)]

    scatter_offsets = candidate_offsets(fontsize)
    override_map = overrides or {}
    annotations: list[Annotation | None] = [None] * len(label_list)
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    plot_bbox = _plot_area_bbox(ax, renderer)
    point_bboxes = [_point_bbox(ax, x, y) for x, y in zip(x_list, y_list)]

    placed_bboxes: list[Bbox] = []
    for idx in order:
        text = label_list[idx]
        x = x_list[idx]
        y = y_list[idx]
        color = color_list[idx]
        if text in override_map:
            override = override_map[text]
            trial = ax.annotate(
                text,
                xy=(x, y),
                xytext=(override.dx, override.dy),
                textcoords="offset points",
                fontsize=fontsize,
                color=color,
                ha=override.ha,
                va=override.va,
                clip_on=True,
            )
            fig.canvas.draw()
            override_score = _score_offset(
                trial, renderer, plot_bbox, placed_bboxes, point_bboxes
            )
            trial.remove()
            candidates = (
                [override]
                if override_score < OUTSIDE_PLOT_PENALTY
                else scatter_offsets
            )
        else:
            candidates = scatter_offsets

        best_offset: LabelOffset | None = None
        best_score = float("inf")
        for offset in candidates:
            ann = ax.annotate(
                text,
                xy=(x, y),
                xytext=(offset.dx, offset.dy),
                textcoords="offset points",
                fontsize=fontsize,
                color=color,
                ha=offset.ha,
                va=offset.va,
                clip_on=True,
            )
            fig.canvas.draw()
            score = _score_offset(ann, renderer, plot_bbox, placed_bboxes, point_bboxes)
            if score < best_score:
                best_score = score
                best_offset = offset
            ann.remove()

        if best_offset is None or best_score >= OUTSIDE_PLOT_PENALTY:
            raise RuntimeError(f"Could not place label for {text!r} inside plot grid")
        if best_score > 0:
            print(f"Warning: residual label overlap for {text!r} (score={best_score:.0f})")
        final_ann = ax.annotate(
            text,
            xy=(x, y),
            xytext=(best_offset.dx, best_offset.dy),
            textcoords="offset points",
            fontsize=fontsize,
            color=color,
            ha=best_offset.ha,
            va=best_offset.va,
            clip_on=True,
        )
        annotations[idx] = final_ann
        fig.canvas.draw()
        placed_bboxes.append(_expanded_bbox(final_ann, renderer))

    return [ann for ann in annotations if ann is not None]


def _data_x_right_of_point(ax: Axes, x: float, y: float, gap_points: float) -> float:
    px, py = ax.transData.transform((x, y))
    px += gap_points * ax.figure.dpi / 72.0
    x_data, _ = ax.transData.inverted().transform((px, py))
    return x_data


def place_label_at_grid_bottom(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    color: str,
    fontsize: float,
    *,
    x_gap_points: float,
    align_fraction: float = 0.28,
) -> Text:
    """Place label to the right of a point, low in the grid and near the marker row."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    plot_bbox = _plot_area_bbox(ax, renderer)
    x_data = _data_x_right_of_point(ax, x, y, x_gap_points)
    ymin, ymax = ax.get_ylim()
    y_data = ymin + (y - ymin) * align_fraction

    label = ax.text(
        x_data,
        y_data,
        text,
        transform=ax.transData,
        fontsize=fontsize,
        color=color,
        ha="left",
        va="bottom",
        clip_on=True,
    )
    fig.canvas.draw()
    label_bbox = _expanded_bbox(label, renderer)
    if not _inside_plot(label_bbox, plot_bbox):
        label.set_position((x_data, ymin + (ymax - ymin) * 0.01))
        label.set_verticalalignment("bottom")
        fig.canvas.draw()
    return label
