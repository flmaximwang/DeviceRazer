# Instrument parsers

Every documented parser class is importable **both** flat and by full module
path — the two resolve to the same object:

```python
from dvrazer.instruments import ChemStChrom                       # flat (short) form
from dvrazer.instruments.Agilent.chemstation_processor import ChemStChrom  # full path
```

The table below lists the defining module; the entry-point column names the
class, which is also re-exported from `dvrazer.instruments` (see
`dvrazer.instruments.__all__`). After loading, call
`set_default_annotations()` before plotting.

| Instrument / software | Import (module) | Entry point | Returns |
|---|---|---|---|
| Agilent ChemStation HPLC | `dvrazer.instruments.Agilent.chemstation_processor` | `ChemStChrom.from_exported_directory(dir, name=None)` | `ChemStChrom` (`Signal1DCollection`), signals named by wavelength (`"280"`, `"214"`…) + `"Fraction"` |
| Agilent Cary WinUV (Cary 100/300) "Scan" CSV | `dvrazer.instruments.Agilent.cary_winuv` | `CaryAbsSpecCollection.from_csv(path, name=None, optical_path_length_mm=10)` | `CaryAbsSpecCollection` of `CaryAbsSpec` |
| CH Instruments CHI660E — CV | `dvrazer.instruments.CH_Instruments.chi660e` | `chi660eCV.from_exported_files(paths, name="CV")` | `VoltammegramCollection` |
| CH Instruments CHI660E — EIS | same module | `chi660eEIS.from_exported_files(paths, name=...)` | `ImpedanceSpectrumCollection` |
| ÄKTA / Unicorn 5 | `dvrazer.instruments.GE_Heathcare.unicorn5` (or `...Cytiva.unicorn5`, re-export) | `Unicorn5Chrom.from_xls(path)`, `Unicorn5Chrom.from_asc(path, names=None)` | `Chrom` |
| ÄKTA / Unicorn 7 | `dvrazer.instruments.GE_Heathcare.unicorn7` (or `...Cytiva.unicorn7`, re-export) | `Unicorn7Project.read_txt(path, name=None)`; `Unicorn7Chrom.from_txt(path, name=None)` is an alias | **`list[Chrom]`**, one per `Chrom.N` in the file, named `<stem>_<N>` |
| Molecular Devices SoftMax Pro | `dvrazer.instruments.MolecularDevices` | `SoftMaxPro_Project.read_txt(path)` | `SoftMaxPro_Project` (plates + groups) |
| SoftMax Pro cuvette (clipboard/text) | `dvrazer.instruments.MolecularDevices.softmax_pro` | `SoftMaxPro_CuvetteData.from_clipboard(txt=path \| text=str, section="Raw-Ref", mode="OD")` | `ContinuousSignal1D` |
| Thermo NanoDrop 2000 | `dvrazer.instruments.ThermoFisher.nanodrop2000` | `Nanodrop2000Workbook.from_tsv(path, name=None)` | `AbsorbSpecCollection` subclass |
| Thermo Multiskan FC | `dvrazer.instruments.ThermoFisher.multiscan_fc` | `MultiWellPlateFC.from_exported_file(path, name=...)` | `MultiWellPlate` |

Naming notes: the CH Instruments package is `CH_Instruments` (it was renamed
from `CHI`; `dvrazer.instruments.CHI` does not exist). `Unicorn7Chrom` exists
and its `from_txt` classmethod simply delegates to
`Unicorn7Project.read_txt` (a `@staticmethod`, so both are called on the class);
both return `list[Chrom]`.
Legacy modules `chemstation_archive.py`, `unicorn_archive.py`,
`nanodrop_utils.py` are the old API — don't use them for new code.

## File formats at a glance

| Export | Encoding | Separator | Layout notes |
|---|---|---|---|
| ChemStation signal `*.CSV` | UTF-16 LE | tab | no header; one file per wavelength in an export directory |
| ChemStation `Fraction.csv` | UTF-8 | tab | header row |
| Cary WinUV Scan CSV | UTF-8 | comma | row 1 spectrum names (2 cols each), row 2 `Wavelength (nm),Abs`, data descending, then one metadata block per spectrum |
| Unicorn 5 `.xls` | Excel | — | sheet `Curves`; `pandas.read_excel` reads it with the `xlrd` engine |
| Unicorn 5 `.asc` | ISO-8859-15 | tab | names in line 2 |
| Unicorn 7 `.txt` | UTF-16 LE | tab | row 0 `Chrom.N`, row 1 signal name, row 2 units, data in (volume, value) column pairs |
| SoftMax Pro `.txt` | UTF-16 LE | tab | `##BLOCKS= N`, blocks end with `~End`; `Plate:` and `Group:` blocks |
| NanoDrop `.tsv` | UTF-8 | tab | spectra separated by blank lines |
| Multiskan FC `.txt` | UTF-8 | tab | data start at the `\t1\t2…\t12` header row |
| CHI660E `.txt` | UTF-8 | comma | header row contains `Potential/V` (CV) or `Freq/Hz` (EIS) |

## Recipes

### Chromatography (ChemStation, Unicorn)

```python
from dvrazer.instruments import Unicorn7Project

chroms = Unicorn7Project.read_txt("run.txt")
chrom = chroms[0]
chrom.signal_names        # e.g. ['UV', 'Cond', 'Conc B', 'Fraction', ...]
chrom.visible_signal_names = ["UV", "Cond", "Fraction"]   # need >=1 continuous for mode 1
chrom.set_default_annotations()
chrom.align_axes(0, 25)                     # mL window
chrom["UV"].value_annotation.limit = (-5, 300)
fig, axes = chrom.plot()                    # Chrom defaults: mode 1, ax_size (16, 5) cm
```

- Unicorn 7: `Unicorn7Chrom.from_txt(path)` is an alias for
  `Unicorn7Project.read_txt`; both return `list[Chrom]` (one per `Chrom.N`).
- Unicorn axis is `Volume (mL)`; signals include `UV`, `UV 1_280`, `Cond`,
  `Conc B`, `pH`, pressures, `System flow`; `Injection`, `Fraction`,
  `Run Log` are `ChromLog` (discrete).
- ChemStation collections are plain `Signal1DCollection` (default mode 0);
  set `chrom.plot_args.mode = 1` for stacked twin axes.
- Peak height / position: `chrom["UV"].get_peak_between(v0, v1)`.
- Compare runs: pull the same signal out of several `Chrom`s into a
  `ContinuousSignal1DCollection.from_similar_signals([...], signal_names=[...])`.

### UV-Vis spectra (Cary, NanoDrop)

```python
from dvrazer.instruments import CaryAbsSpecCollection, Nanodrop2000Workbook
col = CaryAbsSpecCollection.from_csv("scan.csv", optical_path_length_mm=1)
col["sample_1"].metadata["UV-Vis SBW (nm)"]; col["sample_1"].collection_time
diff = col["reduced"] - col["oxidised"]       # same annotations → difference spectrum
```

- Cary: axis is re-sorted ascending on load; duplicate names get `(1)`,
  `(2)` suffixes; truncated scans drop blank cells with a `UserWarning`.
  `optical_path_length_mm` only changes the value label
  (`"1-mm Absorbance"`), not the numbers.
- NanoDrop: **`from_tsv` only reads the file — it never modifies the input**.
  Trailing blank-line trimming/padding happens in memory, so parsing the
  user's only original file is safe (no temp copy needed).
- NanoDrop: `wb.remove_timestamp()` strips the timestamp suffix from names;
  `wb.set_default_annotations(mode="UV-Vis" | "Protein A280")` sets
  220–720 nm or 220–320 nm windows; `wb.average_similar_signals()` merges
  replicates (names grouped by text before the first space by default).

### Plate readers (SoftMax Pro, Multiskan FC)

```python
from dvrazer.instruments.MolecularDevices import SoftMaxPro_Project, SoftMaxPro_Protocol

project = SoftMaxPro_Project.read_txt("export.txt")
project.plate_name                 # ['Plate1', ...]
plate = project["Plate1"]          # also finds groups by name
project.group("Standards").data    # reduction table of a Group: block
```

Plate block type depends on the read mode:

- **Endpoint** → `SoftMaxPro_Plate_Endpoint` (`MultiWellPlate`): `plate["A", 1]`.
- **Kinetic** → `SoftMaxPro_Plate_Kinetic` (`ContinuousSignal1DCollection`):
  signals `"A1_280"` (well_wavelength) plus `"Temperature"`; time axis in s.
  ```python
  plate.remove_signal("Temperature")
  plate = plate.average_similar_signals(lambda n: n.split("_")[1])  # mean per wavelength
  for s in plate.signals: s.axis /= 60
  plate.axis_annotation.unit = "min"; plate.set_default_annotations()
  ```
- **Spectrum** → `SoftMaxPro_Plate_Spectrum` (`ContinuousSignal1DCollection`), one spectrum per well.

Standard curve + unknowns (BCA, Bradford…):

```python
protocol = SoftMaxPro_Protocol([
    {"name": "standards", "type": "standards", "fit": "linear",
     "series": [{"value": 0, "unit": "mg/ml", "wells": ["A1", "A2"]},
                {"value": 0.5, "unit": "mg/ml", "wells": ["B1", "B2"]}]},
    {"name": "S1", "type": "unknown", "wells": ["A4", "B4"]},
    {"name": "Elution", "type": "unknown_dilution",
     "series": [{"dilution_factor": 1, "wells": ["C4", "C5"]},
                {"dilution_factor": 4, "wells": ["D4", "D5"]}]},
]).apply(plate)                          # apply() returns self
protocol.results      # per well: Value, InRange, Concentration (not dilution-corrected), ...
protocol.summary      # per group / dilution level: Mean, SD, CV%, Dilution, AdjResult
protocol.fit_result   # scipy linregress
protocol.dilution_fit # {group: linregress of conc vs 1/dilution}; slope = stock conc
protocol["S1"]        # rows for one group
fig = protocol.plot_standard_curve(groups="all")
```

Exactly one `standards` group is required; only `"linear"` fit exists.

Generic plate calibration without SoftMax (any `MultiWellPlate`, e.g.
Multiskan FC):

```python
fig, ax, fit, table = plate.calibration_and_measurement(
    calibration_values=[0, 0.25, 0.5, 1.0],
    calibration_markers=[("A", 1), ("A", 2), ("A", 3), ("A", 4)],
    measurement_markers=[("B", 1), ("B", 2)],
    xlabel="BSA (mg/mL)", ylabel="A562")
```

### Electrochemistry (CHI660E)

```python
from dvrazer.instruments import chi660eCV, chi660eEIS

cv = chi660eCV.from_exported_files({"run1.txt": "pH 7", "run2.txt": "pH 5"})  # dict → custom names
cv.set_default_annotations(); fig, ax = cv.plot()

eis = chi660eEIS.from_exported_files(["cell.txt"])
fig, ax = eis.plot_nyquist(); fig, axes = eis.plot_bode()
```

A list of paths names signals by file basename (duplicates de-duplicated).
CV signals are `Voltammegram` (`SegmentedContinuousSignal1D`): scan segments
are split automatically; select with `sig.set_active_segments([...])`.
