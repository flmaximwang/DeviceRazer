# Molecular Devices SoftMax Pro

- **Data formats**: TXT (UTF-16 LE), XLS
- **Module**: `dvrazer.instruments.MolecularDevices.softmax_pro`
- **Flat imports**: `SoftMaxPro_Project`, `SoftMaxPro_Protocol`
- **Supported reads**: kinetic, endpoint and spectrum modes; absorbance and
  fluorescence detection

## Reading a project

```python
from dvrazer.instruments import SoftMaxPro_Project

project = SoftMaxPro_Project.read_txt("plate_reader_data.txt")
plate = project["Plate Name"]              # get the named plate
kinetic_data = plate["A1"]                 # kinetic curve
kinetic_data.plot_at(ax)
```

If the export also contains reduction groups (the `Group:` blocks), such as a BCA
quantification standard-curve group `Standards` and the sample groups, fetch them
with `project.group(name)`:

```python
standards = project.group("Standards")     # BCA standard-curve group
standards.data                             # Conc / Value / MeanValue ... table
plate = project["Plate1"]                  # Endpoint read as a MultiWellPlate
plate["A", 1]                              # access a well value
```

## Post-processing with `SoftMaxPro_Protocol`

Use `SoftMaxPro_Protocol` to define standard curves per well and back-calculate
unknown well concentrations (standard groups with a `fit` key of `"linear"` use
linear regression):

```python
from dvrazer.instruments import SoftMaxPro_Protocol

standards = {
    "name": "standards",
    "type": "standards",
    "fit": "linear",                                  # fit method: linear (linear regression)
    "series": [
        {"value": 0, "unit": "mg/ml", "wells": ["A1", "A2", "A3"]},
        {"value": 0.125, "unit": "mg/ml", "wells": ["B1", "B2", "B3"]},
        # ... the remaining standard concentrations
    ],
}
sample = {"name": "20mMTris", "type": "unknown", "wells": ["A4", "B4", "C4", "D4"]}
# Sample with a dilution series: each series entry is one dilution gradient and
# dilution_factor is that gradient's dilution factor.
elution = {
    "name": "Elution",
    "type": "unknown_dilution",
    "series": [
        {"dilution_factor": 1.0, "wells": ["B4", "B5", "B6"]},
        {"dilution_factor": 2.0, "wells": ["C4", "C5", "C6"]},
        {"dilution_factor": 4.0, "wells": ["D4", "D5", "D6"]},
    ],
}

protocol = SoftMaxPro_Protocol([standards, sample, elution])
protocol.apply(plate)                                 # returns self
protocol.results                                      # DataFrame: Well, Group, Value, InRange, Concentration, ...
protocol.summary                                      # one row per group (per gradient for dilution groups): Mean/SD/CV%, Dilution, AdjResult
protocol.plot_standard_curve()                        # standard-curve figure (Figure, with per-group mean ± error bars)
protocol.plot_standard_curve(groups=["Elution"])      # plot only the given unknown group(s)
protocol["Elution"]                                   # all well concentration results for a group name
protocol.fit_result                                   # linear regression result (slope, intercept, rvalue...)
```

The columns of `results` are `Well` (well), `Group` (group name), `Value`
(absorbance), `InRange` (whether the absorbance falls inside the standard range
`MinStd..MaxStd`, corresponding to SoftMax's `R` flag), `Concentration` (the
back-calculated concentration, **not corrected for dilution**) and `Unit` (the
concentration unit). The first row of each gradient also carries `MeanResult` /
`Std.Dev.` / `CV%` statistics, and `unknown_dilution` groups additionally have
`Dilution` (dilution factor) and `AdjResult` (= MeanResult × Dilution, corrected
back to the original sample concentration). `summary` is a summary table with one
row per `unknown` group and one row per dilution gradient of an
`unknown_dilution` group (n, mean and standard deviation of absorbance /
concentration, CV%, `nInRange`, `Dilution`, `AdjResult`).
`plot_standard_curve(groups=...)` defaults to `"all"` and plots every unknown
group; pass a group name (a string or a list) to plot only those groups. Each
gradient of a dilution group is plotted as one point and the legend shows the
dilution factor (e.g. `Elution 2×`).

`unknown_dilution` groups can also be analysed with a **dilution linear
regression**: regress the uncorrected back-calculated concentration (y) against
`1/dilution_factor` (x). Ideally `c_backcalc = c_original / dilution`, so **the
slope is the original sample concentration** and the intercept should be close to
0:

```python
protocol.dilution_fit                     # {group name: linregress result}, slope = original concentration
protocol.summary["FittedConcentration"]   # concentration from the fit (same for every row of a dilution group)
protocol.plot_unknown_dilution_curve()                     # dilution linearity figure (Figure)
protocol.plot_unknown_dilution_curve(groups=["Elution"])   # plot only the given dilution group(s)
```

On the dilution linearity plot each gradient is one point (x = `1/dilution`, with
the x-axis ticks labelled by the corresponding dilution factor) plus the group's
dashed regression line. The caption states the equation, R² and
`slope = ... (original concentration)`. Groups with fewer than 2 gradients in
`dilution_fit` are `None` (they cannot be regressed, and plotting raises
`ValueError`).
