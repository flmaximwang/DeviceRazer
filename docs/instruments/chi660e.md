# CH Instruments CHI660E

- **Data format**: TXT
- **Module**: `dvrazer.instruments.CH_Instruments.chi660e`
- **Flat imports**: `chi660eCV`, `chi660eEIS`

```python
from dvrazer.instruments import chi660eCV, chi660eEIS

cv = chi660eCV.from_exported_files(["file1.txt", "file2.txt"])
eis = chi660eEIS.from_exported_files({"file.txt": "Sample Name"})
```

`chi660eCV` parses cyclic-voltammetry exports into `Voltammegram` data, and
`chi660eEIS` parses impedance-spectroscopy exports into an `ImpedanceSpectrum`.

See the runnable examples in `examples/chi660e/CV/` (synthetic ferricyanide CV
data) and `examples/chi660e/EIS/` (synthetic Randles-circuit EIS data).
