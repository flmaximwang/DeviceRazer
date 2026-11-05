# Architecture

DVRazer turns the raw exports of many instruments into one data model, and then
runs the same analysis and plotting code on top of that model. The core tension it
resolves is: **every instrument has a different file format and physical meaning,
but the analysis logic is shared** — so the library binds "the data" and "the
physical meaning of the data" into one object, and upper layers no longer need to
care which instrument the data came from.

## Layers

The package is split into four layers by responsibility. `abstract/` is the core
framework (the abstract data model), `concrete/` contains semantic subclasses for
domains (spectroscopy, chromatography, kinetics, …), `instruments/` contains the
vendor parsers, and `utils/` holds miscellaneous helpers. **Dependencies point in
one direction only**: `instruments → concrete → abstract`.

```
dvrazer/
├── abstract/          # abstract data-model layer — the core framework
│   ├── signal.py              # Signal base class + DescAnno annotation system
│   ├── signal_1d.py           # 1D signals (Signal1D, ContinuousSignal1D, DiscreteSignal1D)
│   ├── signal_collection.py   # SignalCollection base class
│   ├── signal_1d_collection.py# Signal1DCollection
│   ├── signal_2d.py           # 2D signals (framework placeholder)
│   ├── matrix.py              # Matrix
│   ├── matrix_collection.py   # MatrixSeries
│   └── display.py             # SignalPlotArgs plotting arguments
├── concrete/          # concrete domain signal types
│   ├── __init__.py            # re-exports all concrete types (MultiWellPlate, Chrom, ...)
│   ├── spectroscopy.py        # spectroscopy (Spectrum, AbsorbSpec)
│   ├── chromatography.py      # chromatography (Chrom, ChromSig, ChromLog)
│   ├── kinetics.py            # kinetics (KineticCurve)
│   ├── voltammetry.py         # voltammetry (Voltammegram)
│   ├── impedance_spectroscopy.py # impedance spectroscopy (ImpedanceSpectrum)
│   └── multi_well_plates.py   # multi-well plates (MultiWellPlate, plate layouts)
├── instruments/       # instrument-specific data parsers
│   ├── __init__.py            # flat-import entry point (re-exports parser types)
│   ├── Agilent/
│   ├── CH_Instruments/
│   ├── Cytiva/ & GE_Heathcare/
│   ├── MolecularDevices/
│   └── ThermoFisher/
├── bundle.py          # locates the shipped docs/examples/skills bundle
└── utils/             # utility functions
    ├── name_utils.py          # name deduplication
    ├── path_utils.py          # path handling
    └── transform_utils.py     # data scaling
```

## Class hierarchy

```
Signal (dataclass)          — Base: .data (pd.DataFrame), .name, .description_annotations
  Signal1D                  — 2 columns: axis (cont) + value
    ContinuousSignal1D      — Interpolation, arithmetic, peak detection, smoothing
    DiscreteSignal1D        — Discrete values (fractions)
    SegmentedSignal1D       — Multi-segment data (voltammetry)
      SegmentedContinuousSignal1D
```

## Key conventions

1. **dataclass + property pattern**: all signal classes are `@dataclass`.
   Properties expose axis/value/annotation access.
2. **Normalized plotting**: all plotting uses [0, 1] normalized coordinates. Real
   data becomes plot coordinates through `rescale()` + `ContDescAnno` (limit +
   margin).
3. **Column annotations**: each DataFrame column has a `DescAnno` with name, unit,
   limit, margin and tick settings.
4. **Collection pattern**: `SignalCollection` acts as a dict-like container with
   `__getitem__` by name.
5. **Instrument parsers**: static factory methods named `from_raw_export()`,
   `from_exported_directory()`, `from_xls()`, etc.

## The concrete layer is a thin set of semantic aliases

The classes in `concrete/` are mostly empty shells — `Spectrum` and `AbsorbSpec`
are just subclasses of `ContinuousSignal1D` whose class body is `pass`. This is
not redundancy: it **translates the inheritance hierarchy into domain vocabulary**.
Callers write `AbsorbSpec` instead of `ContinuousSignal1D[ContDescAnno]`, which
makes the code immediately readable, and there is a ready place to attach
type-specific behaviour later.

```python
from dataclasses import dataclass, field
from ..abstract import (
    ContinuousSignal1D,
    ContinuousSignal1DCollection,
    ContDescAnno,
)


@dataclass
class Spectrum(ContinuousSignal1D):

    pass


@dataclass
class SpectrumCollection(ContinuousSignal1DCollection):

    pass


@dataclass
class AbsorbSpec(ContinuousSignal1D):

    pass


@dataclass
class AbsorbSpecCollection(ContinuousSignal1DCollection):

    pass
```

## The instrument layer in one example

A parser's only job is to turn a vendor file into a `DataFrame` and hand it to a
concrete class. The Multiskan FC reader scans the `.txt` export line by line until
it finds the 12-column header, feeds the text after that header to pandas, and
constructs a `MultiWellPlateFC` — about 14 lines in total. This is the architecture
paying off: **switching to another instrument only changes the small piece that
reads the file into a DataFrame**, while the data model, plotting and
interpolation above it stay untouched.

```python
class MultiWellPlateFC(MultiWellPlate):

    @staticmethod
    def from_exported_file(txt_path, name="Default Multi-Scan Fluorescence Collection"):
        with open(txt_path, "r") as f:
            flag = False
            data_txt = ""
            for line in f:
                if not flag and "\t1\t2\t3\t4\t5\t6\t7\t8\t9\t10\t11\t12" in line:
                    flag = True
                if flag:
                    data_txt += line
        my_df = pd.read_csv(io.StringIO(data_txt), sep="\t", index_col=0)

        return MultiWellPlateFC(data=my_df, name=name)
```

See [Adding an instrument](../development/adding-an-instrument.md) for the
step-by-step version.

## See also

- [Description annotations](desc-anno.md) — the foundation of the data model.
- [Signal](signal.md) — the root class.
- [Signal1D](signal-1d.md) — the most-used concrete shape.
- [Signal collections](signal-collection.md) — grouping signals.
