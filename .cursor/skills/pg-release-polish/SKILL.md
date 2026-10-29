---
name: pg-release-polish
description: >-
  Post data-collection polish for pgbent getbent.io: slim charts and study
  datasets to the most representative points, fix label placement, and keep
  landing/leaderboard pages thin while larger work lives in its own sections.
  Clears old WIP as releases wrap. Use after pg-release-publish assembly when
  cleaning charts, sanitizing PG18/PG19 docs, trimming leaderboards or the
  homepage, or ordering narrative as tuning > hardware > regression > power.
---

# Release polish (charts + docs)

Use this **after** study data is assembled (`pg-release-publish`) and graphs
exist. Assembly produces pages and PNGs; polish makes them publishable.

Flow should stay **tuning > hardware > regression > power**.

## Chart polish (two phases)

### 1. Cruft out, representative in

One polish phase tries to remove cruft from the chart and slim data sets to
the most representative.

| Do | Don't |
|----|-------|
| Keep the fair / headline cell per CPU or config | Plot every repeat, every face, every also-ran |
| Drop CPUs or servers that dilute the story (e.g. one-off desktop in a farm chart) | Leave debug series, unused `DROP_CPUS` leftovers, or dual subplots that say the same thing |
| Prefer one combined face when faces track together | Duplicate panels that only differ by a label |
| Use clear vendor colors when comparing AMD vs Intel (`#ED1C24` / `#0071C5`) | Rainbow defaults that fight the narrative |
| Filter joules / power boards to comparable RAM class when needed (~128 GB) | Mix memory classes without calling it out |

Encode filters in the study SQL or `reports/*.py` (`DROP_CPUS`, fair-cell
predicates, RAM filters)—not by hand-editing PNG. Regenerate with:

```bash
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.matplotlib-cache" .venv-graph/bin/python reports/<script>.py [--pg <N>]
```

Companion charts (e.g. checkpoint **write GB/h** next to throughput) are fine
when they sell a different axis of the same study; do not stack redundant
faces of the same metric.

### 2. Labels

Then adjust labels to avoid lines and each other, while staying near some
point.

Follow [`scatter-label-layout`](../scatter-label-layout/SKILL.md) for
mechanics (`place_point_labels`, bar inside/outside, one-axis nudges). Polish
checklist specific to wrap:

- [ ] Every remaining marker has one readable label inside the plot grid
- [ ] Labels clear trend lines, bars, and neighbors—not just other text
- [ ] Overrides are sparse; auto-placement first, then per-CPU tweaks
- [ ] Axis text does not repeat the title
- [ ] Read the PNG after regenerate; fix conflicts before prose

## Documentation polish

In the documentation, larger work details should be placed in their own
sections. The main landing page and the leaderboard stay slim. Details about
old WIP should clear out as releases wrap.

### Slim surfaces

| Page | Role | Keep |
|------|------|------|
| `docs/index.md` | Tools + Tuning lead + hardware teaser | One chart + short gloss; link out for depth |
| `docs/leaderboards.md` | Rankings + history | Headline numbers, history chart, link to power/detail children |
| `docs/results-summary/pg<N>/index.md` | Study list for that major | Links + one-line findings only |
| `docs/model/*.md` | Tuning depth | Embed the chart; short why; link study page for provenance |

### Detail homes

Put long method, tables, regenerate commands, and multi-chart write-ups under:

- `docs/results-summary/pg<N>/<study>.md`
- `docs/leaderboards/*-performance-power.md`
- `docs/model/<knob>.md` when the knob study is the product

Do not paste full study prose onto the homepage or parent leaderboard.

### Clear WIP on wrap

When a release snapshot (or study) wraps:

- [ ] Strip Streamlit / temporary explorer asides from finished pages
- [ ] Remove “still collecting”, placeholder peaks, and superseded mid-cycle notes
- [ ] Point Tuning Model / index teasers at the current snapshot (e.g. PG19rc1)
- [ ] Leave older majors as **frozen examples**, not open scratchpads
- [ ] Site narrative order: **tuning → hardware → regression → power**
  (homepage sections, leaderboard child `nav_order`, study index links)

`pg-release-runs` and publish skills may still hold lab WIP; public Markdown
should not.

## Suggested wrap checklist

```
- [ ] Study SQL / graph scripts slimmed to representative cells
- [ ] PNGs regenerated; labels clear of lines and each other
- [ ] Study page carries detail; index/leaderboard only teaser + links
- [ ] Old WIP / Streamlit / placeholders removed from wrapped pages
- [ ] Homepage and nav still read tuning > hardware > regression > power
- [ ] Preview with docs/serve; commit when Greg asks
```

## Related skills

| Skill | When |
|-------|------|
| `pg-release-publish` | Assemble SQL, first graphs, close-out file layout |
| `scatter-label-layout` | Label placement mechanics |
| `pg-release-runs` | Lab collection still open — not polish |
