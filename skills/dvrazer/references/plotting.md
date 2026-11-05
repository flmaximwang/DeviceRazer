# Plotting with DVRazer

## The one idea: everything is drawn in [0, 1]

Every Axes is fixed to `xlim = ylim = (0, 1)`. Real data are mapped onto it
by each column's `ContDescAnno`:

```
plotted = margin[0] + (x - limit[0]) / (limit[1] - limit[0]) * (margin[1] - margin[0])
```

- `limit = (lo, hi)` — the real-world range shown (this is how you "zoom").
- `margin = (0.0, 1.0)` by default — where that range lands inside the Axes.
  `margin = (0.1, 0.9)` leaves 10 % headroom on each side.
- Tick labels are generated from `limit` + `ticklabel_space_major`
  (+ optional `ticklabel_space_minor`, `ticklabel_floor`); tick digits are
  chosen from the spacing automatically.

Consequence: **never call `ax.set_xlim` / `ax.set_ylim` / `ax.set_xticks`
with real units**. Change the annotation instead. To draw your own artist at
real coordinates, convert first:

```python
from dvrazer import Signal
ann = col.axis_annotation
x01 = Signal.rescale(280.0, ann.limit, ann.margin)
ax.axvline(x01, ls="--", color="grey")
```

## Collection plot workflow

```python
col.set_default_annotations()          # limits + tick spacing from the data (required)
col.align_axes(250, 600)               # x range for all signals
col.align_values(col.signal_names, 0, 1.2)   # y range for chosen signals (+ collection)
col.axis_annotation.ticklabel_space = (50, 10)     # (major, minor)
col.value_annotation.ticklabel_space_major = 0.2
col.visible_signal_names = ["A", "C"]  # only these are drawn, in this order
fig, ax = col.plot()
fig.savefig("out.png", dpi=300, bbox_inches="tight")
```

`plot(**kwargs)` forwards Line2D kwargs (`linewidth`, `alpha`, `linestyle`,
`marker`) to every signal, and accepts `mode=` (see below).

To draw onto an Axes you already have (e.g. a subplot grid), use
`col.plot_with_collection_annotations_at(ax)`; for a single signal,
`sig.plot_at(ax, color="C0", label="...")` (it rescales but does not set ticks).

## Modes — `plot(mode=N)` or `col.plot_args.mode`

```python
col.plot_args.mode = 1                 # default mode for the collection
fig, axes = col.plot()

fig, axes = col.plot(mode=2)           # per-call override, plot_args.mode unchanged
```

`plot(mode=N)` is **honoured**: the kwarg overrides `plot_args.mode` for that
call only (it does not mutate the collection). Valid modes are 0, 1, 2; any
other value raises `ValueError`.

| mode | layout | returns | annotations used |
|---|---|---|---|
| 0 (default for most collections) | all visible signals overlaid on one Axes | `fig, ax` | **collection** `axis_annotation` + `value_annotation` |
| 1 (default for `Chrom`) | shared x, one twin y-axis per continuous signal; discrete signals (fractions) drawn on the primary Axes | `fig, [ax, twin1, ...]` | collection axis; **each signal's** `value_annotation` |
| 2 | one subplot per visible signal | `fig, axes` (2-D list) | **each signal's** axis and value annotations; pass `row=`, `col=` to fix the grid |

Mode 1: at least one visible signal must be continuous — it owns the shared x
axis. Discrete signals (`ChromLog`, fractions) are drawn on the primary Axes,
so `visible_signal_names` does **not** have to start with a continuous signal;
without any continuous visible signal `plot()` raises `TypeError`.
Twin spines are spaced by `plot_args.axis_shift` (default 0.2).

`set_default_annotations()` now sets the tick spacing on every signal as well
as on the collection, so modes 1 and 2 work right after loading. The
`AssertionError: ticklabel_space_major is not set` only shows up if you built
or edited annotations yourself — then set the per-signal spacing:

```python
for s in col.signals:
    s.axis_annotation.ticklabel_space_major = 50
    s.value_annotation.ticklabel_space_major = 0.2
```

## Colours and legend (`plot_args`, mode 0)

- `cmap = None` → matplotlib cycle `C0, C1, ...`
- `cmap = "viridis"` (name or `Colormap`) → evenly sampled within
  `cmap_limit` (default `(0, 1)`; use e.g. `(0.1, 0.9)` to skip extremes)
- `cmap = ["k", "tab:red", ...]` → explicit list; length must equal the
  number of visible signals
- `legend_cols`, `legend_loc` (default `"upper right"`),
  `legend_bbox_to_anchor` (e.g. `(1.02, 1)` with `legend_loc="upper left"` to
  put it outside)

## Fixed physical size (publication figures)

```python
col.plot_args.ax_size = (8, 6)     # data area in cm, not the whole figure
fig, ax = col.plot()                # margins auto-measured on first plot, cached
col.plot_args.margin = None         # force re-measure after changing labels/legend
col.plot_args.margin_right = 2.5    # or override one side (cm)
col.plot_args.margin = (1.9, 2.0, 1.5, 1.0)   # left, right, bottom, top (cm)
```

With `ax_size = None` (default) matplotlib sizes the figure and
`tight_layout()` is applied. `Chrom` defaults to `ax_size = (16, 5)`,
`mode = 1`; NanoDrop workbooks default to `ax_size = (8, 6)`.

## Peaks, error bands, special plots

- `sig.plot_peak_at(ax, left, right, type="vline" | "annotation",
  text_shift=(dx, dy), text_digits=2)` marks the maximum in the window
  (`text_shift` is in normalised units).
- Signals with a std column (from averaging) automatically get a shaded
  ±std band.
- `ImpedanceSpectrumCollection.plot_nyquist(real_limit, imag_limit, scale)`
  and `.plot_bode(freq_limit, mag_limit, phase_limit, direction)` use normal
  matplotlib axes (not the [0, 1] system).
- `MultiWellPlate.calibration_and_measurement(...)` and
  `SoftMaxPro_Protocol.plot_standard_curve(groups=...)` draw standard curves
  directly.

## Headless use

Put `import matplotlib; matplotlib.use("Agg")` before any pyplot import in
scripts and tests, and `plt.close(fig)` in loops that make many figures.
