# Thermo Fisher NanoDrop 2000

- **Data format**: TSV
- **Module**: `dvrazer.instruments.ThermoFisher.nanodrop2000`
- **Flat import**: `from dvrazer.instruments import Nanodrop2000Workbook`

```python
from dvrazer.instruments import Nanodrop2000Workbook

workbook = Nanodrop2000Workbook.from_tsv("spectra.tsv")
workbook.set_default_annotations(mode="UV-Vis")
fig, ax = workbook.plot()
```

`from_tsv` only reads the file (trailing blank lines are trimmed and padded in
memory), so it never modifies the input file — you can safely parse the user's
only original export.

See the runnable examples in `examples/nanodrop2000/protein-a280/` (measured TSV
data) and `examples/nanodrop2000/UV-Vis/` (bring your own TSV named
`example.tsv`).
