---
name: dvrazer-add-instrument
description: >-
  Contributor workflow for the DVRazer repository: add a parser for a new
  instrument or export format under `dvrazer/instruments/`, extend or fix an
  existing parser (ChemStation, Cary WinUV, CHI660E, Unicorn, SoftMax Pro,
  NanoDrop, Multiskan), or add a new concrete signal type. Covers where code
  goes, the parser conventions, synthetic-fixture tests, the example script,
  README/skill updates and the repo's commit rules. Use when changing code
  inside the DVRazer repo, not when merely using the library (see the
  `dvrazer` skill for that).
---

# Adding or changing an instrument parser in DVRazer

Read `README.md` and `AGENTS.md` first. Use the mamba environment
`/Applications/DVRazer` for everything:

```bash
/Applications/DVRazer/bin/python -m pytest tests/ -q
```

Run the suite **before** you start and save the failure list: the suite has
pre-existing failures, and "done" means you added none (and fixed the ones
you touched). Install `pytest` into that env if it is missing.

## 1. Inspect the export before writing code

Get a real sample (the user's file, or `tests/data/` / `examples/`). Record:

- encoding (`file -I`, or look for a BOM / `\x00` bytes → UTF-16 LE is common
  for Windows instrument software), separator, header lines;
- how multiple signals/samples are laid out (column pairs? blocks separated by
  blank lines or `~End`? one file per channel?);
- axis direction (many spectrometers scan high→low), units, blank/"----"
  cells, metadata blocks, duplicate sample names.

Never commit the user's raw file (see §6). Build tests from a synthetic
writer that reproduces this structure.

## 2. Where the code goes

```
dvrazer/instruments/<Vendor>/<software_or_model>.py
```

Existing vendors: `Agilent/`, `CH_Instruments/`, `GE_Heathcare/` (typo kept
on purpose; `Cytiva/` re-exports it), `MolecularDevices/`, `ThermoFisher/`.

Every vendor package has an `__init__.py` that re-exports its public classes,
and `dvrazer/instruments/__init__.py` re-exports all of them, so the documented
short form `from dvrazer.instruments import <Class>` works. When adding a
parser, register it in **both** `__init__.py` files (including `__all__`), add
it to `tests/test_imports.py`, and use the short import in the module
docstring. Users may use either the flat or the full module path.

New *domain* types (not vendor specific) go in `dvrazer/concrete/`. Don't
touch `*_archive.py` / `nanodrop_utils.py` (legacy API).

**Template to copy:** `dvrazer/instruments/Agilent/cary_winuv.py` with
`tests/test_cary_winuv.py` — the newest, cleanest parser and test pair.

## 3. Parser conventions

1. **Module docstring** in the house style (Chinese prose, RST title):
   ```
   """
   ``instruments.<Vendor>.<module>`` --- <Vendor> <Instrument> <数据类型>数据解析
   ==========================================================================

   解析 ... 导出的 ``.xxx`` 文件 ...
   - :class:`...` : ...

   导出文件结构::
       <annotated sample of the file>

   使用示例::

       from dvrazer.instruments import <Class>
   """
   ```
   Use the documented short import (`from dvrazer.instruments import <Class>`);
   it must be exported by `dvrazer/instruments/__init__.py`.
2. **Subclass the closest concrete type** so users get plotting/analysis for
   free: `AbsorbSpec`/`AbsorbSpecCollection` (UV-Vis), `ChromSig`/`ChromLog`/
   `Chrom` (chromatography), `KineticCurve*`, `Voltammegram*`,
   `ImpedanceSpectrum*`, `MultiWellPlate` (plates), or
   `ContinuousSignal1D`/`ContinuousSignal1DCollection` if nothing fits.
   Classes are `@dataclass`; extra per-sample info goes in a
   `metadata: dict = field(default_factory=dict)` field with convenience
   properties.
3. **Factory classmethod**, named after the source: `from_csv`, `from_tsv`,
   `from_txt`/`read_txt`, `from_xls`, `from_raw_export`,
   `from_exported_directory`, `from_exported_file(s)`. Accept
   `str | Path`, a `name=None` override (default: file stem), and open files
   with an explicit `encoding=`.
4. **Build signals with `from_data`**, always passing
   `axis_name/axis_unit/value_name/value_unit`, so headers become
   `"Name (unit)"` labels and limits are filled in. Collections via
   `from_similar_signals(signals, name=..., signal_names=...)`, then
   `set_default_annotations()` is the user's call.
5. **Sort the axis ascending** before building a `ContinuousSignal1D`
   (interpolation silently breaks otherwise), coerce to `float`, drop blank
   cells and emit a `UserWarning` saying what was dropped — never leave NaN
   in the value column.
6. **Unique names**: de-duplicate sample names (`(1)`, `(2)` suffixes like
   Cary, or `dvrazer.utils.name_utils.rename_duplicated_names`). Collections
   key by name, so duplicates break lookup.
7. **Validate inputs** with clear `ValueError`s (bad extension, non-positive
   parameters, unknown signal type) rather than failing deep in pandas.
8. **Plot defaults**: give the collection a `PlotArgs` subclass
   (`@dataclass(slots=True)` of `Signal1DPlotArgs`, e.g. `ax_size=(8, 6)`,
   `mode=0`) via `plot_args: Signal1DPlotArgs = field(default_factory=...)`;
   override `set_default_annotations()` only for instrument-specific windows
   (see `Nanodrop2000Workbook.set_default_annotations(mode=...)`).
9. Match surrounding style: type hints, numpy-style docstrings, Chinese
   comments where the module already uses them.

## 4. Tests

File: `tests/test_<module>.py`. Header used across the suite:

```python
import sys
sys.path.append("..")
import matplotlib
matplotlib.use("Agg")
import pytest
from dvrazer.instruments.<Vendor>.<module> import <Class>
```

- Write a `write_export(path, spectra, ...)` helper that emits a synthetic file
  with the real structure, plus a `tmp_path` fixture — no binary or large
  fixture files. (`tests/data/` and `tests/out/` are git-ignored, so tests
  depending on them won't run for anyone else.)
- Cover: number/names of signals, column labels and annotations, values at a
  few points, axis ascending, metadata, duplicates, truncated/blank data
  (assert the warning with `pytest.warns`), invalid parameters
  (`pytest.raises`), custom `name`, and that `set_default_annotations()` +
  `plot()` run.
- Bug fix ⇒ add a regression test that fails before the fix.

## 5. Example

Add `examples/<instrument>/example.py` (or `examples/<instrument>/<read-mode>/example.py`
when one instrument has several read modes, e.g. `examples/softmax_pro/plate-spectrum/`,
`examples/chi660e/CV/`) that generates synthetic data (or reads a tiny file the user
supplies at runtime), parses it, calls `set_default_annotations()`, plots and saves
`example.png` next to itself. Resolve input/output paths relative to the script
(`os.path.dirname(__file__)`) so it runs from the repo root too. Mirror
`examples/multiscan_fc/example.py`. Don't commit the generated data or PNG.

## 6. Docs and commit rules

- **README.md**: add a row to the "支持的仪器" table (vendor, instrument,
  format, module), a usage subsection with a runnable snippet using the short
  import path, and parsing details worth knowing (encoding, axis sorting,
  warnings).
- **`__init__.py` exports**: add the class to
  `dvrazer/instruments/<Vendor>/__init__.py` and
  `dvrazer/instruments/__init__.py` (plus their `__all__`), and list the
  documented import in `tests/test_imports.py`.
- **skills/dvrazer/references/instruments.md**: add the parser to the table,
  the file-format table and, if non-trivial, a recipe. Keep the skill in sync
  whenever an import path, entry point or return type changes.
- Commit only code/docs. Never commit instrument exports (`.txt .csv .tsv
  .xls .asc`), generated images (unless a ≤100 KB doc figure), or large test
  data.
- Finish with the full test suite run in `/Applications/DVRazer` and report
  any failures that remain, distinguishing pre-existing ones.
