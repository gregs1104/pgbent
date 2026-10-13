---
name: scatter-label-layout
description: >-
  Tune Matplotlib labels on pgbent PG18 charts: scatter point placement,
  horizontal bar value labels (inside bar with contrast color when they fit),
  overlap avoidance, and PNG regeneration. Use when fixing crowded scatter or
  bar labels, pg18-osm-power-*.png, pg18-osm-relation-power.png,
  pg18-osm-relation-scatter.png, reports/label_layout.py, or place_point_labels.
---

# Graph label layout (pgbent)

Scatter point labels and horizontal bar value labels share one goal: **keep
readable text inside the plot grid**, associated clearly with its mark, without
crowding neighbors.

## Goal

Each scatter marker gets **one clearly associated label**:

- Text **lines up with its dot** (usually vertically centered on the marker).
- Labels stay **inside the plot grid** (the area inside the axes — not title/legend margins).
- Labels pick **left or right** (or a grid-edge lane) to **avoid conflicts**.
- Axis labels avoid repeating what the **title already states**.

## Hard constraints

1. **Never place labels outside the plot grid.** Legend/title margins are off-limits.
2. Overrides that extend outside `ax.patch` are **rejected silently**; auto-placement wins and may look wrong. If a label “won’t move,” check whether the override failed the inside-plot test.
3. When the user asks to nudge a label, change **one axis at a time** (horizontal *or* vertical). Do not revert a working horizontal placement while fixing vertical alignment.

## Tooling in this repo

| Piece | Location |
|-------|----------|
| Overlap-aware placement | `reports/label_layout.py` — `place_point_labels()`, `place_label_at_grid_bottom()` |
| Override tuple | `LabelOffset(dx, dy, ha=..., va=...)` in **offset points** from the marker |
| Marker gap helper | `_marker_x_gap(gap=12)` — `sqrt(marker_size/π) + gap` |
| Font/style | `reports/pg18_style.py` — call `use_pg18_style()`; use `POINT_LABEL_FONTSIZE`, `BAR_LABEL_FONTSIZE` |
| Reference scatter charts | `reports/osm-power.py`, `reports/osm-relation-power.py` (scatter) |
| Reference bar chart | `reports/osm-relation-power.py` — `plot_relation_efficiency()` |

## Workflow

```
- [ ] Read the PNG and list conflicts (overlap, wrong axis, off-grid).
- [ ] Wire scatter plots through place_point_labels() after fig.tight_layout().
- [ ] Add y-axis headroom (~6%) before label placement if top markers clip centered labels.
- [ ] Add per-CPU overrides only for crowded markers; regenerate PNG.
- [ ] Confirm each override is accepted (no silent fallback); read warnings from the script.
- [ ] Tune one axis per user feedback iteration.
```

Regenerate (use the venv when matplotlib is not on system Python):

```bash
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-power.py
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/osm-relation-power.py
```

## Placement patterns

### Default: right of dot, vertically centered

```python
LabelOffset(_marker_x_gap(), 0, ha="left", va="center")
```

### Left of dot (conflict on the right or near right edge)

```python
LabelOffset(-_marker_x_gap(), 0, ha="right", va="center")
```

### Stacked labels at similar x (e.g. two Apple chips)

- Upper point: `va="bottom"`, small positive `dy` (e.g. 6), tight `dx` via `_marker_x_gap(-4)`.
- Lower point: `va="center"`, standard right gap.

### Lowest crowded marker (NVIDIA pattern)

Exclude from `place_point_labels()`; use `place_label_at_grid_bottom()` so the label runs along the **bottom grid edge**, starting right of the dot (`align_fraction` ≈ 0.14).

### Fine nudges

Adjust `dx` or `dy` in **offset points** only. Positive `dy` moves up; negative `dy` moves down. Keep `ha`/`va` consistent with the chosen side.

## Direction selection

| Situation | Prefer |
|-----------|--------|
| Marker near **right** plot edge | Label on the **left** (`ha="right"`, negative `dx`) |
| Two markers at **same x**, different y | Split directions (one left, one right) or separate vertical lanes |
| Marker near **top** of y-range | Add y headroom; keep `va="center"` |
| Marker in **lower-left cluster** | Right-aligned labels; lowest may need grid-bottom placement |
| Long CPU name + neighbor close in y | Choose the side with empty space; never overlap a neighbor’s dot |

## Axis label cleanup

If the title already says “OSM load … throughput”, shorten the y-axis:

- `Throughput (kNodes/s)` instead of `OSM load throughput (kNodes/s)`
- `Relations` instead of `Relation Phase Rate`

Do not duplicate workload context on both title and axis.

## Failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Override ignored | Label bbox outside plot grid | Reduce offset, add y headroom, or switch side |
| Label below/above dot despite `va="center"` | Auto-placement fallback | Fix inside-plot constraint first, then re-apply override |
| Huge overlap score in warnings | Labels fighting at same x/y band | Split left/right between neighbors |
| User says “nudge” but layout jumps | Changed horizontal when only vertical was requested | Revert horizontal; adjust `dy` only |

## Reference overrides

Working examples live in:

- `SINGLE_CHART_LABEL_OVERRIDES` in `reports/osm-power.py` (`nodes_kips` / `index_kips`)
- `RELATION_SCATTER_LABEL_OVERRIDES` in `reports/osm-relation-power.py`

Copy patterns from those dicts before inventing new layout logic.

## Done checklist

- [ ] Every dot has one readable label; no text-on-text overlap.
- [ ] Labels remain inside the plot grid.
- [ ] Horizontal placement matches user-approved side before vertical fine-tuning.
- [ ] PNG under `docs/images/` regenerated and matches the script output.
- [ ] Residual overlap warnings understood (minor point overlap may remain; text overlap should not).

## Horizontal bar value labels

Used on charts like `pg18-osm-relation-power.png` where each bar needs a
descriptive value string (e.g. `1,666 rel · 5 W avg`).

### Rule: inside when it fits, outside when it does not

1. After drawing bars, measure each label’s **text width in data coordinates**
   (probe with `alpha=0.0`, not `visible=False` — invisible text returns zero width).
2. Compare to **bar width** (`rel_per_watt` or equivalent x value).
3. **Fits** (`text_width + 2 * inner_pad <= bar_width`):
   - Place **inside the bar**, `ha="right"`, x = `bar_width - inner_pad`.
   - Set text color with **`_contrast_text_color(bar_color)`** (white on dark bars).
   - Enable `clip_on=True`.
4. **Does not fit**:
   - Place **outside to the right**, `ha="left"`, x = `bar_width + pad`.
   - Use a neutral outside color (e.g. `#333333`).
5. Set **`xlim` from actual label extents** (`max_x + pad`), not a fixed multiple of
   `xmax`. Outside labels on short bars must not drive text off the right edge.

### Why this works on PG18 relation power

The **longest bars** (highest rel/W — typically Apple Silicon) extend farthest
right and are **always wide enough** to hold the full value string inside. Those
are exactly the bars that previously pushed outside labels past the plot edge.
Shorter bars (AMD/Intel/NVIDIA) keep outside labels because the string is wider
than the bar — that is expected.

Reference implementation: `_text_width_data()`, `_contrast_text_color()`, and
the label loop in `plot_relation_efficiency()` in `reports/osm-relation-power.py`.

### Bar chart checklist

- [ ] Longest bars use inverted/contrast text inside the bar.
- [ ] Short bars keep outside labels; none overlap the y-axis category text.
- [ ] `xlim` fits all outside labels without extra dead space from a blind `xmax * N`.
- [ ] Text width probe uses `alpha=0.0` so fit detection is reliable.
