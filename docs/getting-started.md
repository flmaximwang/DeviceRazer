# Getting started

## Installation

```bash
pip install git+https://github.com/flmaximwang/DVRazer.git
```

Requirements: Python ≥ 3.11, `numpy`, `pandas`, `matplotlib`, `scipy`,
`scikit-learn`, `impedance`, `python-calamine` and `xlrd`. `xlrd` is the Excel
engine that reads the Unicorn 5 `.xls` exports (the parser calls
`pandas.read_excel` on them).

If you work on DVRazer itself, install the development environment with uv
instead — see [Contributing](development/contributing.md).

## A first example

Load a spectrum from a CSV file, inspect it, and plot a collection of signals:

```python
from dvrazer import ContinuousSignal1D, Signal1DCollection

# Read a spectrum (axis name and unit are detected automatically).
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

## Loading data

`Signal` and its subclasses can read CSV files directly:

```python
from dvrazer import Signal

# Load from CSV.
sig = Signal.from_csv("data.csv")

# Or build one from a pandas DataFrame.
import pandas as pd
sig = Signal(
    data=pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}),
    name="My Signal",
)

# Export.
sig.to_csv("export.csv")
```

One-dimensional signals can be built from a DataFrame with explicit axis and value
annotations:

```python
sig = ContinuousSignal1D.from_data(
    data=df,
    axis_name="Wavelength",
    axis_unit="nm",
    value_name="Absorbance",
    value_unit="AU",
)
```

See [Signal1D](concepts/signal-1d.md) for interpolation, arithmetic, peak
detection and filtering, and [Signal collections](concepts/signal-collection.md)
for working with groups of signals.

## Running the examples

Complete runnable examples live in the `examples/` directory, one or more per
instrument. The directory names below are the real paths in the repository:

| Instrument | Directory | Data source |
|------------|-----------|-------------|
| **NanoDrop 2000** (Protein A280) | `examples/nanodrop2000/protein-a280/` | Measured TSV data |
| **NanoDrop 2000** (UV-Vis) | `examples/nanodrop2000/UV-Vis/` | Bring your own TSV named `example.tsv` |
| **ChemStation HPLC** | `examples/chemstation_hplc/` | Measured CSV data (5 wavelengths + fractions) |
| **ÄKTA / Unicorn 5** | `examples/unicorn5/read_asc/` | Synthetic ASC data (UV, Cond, pH, Conc) |
| **ÄKTA / Unicorn 5** (two runs compared) | `examples/unicorn5/compare_difference_sec/` | Bring your own two ASC files |
| **ÄKTA / Unicorn 7** | `examples/unicorn7/read_txt/` | Bring your own TXT named `example.txt` |
| **ÄKTA / Unicorn 7** (SEC plot) | `examples/unicorn7/sec/` | Bring your own TXT (passed on the command line) |
| **SoftMax Pro** (Spectrum) | `examples/softmax_pro/plate-spectrum/` | Measured TXT data (96-well spectrum) |
| **SoftMax Pro** (Kinetics) | `examples/softmax_pro/plate-kinetics/` | Measured TXT data (96-well kinetics, 6 wavelengths, protein–hemin binding) |
| **SoftMax Pro** (Cuvette) | `examples/softmax_pro/cuvette/` | Bring your own cuvette TXT (`clipboard2csv.py`) |
| **CHI660E** (CV) | `examples/chi660e/CV/` | Synthetic ferricyanide CV data |
| **CHI660E** (EIS) | `examples/chi660e/EIS/` | Synthetic Randles-circuit EIS data |
| **Multiskan FC** | `examples/multiscan_fc/` | Synthetic 96-well data (BSA standard curve) |

> `examples/unicorn7/unicorn7_txt/` is a historical copy of the `read_txt/`
> example that still uses the older `dvrazer.instruments.GE_Heathcare.unicorn7`
> import path; use `read_txt/` for new code.

Run an example (most scripts resolve their input files relative to the script
itself, so they work both from the repository root and from the example
directory):

```bash
python examples/chemstation_hplc/example.py
# or
cd examples/chemstation_hplc
python example.py
```

Most scripts write `example.png` next to the script. The exceptions are:

| Script | Output |
|--------|--------|
| `examples/softmax_pro/plate-kinetics/example.py` | `example_soret.png` and `example_visible.png` |
| `examples/nanodrop2000/protein-a280/example.py`, `examples/nanodrop2000/UV-Vis/example.py` | no image file — the figure is only shown on screen |
| `examples/unicorn5/compare_difference_sec/sec.py` | `data/SEC_Comparison_<timestamp>.png`; it reads `data/SECNoSalt.asc` and `data/SECSalt.asc` relative to the current directory, so run it from the example directory |
| `examples/unicorn7/sec/sec.py` | the input `.txt` path with the suffix changed to `.png` (override with `-o`); the input file is passed with `-i` |
| `examples/softmax_pro/cuvette/clipboard2csv.py` | a CSV file, not an image: `<input>_<section>_<mode>.csv` by default, or the path given with `-o` |

## Where to go next

- [Plotting](plotting.md) — the plotting modes and figure layout.
- [Multi-well plates](plates.md) — plate handling and calibration.
- [Architecture](concepts/architecture.md) — how the package is organized.
- [Supported instruments](instruments/index.md) — parsers and import paths.
