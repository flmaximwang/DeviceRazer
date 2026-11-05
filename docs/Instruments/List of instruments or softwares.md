# Supported Instruments and Software

Every public parser class is importable both by full module path and by the
short form `from dvrazer.instruments import <Class>` (the
`dvrazer.instruments` package re-exports all public parser types;
`dvrazer/instruments/__init__.py` lists them in `__all__`).

## Agilent

- **ChemStation** — HPLC data (.csv, UTF-16 LE, tab-separated)
  - Parser: `instruments.Agilent.chemstation_processor` (new)
  - Archive: `instruments.Agilent.chemstation_archive` (legacy)

## CH Instruments

- **CHI660E** — Electrochemical Workstation (.txt)
  - Cyclic Voltammetry: `instruments.CH_Instruments.chi660e.chi660eCV`
  - Impedance Spectroscopy: `instruments.CH_Instruments.chi660e.chi660eEIS`

## Cytiva / GE Healthcare

- **Unicorn 5** — ÄKTA chromatography systems (.xls, .asc)
  - Parser: `instruments.GE_Heathcare.unicorn5.Unicorn5Chrom`
  - Alias: `instruments.Cytiva.unicorn5.Unicorn5Chrom` (re-export)
- **Unicorn 7** — ÄKTA chromatography systems (.txt, UTF-16 LE)
  - Parser: `instruments.GE_Heathcare.unicorn7.Unicorn7Project.read_txt`
    (returns `list[Chrom]`)
  - Alias: `instruments.GE_Heathcare.unicorn7.Unicorn7Chrom.from_txt`
    (delegates to `Unicorn7Project.read_txt`, same `list[Chrom]` result)
  - Alias: `instruments.Cytiva.unicorn7.Unicorn7Project` / `Unicorn7Chrom` (re-export)
- **Archive (Legacy)**
  - `instruments.Cytiva.unicorn_archive.UnicornData` / `UnicornChromtogram`

## Molecular Devices

- **SoftMax Pro** — Microplate readers (.txt / .xls, UTF-16 LE)
  - Parser: `instruments.MolecularDevices.softmax_pro.SoftMaxPro_Project`
  - Supports: Kinetic, Endpoint, Spectrum read modes
  - Supports: Absorbance, Fluorescence detection modes

## Thermo Fisher Scientific

- **NanoDrop 2000** — UV-Vis Spectrophotometer (.tsv)
  - Parser: `instruments.ThermoFisher.nanodrop2000.Nanodrop2000Workbook`
    (`from_tsv` reads only and never modifies the input file)
  - Archive: `instruments.ThermoFisher.nanodrop_utils` (legacy)
- **Multiskan FC** — Microplate reader (.txt)
  - Parser: `instruments.ThermoFisher.multiscan_fc.MultiWellPlateFC`

## Data Types Coverage

| Data Type | Abstract Base | Concrete Type | Instruments |
|-----------|--------------|---------------|-------------|
| UV-Vis Spectrum | ContinuousSignal1D | Spectrum, AbsorbSpec | NanoDrop 2000, SoftMax Pro |
| Chromatogram (UV, Cond, pH) | Signal1DCollection | Chrom | ChemStation, Unicorn 5/7 |
| Cyclic Voltammogram | SegmentedContinuousSignal1D | Voltammegram | CHI660E |
| Impedance Spectrum | Signal | ImpedanceSpectrum | CHI660E |
| Kinetic Curve | ContinuousSignal1D | KineticCurve | SoftMax Pro |
| Microplate Read | Matrix | MultiWellPlate | SoftMax Pro, Multiskan FC |
