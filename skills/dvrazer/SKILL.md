---
name: dvrazer
description: >-
  Use DVRazer (Python package `dvrazer`) to load, analyse and plot scientific
  instrument data: UV-Vis/absorbance spectra, HPLC and ÄKTA chromatograms,
  cyclic voltammetry, impedance (EIS), microplate endpoint/kinetic/spectrum
  reads and standard curves. Use whenever a script or notebook imports
  `dvrazer`, or the user wants to parse exports from Agilent ChemStation, Cary
  WinUV, CHI660E, Unicorn 5/7, SoftMax Pro, NanoDrop 2000 or Multiskan FC, or
  to interpolate, subtract, average, find peaks in or plot such signals.
---

# DVRazer

DVRazer turns vendor export files into one data model — a `pandas.DataFrame`
plus a physical-meaning annotation (name, unit, limit, ticks) for every
column — and plots everything from those annotations.

Layers (dependencies point down only):

```
instruments/  vendor parsers        -> return concrete objects
concrete/     Spectrum, Chrom, ...  -> thin semantic subclasses
abstract/     Signal, Signal1D, collections, DescAnno, plot args
```

Read the reference that matches the task:

| Task | Read |
|---|---|
| Loading a vendor file (which class, which method, what comes back) | [references/instruments.md](references/instruments.md) |
| Figures: plot modes, axis limits, ticks, figure size, extra artists | [references/plotting.md](references/plotting.md) |
| Interpolation, arithmetic, averaging, peaks, smoothing, export | this file |

## Imports

Both import styles work and resolve to the same objects — use whichever is
clearer:

```python
# flat / short form (what README, docstrings and these skills use)
from dvrazer import MultiWellPlate, ContinuousSignal1D, Signal1DCollection
from dvrazer.instruments import (
    ChemStChrom, CaryAbsSpecCollection, chi660eCV, chi660eEIS,
    Unicorn5Chrom, Unicorn7Project, Unicorn7Chrom,
    SoftMaxPro_Project, SoftMaxPro_Protocol,
    Nanodrop2000Workbook, MultiWellPlateFC,
)

# full module path (equivalent)
from dvrazer.concrete.spectroscopy import AbsorbSpec, AbsorbSpecCollection
from dvrazer.instruments.Agilent.chemstation_processor import ChemStChrom
from dvrazer.instruments.Cytiva.unicorn7 import Unicorn7Chrom
```

- `from dvrazer import ...` exposes the abstract layer (`Signal`, `Signal1D`,
  `ContinuousSignal1D`, `DiscreteSignal1D`, `FractionSignal`,
  `SignalCollection`, `Signal1DCollection`, `ContinuousSignal1DCollection`,
  `DescAnno`, `ContDescAnno`, `DiscDescAnno`, `Matrix`, `MatrixSeries`,
  `SignalPlotArgs`, `Signal1DPlotArgs`) **and** the concrete layer
  (`MultiWellPlate`, `Chrom`, `AbsorbSpec`, `Voltammegram`,
  `ImpedanceSpectrum`, `KineticCurve`, ...).
- `dvrazer.instruments` re-exports every documented parser class; the mapping
  class → module is in [references/instruments.md](references/instruments.md).
- The CH Instruments package is `dvrazer.instruments.CH_Instruments` (renamed
  from `CHI`). `Unicorn7Chrom.from_txt` exists and is an alias of
  `Unicorn7Project.read_txt` (both return `list[Chrom]`).
- Legacy modules `chemstation_archive`, `unicorn_archive`, `nanodrop_utils`
  are the old API; don't import them in new code.

## Data model in one screen

- `Signal1D.data` columns: **0 = axis** (continuous), **1 = value**,
  optional **2 = value_std**. Column headers are kept as
  `annotation.label`, i.e. `"Wavelength (nm)"`.
- `sig.description_annotations[0]` / `[1]` ⇔ `sig.axis_annotation` /
  `sig.value_annotation`. For continuous columns these are `ContDescAnno`
  with `name`, `unit`, `label`, `limit`, `margin`, `ticklabel_space`.
- `ContinuousSignal1D` — continuous value; supports everything below.
  `DiscreteSignal1D` / `FractionSignal` / `ChromLog` — text labels at axis
  positions (fractions, injections, run logs).
- Collections (`Signal1DCollection`, `ContinuousSignal1DCollection` and
  their subclasses such as `Chrom`, `AbsorbSpecCollection`,
  `SoftMaxPro_Plate_Kinetic`) are dict-like by signal name, carry their own
  collection-level axis/value annotations, a `visible_signal_names` list
  (what gets plotted) and `plot_args`.
- `MultiWellPlate` is a `Matrix` (rows A.., columns 1..), indexed
  `plate["A", 1]`; shape auto-detected for 6/12/24/48/96/384 wells.

## Building signals yourself

```python
import pandas as pd
from dvrazer import ContinuousSignal1D, ContinuousSignal1DCollection

sig = ContinuousSignal1D.from_data(
    df,                       # 2 or 3 columns: axis, value[, std]
    axis_name="Wavelength", axis_unit="nm",
    value_name="Absorbance", value_unit="AU",
    name="sample 1",
)
sig = ContinuousSignal1D.from_csv("x.csv")   # parses "Name (unit)" headers; name = file stem

col = ContinuousSignal1DCollection.from_similar_signals(
    [sig_a, sig_b], name="Batch", signal_names=["A", "B"])   # deep-copies the signals
col = ContinuousSignal1DCollection.from_folder("csv_dir/")   # every *.csv, sorted
```

Collection editing: `col["A"]`, `"A" in col`, `col.signal_names`,
`col.extend_signals([...])`, `col.rename_signal(old, new)`,
`col.remove_signal(name)`, `col.visible_signal_names = [...]`,
`Signal1DCollection.merge([c1, c2])` (prefixes names with the collection name).
`col.append(sig)` adds the signal but **not** to `visible_signal_names`, so it
is not plotted — prefer `extend_signals([sig])`, which does both.

## Analysis on `ContinuousSignal1D`

```python
sig[540]                 # linear interpolation at axis = 540 (scalar)
sig[[530, 550]]          # ndarray
sig.value[540]           # same as sig[540]; sig.value is also array-like
sig.data.iloc[:, 1]      # the raw value column (use this for pandas ops)

diff = sample - blank            # or sample.blank_with(blank)
scaled = sig * 2.0;  ratio = a / b

peak_x, peak_y = sig.get_peak_between(400, 450)   # maximum in a window
sig.slice_axis(400, 450)          # axis points in window (+ the limits themselves)
sig.slice_value_by_axis(400, 450) # interpolated values at those points

avg = ContinuousSignal1D.average([s1, s2, s3])     # adds a std column
avg.std[540]                                        # interpolated std
col.average_similar_signals(lambda n: n.split("_")[0])  # group by key, average each group
```

Rules that bite:

1. **The axis must be ascending.** Interpolation uses `np.interp`; a
   descending axis silently returns garbage (no error). Parsers that read
   descending exports (Cary) sort for you; if you build a signal from
   `df`, sort it first: `df.sort_values(df.columns[0])`.
2. Signal ⊕ signal (`+ - * /`) requires identical axis **and** value
   `name` + `unit` on both, else `ValueError`. `+`/`-` evaluate on the
   union of both axes and return a plain `ContinuousSignal1D` (subclass
   and std are dropped). Scalar operations keep the subclass and scale the std.
3. `sig.std` raises `ValueError` unless the signal came from
   `average()` / `average_similar_signals()` (or you supplied a 3rd column).
4. `filter_by_moving_average(window)` and `clean_by_moving_average(z)`
   **mutate the signal in place** and return `None`. Copy first
   (`copy.deepcopy(sig)`) if you need the original. `filter_by_moving_average`
   currently only works with **even** windows — odd windows raise
   `ValueError` (length mismatch).
5. `integrate_between()` is broken (references undefined `baseline`). Integrate
   manually:
   ```python
   import numpy as np
   m = (sig.axis >= a) & (sig.axis <= b)
   area = np.trapezoid(sig.data.iloc[:, 1][m] - baseline, sig.axis[m])
   ```
6. `sig.to_csv(path)` never overwrites: if the file exists it writes
   `<stem>_<YYYYmmdd_HHMMSS>.csv` and warns. Same for
   `collection.to_folder(dir)`.
7. Changing `sig.data` does not update `axis_annotation.limit`; call
   `col.set_default_annotations()` again (or set limits) before plotting.

## Typical end-to-end script

```python
import matplotlib
matplotlib.use("Agg")            # headless scripts / tests
from dvrazer.instruments import Nanodrop2000Workbook

wb = Nanodrop2000Workbook.from_tsv("spectra.tsv")  # reads only, never modifies the file
wb = wb.average_similar_signals()                 # replicate scans -> mean ± std
wb.set_default_annotations(mode="UV-Vis")         # instrument-specific defaults
wb.align_values(wb.signal_names, 0, 1)
wb.value_annotation.ticklabel_space = (0.2, 0.04) # (major, minor)
fig, ax = wb.plot()
wb[wb.signal_names[0]].plot_peak_at(ax, 400, 420)
fig.savefig("spectra.png", dpi=300, bbox_inches="tight")
```

Always call `set_default_annotations()` after loading and before `plot()`;
plotting asserts that limits and tick spacing are set.

## Finding installed docs, examples and skills

The documentation, runnable examples and these skill files ship inside the
installed package, so read the copy that matches the installed version instead
of guessing a repository path:

```python
import dvrazer

docs = dvrazer.bundle_path("docs")          # .../dvrazer/_bundle/docs when installed
examples = dvrazer.bundle_path("examples")  # .../dvrazer/_bundle/examples
skills = dvrazer.bundle_path("skills")      # .../dvrazer/_bundle/skills

(docs / "index.md").read_text()             # documentation map: start here
sorted(p.name for p in examples.iterdir())  # one directory per instrument
(skills / "dvrazer" / "SKILL.md")           # this file, for the installed version
```

`bundle_path(kind)` accepts `"docs"`, `"examples"` and `"skills"`. It looks in
the installed package first and falls back to the repository checkout for
editable / development installs; if neither exists it raises
`FileNotFoundError`, and an unknown kind raises `ValueError`. Copy an example
next to your own script (examples write their output next to themselves) rather
than writing into the installed package.

## Where to look in the source

- `dvrazer/abstract/signal.py` — `DescAnno`, `ContDescAnno`, `Signal`
- `dvrazer/abstract/signal_1d.py` — signal classes, interpolation, arithmetic
- `dvrazer/abstract/signal_1d_collection.py` — collections and all plotting
- `dvrazer/abstract/display.py` — `SignalPlotArgs`, `Signal1DPlotArgs`
- `dvrazer.bundle_path("examples") / "<instrument>"` and
  `... / "<instrument>/<mode>"` — runnable scripts per instrument/read mode
  (e.g. `nanodrop2000/protein-a280/`, `unicorn7/read_txt/`, `chi660e/CV/`).
  In a source checkout the same tree is `examples/` at the project root.
