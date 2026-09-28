---
name: dvrazer
description: >-
  Expert in the DVRazer Python library — used for processing,
  analyzing, and visualizing scientific instrument data (spectra, chromatography,
  voltammetry, impedance, microplate, kinetics). Knows the abstract data model,
  concrete types, instrument-specific parsers, and plotting system.
---

# DVRazer Skill

You are an expert on the **DVRazer** Python library. This library provides a unified data model and instrument-specific parsers for scientific laboratory equipment data.

## Project Location

The library source is at the project root in `dvrazer/`.

## Architecture Overview

The library has three layers:

```
abstract/        ← Generic data model (Signal, Signal1D, SignalCollection, Matrix)
  concrete/      ← Domain-specific types (Spectrum, Chrom, Voltammegram, etc.)
    instruments/ ← Instrument file parsers (Agilent, CHI, Cytiva, etc.)
```

## Core Data Model

### Signal Classes (abstract/signal.py, abstract/signal_1d.py)

- **`Signal`** — Base class. Holds `pd.DataFrame` in `.data`, has `name`, `description_annotations` list.
- **`Signal1D(Signal)`** — Two columns: continuous `axis` (column 0) + `value` (column 1). Properties: `.axis`, `.value`, `.axis_annotation`, `.value_annotation`.
- **`ContinuousSignal1D(Signal1D)`** — Both axis and value are continuous. Supports:
  - Interpolation via `signal[axis_value]`
  - Arithmetic: `+`, `-`, `*`, `/`, `-` (negate), `blank_with()`
  - Peak detection: `get_peak_between(left, right)` → `(peak_axis, peak_value)`
  - Averaging: `ContinuousSignal1D.average([sig1, sig2, ...])` with std. dev.
  - Smoothing: `clean_by_moving_average()`, `filter_by_moving_average(window)`
  - Optional 3rd column: `value_std` for error bands on plots
- **`DiscreteSignal1D(Signal1D)`** — Continuous axis, discrete values (e.g., fraction labels).
- **`SegmentedSignal1D` / `SegmentedContinuousSignal1D`** — Multi-segment data with a "Segment" column (used by voltammetry).
- **`FractionSignal(DiscreteSignal1D)`** — Fraction collection data.

### Description Annotations (abstract/signal.py)

Each column in the DataFrame is annotated with a `DescAnno` object:

```python
ContDescAnno(name="Wavelength", unit="nm", limit=(200, 800), margin=(0, 1))
```

- `.label` → `"Wavelength (nm)"`
- `.limit` = (min, max) real-world range
- `.margin` = (left, right) normalized plot position
- `.ticklabel_space` → auto-computes `.ticklabels` and `.ticks`
- `.ticks` → tick positions in [0,1] normalized coordinates

### Collection Classes (abstract/signal_collection.py, abstract/signal_1d_collection.py)

- **`SignalCollection`** — Dict-like container: `collection["name"]`, `.append()`, `.remove_signal()`, `.rename_signal()`, `.to_folder()`, `.merge()`.
- **`Signal1DCollection`** — Holds Signal1D objects. Has `from_folder()`, `align_axes()`, `align_values()`, `set_default_annotations()`.
- **`ContinuousSignal1DCollection`** — Holds only ContinuousSignal1D. Adds `average_similar_signals()`.

### Matrix Classes (abstract/matrix.py, abstract/matrix_collection.py)

- **`Matrix`** — 2D data table wrapping `pd.DataFrame`. Has `.loc`, `.iloc`.
- **`MatrixSeries`** — Multiple matrices indexed along an axis. Can convert to `ContinuousSignal1DCollection`.

### Plot Args (abstract/display.py)

- **`SignalPlotArgs`** — `figsize`, `cmap` (str, Colormap, Callable, or list), `cmap_limit`, `legend_cols`.
- **`Signal1DPlotArgs`** — Adds `mode`:
  - **0**: Shared axes, all signals overlaid (default)
  - **1**: Separate y-axes (twinx), side-by-side
  - **2**: Separate subplots for each signal

## Plotting System

The plotting system uses **normalized coordinates [0, 1]** for all axes:

1. Each signal stores real-world data in `ContDescAnno.limit`
2. `ContDescAnno.margin` defines where in [0,1] the data appears
3. `Signal.rescale()` converts real-world → normalized
4. `.ticks` and `.ticklabels` properties generate display ticks in [0,1] space

Always use `signal.plot_at(ax, **kwargs)` which handles rescaling internally.

## Concrete Domain Types

### Spectroscopy (`concrete/spectroscopy.py`)
- `Spectrum(ContinuousSignal1D)` — generic spectrum
- `AbsorbSpec(ContinuousSignal1D)` — absorbance spectrum

### Chromatography (`concrete/chromatography.py`)
- `ChromSig(ContinuousSignal1D)` — UV, Cond, pH, pressure, flow
- `ChromLog(DiscreteSignal1D)` — Fraction, Injection logs
- `Chrom(Signal1DCollection)` — full chromatogram. Default: mode=1, figsize=(20,6)

### Voltammetry (`concrete/voltammetry.py`)
- `Voltammegram(SegmentedContinuousSignal1D)` — Potential vs Current with Segments
- `VoltammegramCollection(ContinuousSignal1DCollection)`

### Impedance Spectroscopy (`concrete/impedance_spectroscopy.py`)
- `ImpedanceSpectrum(Signal)` — Frequency, Z', Z''. Has `plot_nyquist()` / `plot_bode()`
- `ImpedanceSpectrumCollection(SignalCollection)`

### Kinetics (`concrete/kinetics.py`)
- `KineticCurve(ContinuousSignal1D)`, `KineticCurveCollection`

### Multi-Well Plates (`concrete/multi_well_plates.py`)
- `MultiWellPlate(Matrix)` — auto-detects 6/12/24/48/96/384 wells
  - `plate["A", 1]` access, `plate.calibration_and_measurement()`
- `MultiWellPlateSeries(MatrixSeries)`

## Instrument Parsers

### Agilent ChemStation
```python
from dvrazer.instruments import ChemStChrom
chrom = ChemStChrom.from_exported_directory("export_dir/")
uv = chrom["280"]
```
CSV: UTF-16 LE, tab-separated, no header. Fraction.csv: UTF-8.

### CHI660E Electrochemistry
```python
from dvrazer.instruments import chi660eCV, chi660eEIS
cv = chi660eCV.from_exported_files(["file1.txt", "file2.txt"])
eis = chi660eEIS.from_exported_files({"file.txt": "Sample Name"})
```

### Unicorn 5 (ÄKTA)
```python
from dvrazer.instruments import Unicorn5Chrom
chrom = Unicorn5Chrom.from_xls("run.xls")  # or from_asc("run.asc")
chrom["UV"].plot_at(ax)
```

### Unicorn 7 (ÄKTA)
```python
from dvrazer.instruments import Unicorn7Chrom
chroms = Unicorn7Chrom.from_txt("run.txt")  # Returns list
chroms[0]["UV"].plot_at(ax)
```

### SoftMax Pro
```python
from dvrazer.instruments import SoftMaxPro_Project
project = SoftMaxPro_Project.read_txt("data.txt")
plate = project["Plate 1"]
well_a1 = plate["A1"]
```
Format: UTF-16 LE, `##BLOCKS=N`, `~End` terminated.

### NanoDrop 2000
```python
from dvrazer.instruments import Nanodrop2000Workbook
wb = Nanodrop2000Workbook.from_tsv("spectra.tsv")
wb.set_default_annotations(mode="UV-Vis")
wb.plot()
```

### Multiskan FC
```python
from dvrazer.instruments import MultiWellPlateFC
plate = MultiWellPlateFC.from_exported_file("data.txt")
```

## File Format Reference

| File | Encoding | Separator | Notes |
|------|----------|-----------|-------|
| ChemStation CSV | UTF-16 LE | tab | No header |
| ChemStation Fraction | UTF-8 | tab | Has header |
| Unicorn 5 XLS | (Excel) | — | Sheet "Curves" |
| Unicorn 5 ASC | ISO-8859-15 | tab | Headers in first lines |
| Unicorn 7 TXT | UTF-16 LE | tab | Chrom.# headers |
| SoftMax Pro TXT | UTF-16 LE | tab | ##BLOCKS= format |
| NanoDrop TSV | UTF-8 | tab | Double-newline separated |
| Multiskan FC TXT | UTF-8 | tab | Column header 1-12 |
| CHI660E TXT | UTF-8 | (varies) | Segment on header |

## Known Issues

1. **`integrate_between()` in `signal_1d.py:690`** references undefined variables — will raise `NameError`.
2. **`GE_Heathcare/`** is a known typo (should be `Healthcare`). Both paths work.
3. **`signal_2d.py` / `signal_2d_collection.py`** are empty stubs.
4. **Two code generations coexist**: archive files vs. modern dataclass-based code.

## Tests

```bash
cd <project-root>
python -m pytest tests/
```
