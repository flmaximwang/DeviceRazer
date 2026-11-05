# Agilent ChemStation (HPLC)

- **Data format**: CSV (UTF-16 LE, tab-separated)
- **Module**: `dvrazer.instruments.Agilent.chemstation_processor` (current parser)
- **Legacy archive**: `dvrazer.instruments.Agilent.chemstation_archive`
- **Flat import**: `from dvrazer.instruments import ChemStChrom`

## Reading an export directory

```python
from dvrazer.instruments import ChemStChrom

chrom = ChemStChrom.from_exported_directory("path/to/chemstation_export/")
uv_signal = chrom["280"]
uv_signal.plot_at(ax)
```

The parser reads a ChemStation export directory and returns a `Chrom`
(a collection of chromatogram signals, indexed by signal name such as `"280"`).

See the runnable example in `examples/chemstation_hplc/`, which uses measured CSV
data with 5 wavelengths plus fractions.
