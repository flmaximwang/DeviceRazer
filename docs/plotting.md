# Plotting

`Signal1DCollection` supports three plotting modes:

| Mode | Description | When to use it |
|------|-------------|----------------|
| 0 | Shared axes, all signals overlaid | Quickly compare several signals |
| 1 | Shared x axis, a separate y axis per signal | Signals with different scales / units (e.g. UV + Cond + pH) |
| 2 | Faceted plot, one subplot per signal | Dense signals that are easier to inspect separately |

```python
collection.plot_args.mode = 1  # switch mode
collection.plot_args.ax_size = (25, 10)  # Axes data area: 25 cm wide, 10 cm high
collection.plot_args.legend_cols = 2
# margin defaults to None: the first plot() measures the label widths and stores
# the margins (in cm) automatically.
collection.plot_args.margin = (1.9, 2.0, 1.5, 1.0)  # or set them manually: left, right, bottom, top
collection.plot_args.margin_right = 2.5  # or set a single margin (cm)
collection.plot_args.margin = None  # restore automatic measurement
fig, axes = collection.plot()
```

The mode can also be overridden per call without changing `plot_args.mode`:

```python
fig, axes = collection.plot(mode=2)  # modes 0/1/2; an invalid mode raises ValueError
```

Mode 1 requires at least one visible continuous signal (discrete signals such as
`Fraction` are drawn on the main axis). `set_default_annotations()` sets the tick
spacing for both the collection and each signal, so a freshly loaded collection
can be plotted directly.

See [Signal collections](concepts/signal-collection.md) for creating and
managing collections, and [Description annotations](concepts/desc-anno.md) for
the tick and label settings used by the axes.
