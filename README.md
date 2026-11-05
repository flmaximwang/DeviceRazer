# DVRazer

DVRazer (import name `dvrazer`) is a Python library for processing, analyzing and
visualizing data from many kinds of scientific instruments. It gives experimental
data a unified data model and processing framework: vendor exports become signals
with their physical meaning attached, and the same analysis and plotting code works
across instruments.

## Features

- **A unified data model** — a layered abstraction `Signal` → `Signal1D` /
  `Signal2D` → instrument-specific signals, so all instrument data is handled the
  same way.
- **A built-in description-annotation system** — every data dimension carries its
  name, unit, range and tick labels, which keeps plotting and presentation simple.
- **Automated plotting** — several plotting modes (overlaid lines, multiple axes,
  faceted panels) with automatic axis scaling and labels.
- **Data operations** — signal arithmetic (add / subtract / multiply / divide),
  interpolation (`sig[axis]`, `sig.value[axis]`, `sig.std[axis]`), peak detection,
  region integration, smoothing and baseline correction.
- **Instrument data parsing** — built-in importers for several instrument vendors.

## Installation

```bash
pip install git+https://github.com/flmaximwang/DVRazer.git
```

Requirements: Python ≥ 3.11, `numpy`, `pandas`, `matplotlib`, `scipy`,
`scikit-learn`, `impedance`, and `python-calamine` (needed for Unicorn 5 `.xls`
files).

## Quickstart

```python
from dvrazer import ContinuousSignal1D, Signal1DCollection

# Read a spectrum; axis name and unit are detected automatically.
sig = ContinuousSignal1D.from_csv("uv_vis_spectrum.csv")

# Interpolate a value at a given axis position.
value_at_540nm = sig[540]

# Find the peak between 500 and 600 nm.
peak_axis, peak_value = sig.get_peak_between(500, 600)

# Load a folder of spectra, align them and plot them in one figure.
collection = Signal1DCollection.from_folder("data/folder/")
collection.set_default_annotations()
fig, ax = collection.plot()
```

Runnable examples for every supported instrument live in `examples/`; see
[Getting started](docs/getting-started.md) for the full table and how to run them.

## Loading data

`Signal` and its subclasses can read CSV files directly:

```python
from dvrazer import Signal

sig = Signal.from_csv("data.csv")
sig.to_csv("export.csv")
```

Use `from_data(...)` to build a signal from an existing `pandas.DataFrame`. The
[Signal1D](docs/concepts/signal-1d.md) page covers interpolation, arithmetic,
peak detection and filtering.

## Docs, examples and skills ship with the package

The English documentation, the runnable examples and the agent skills are bundled
inside the installed `dvrazer` package, so an agent (or a human) can always find
the material that matches the installed version:

```python
import dvrazer

dvrazer.bundle_path("docs")      # pathlib.Path to the bundled docs
dvrazer.bundle_path("examples")  # pathlib.Path to the bundled examples
dvrazer.bundle_path("skills")    # pathlib.Path to the bundled skills
```

`bundle_path(kind)` looks in the installed package first and falls back to the
repository checkout for editable / development installs; if neither exists it
raises `FileNotFoundError`.

## Agent skills

The bundled `skills/` directory contains Agent Skills for coding agents:
`skills/dvrazer` covers using the library (instrument exports, interpolation,
plotting modes and annotations), and `skills/dvrazer-add-instrument` covers adding
or fixing a parser in this repository. When you change import paths, factory
methods, return types or plotting behaviour, update the matching skill files too —
see [skills/README.md](skills/README.md).

## Supported instruments

Agilent ChemStation HPLC and Cary WinUV, CH Instruments CHI660E, Cytiva / GE
Healthcare Unicorn 5 and 7, Molecular Devices SoftMax Pro, and Thermo Fisher
NanoDrop 2000 and Multiskan FC. See
[Supported instruments](docs/instruments/index.md) for data formats, module paths
and the flat-import list.

## Documentation

- [Documentation index](docs/index.md) — the full map of the docs tree.
- [Getting started](docs/getting-started.md) — installation, first example, examples.
- [Architecture](docs/concepts/architecture.md) — package layers, class hierarchy, conventions.
- [Signal1D](docs/concepts/signal-1d.md) — interpolation, arithmetic, peaks, filtering.
- [Plotting](docs/plotting.md) — plotting modes and figure layout.
- [Multi-well plates](docs/plates.md) — plate handling and calibration.
- [Contributing](docs/development/contributing.md) — the uv workflow and commit rules.
- [Adding an instrument](docs/development/adding-an-instrument.md) — writing a parser.

## License

DVRazer is released under the terms in the [LICENSE](LICENSE) file.
