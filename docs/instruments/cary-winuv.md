# Agilent Cary WinUV

- **Data format**: CSV
- **Module**: `dvrazer.instruments.Agilent.cary_winuv`
- **Flat import**: `from dvrazer.instruments import CaryAbsSpecCollection`

A single "Scan" CSV export can contain multiple spectra (stored as column pairs,
two columns per spectrum):

```python
from dvrazer.instruments import CaryAbsSpecCollection

# One "Scan" export .csv can contain multiple spectra (two columns per spectrum).
collection = CaryAbsSpecCollection.from_csv("5705.csv")
collection.signal_names                              # ['5705-ox1_1', '5705-re1_1', ...]

# The cuvette path length (mm, default 10) is only used to label the absorbance
# column; it does not convert the data.
collection = CaryAbsSpecCollection.from_csv("5705.csv", optical_path_length_mm=1)
collection.value_annotation.label                    # '1-mm Absorbance' (default '10-mm Absorbance')
collection.optical_path_length_mm                    # 1

# Each spectrum carries the metadata of its scan (Collection Time / Instrument /
# Start-Stop / SBW / Method Log ...).
collection["5705-ox1_1"].collection_time             # '2026/9/23 14:31:09'
collection["5705-ox1_1"].instrument                  # 'Cary 100'
collection["5705-ox1_1"].metadata["UV-Vis SBW (nm)"] # '1.0'
collection.metadata                                  # {spectrum name: metadata dict}

collection.set_default_annotations()
fig, ax = collection.plot()
```

`from_csv(csv_path, name=None, optical_path_length_mm=10)` parses Cary's Scan
export structure: row 1 holds the spectrum names (two columns per spectrum), row 2
holds the column names (`Wavelength (nm),Abs`), the data section alternates
`(wavelength, absorbance)` pairs (wavelength decreases from Start to Stop in the
exported file), and each spectrum is followed by a metadata block (`Collection
Time` / `Parameter List` / `Method Log` / `[Time]` / `<SBW (nm)>` etc.).

Parsing details:

- **The wavelength axis is stored in ascending order after parsing** (the export
  itself runs from Start down to Stop): within the library, operations that look
  values up by axis (`__getitem__`, `get_peak_between`, `slice_value_by_axis`,
  difference spectra) assume an ascending axis (`np.interp` requires ascending
  `xp`). A descending axis would make them **silently return wrong values** (the
  last data point for any wavelength), so the parser sorts the axis while reading.
- The absorbance column is labelled `<path>-mm Absorbance` (default
  `10-mm Absorbance`; the export writes `Abs` with no unit);
  `optical_path_length_mm` must be > 0.
- Duplicate spectrum names (Cary allows saving over an entry, so duplicates can
  appear in an export) get `(1)`, `(2)` suffixes in order.
- Blank cells left by an interrupted scan (e.g. a spectrum measured only down to
  510 nm) are dropped with a `UserWarning` instead of becoming `NaN`.
- Metadata blocks and spectra correspond one-to-one in file order; if their counts
  differ, the parser falls back to matching by spectrum name and warns.
