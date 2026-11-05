# Supported instruments

DVRazer ships parsers for the following instrument exports. Every public parser
class is importable both by its full module path and by the short form
`from dvrazer.instruments import <Class>` (the `dvrazer.instruments` package
re-exports all public parser types; `dvrazer/instruments/__init__.py` lists them
in `__all__`).

| Vendor | Instrument / software | Data format | Module |
|--------|-----------------------|-------------|--------|
| **Agilent** | ChemStation HPLC | CSV (UTF-16 LE) | `instruments.Agilent.chemstation_processor` |
| **Agilent** | Cary WinUV (Cary 100/300) | CSV | `instruments.Agilent.cary_winuv` |
| **CH Instruments** | CHI660E electrochemical workstation | TXT | `instruments.CH_Instruments.chi660e` |
| **Cytiva (GE Healthcare)** | ÄKTA / Unicorn 5, 7 | XLS, ASC, TXT (UTF-16 LE) | `instruments.Cytiva.unicorn5`, `instruments.Cytiva.unicorn7` (re-exports `instruments.GE_Heathcare.unicorn5/7`; both are equivalent) |
| **Molecular Devices** | SoftMax Pro | TXT (UTF-16 LE), XLS | `instruments.MolecularDevices.softmax_pro` |
| **Thermo Fisher** | NanoDrop 2000 | TSV | `instruments.ThermoFisher.nanodrop2000` |
| **Thermo Fisher** | Multiskan FC | TXT | `instruments.ThermoFisher.multiscan_fc` |

## Flat imports

All parsers are available through short paths, equivalent to the full module paths
above:

```python
from dvrazer.instruments import (
    ChemStChrom,          # Agilent ChemStation
    CaryAbsSpecCollection,# Agilent Cary WinUV
    chi660eCV, chi660eEIS,# CH Instruments
    Unicorn5Chrom,        # Cytiva / GE Healthcare Unicorn 5
    Unicorn7Project, Unicorn7Chrom,  # Cytiva / GE Healthcare Unicorn 7
    SoftMaxPro_Project, SoftMaxPro_Protocol,
    Nanodrop2000Workbook, # Thermo Fisher
    MultiWellPlateFC,
)
```

`dvrazer` re-exports both the abstract and the concrete layer at the top level, so
`from dvrazer import Signal, ContinuousSignal1D, MultiWellPlate, Chrom` also works;
the `__all__` lists of `dvrazer.concrete` / `dvrazer.instruments` name every public
symbol.

## Vendor details

### Agilent

- **ChemStation** — HPLC data (.csv, UTF-16 LE, tab-separated)
  - Parser: `instruments.Agilent.chemstation_processor` (current)
  - Archive: `instruments.Agilent.chemstation_archive` (legacy)
  - Page: [ChemStation](chemstation.md)
- **Cary WinUV** — absorbance scans (.csv)
  - Parser: `instruments.Agilent.cary_winuv`
  - Page: [Cary WinUV](cary-winuv.md)

### CH Instruments

- **CHI660E** — electrochemical workstation (.txt)
  - Cyclic voltammetry: `instruments.CH_Instruments.chi660e.chi660eCV`
  - Impedance spectroscopy: `instruments.CH_Instruments.chi660e.chi660eEIS`
  - Page: [CHI660E](chi660e.md)

### Cytiva / GE Healthcare

- **Unicorn 5** — ÄKTA chromatography systems (.xls, .asc)
  - Parser: `instruments.GE_Heathcare.unicorn5.Unicorn5Chrom`
  - Alias: `instruments.Cytiva.unicorn5.Unicorn5Chrom` (re-export)
- **Unicorn 7** — ÄKTA chromatography systems (.txt, UTF-16 LE)
  - Parser: `instruments.GE_Heathcare.unicorn7.Unicorn7Project.read_txt`
    (returns `list[Chrom]`)
  - Alias: `instruments.GE_Heathcare.unicorn7.Unicorn7Chrom.from_txt`
    (delegates to `Unicorn7Project.read_txt`, same `list[Chrom]` result)
  - Alias: `instruments.Cytiva.unicorn7.Unicorn7Project` / `Unicorn7Chrom`
    (re-export)
- **Archive (legacy)**
  - `instruments.Cytiva.unicorn_archive.UnicornData` / `UnicornChromtogram`
- Page: [Unicorn (ÄKTA)](unicorn.md)

### Molecular Devices

- **SoftMax Pro** — microplate readers (.txt / .xls, UTF-16 LE)
  - Parser: `instruments.MolecularDevices.softmax_pro.SoftMaxPro_Project`
  - Supports: kinetic, endpoint and spectrum read modes
  - Supports: absorbance and fluorescence detection modes
  - Post-processing: `SoftMaxPro_Protocol` for standard curves and dilution fits
  - Page: [SoftMax Pro](softmax-pro.md)

### Thermo Fisher Scientific

- **NanoDrop 2000** — UV-Vis spectrophotometer (.tsv)
  - Parser: `instruments.ThermoFisher.nanodrop2000.Nanodrop2000Workbook`
    (`from_tsv` only reads and never modifies the input file)
  - Archive: `instruments.ThermoFisher.nanodrop_utils` (legacy)
  - Page: [NanoDrop 2000](nanodrop2000.md)
- **Multiskan FC** — microplate reader (.txt)
  - Parser: `instruments.ThermoFisher.multiscan_fc.MultiWellPlateFC`
  - Page: [Multiskan FC](multiscan-fc.md)

## Data-type coverage

| Data type | Abstract base | Concrete type | Instruments |
|-----------|---------------|---------------|-------------|
| UV-Vis spectrum | `ContinuousSignal1D` | `Spectrum`, `AbsorbSpec` | NanoDrop 2000, SoftMax Pro |
| Chromatogram (UV, Cond, pH) | `Signal1DCollection` | `Chrom` | ChemStation, Unicorn 5/7 |
| Cyclic voltammogram | `SegmentedContinuousSignal1D` | `Voltammegram` | CHI660E |
| Impedance spectrum | `Signal` | `ImpedanceSpectrum` | CHI660E |
| Kinetic curve | `ContinuousSignal1D` | `KineticCurve` | SoftMax Pro |
| Microplate read | `Matrix` | `MultiWellPlate` | SoftMax Pro, Multiskan FC |
