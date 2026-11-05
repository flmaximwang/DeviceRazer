# Multi-well plates

`MultiWellPlate` represents a microplate read as a matrix of wells.

```python
from dvrazer import MultiWellPlate

# The plate format is detected automatically (6, 12, 24, 48, 96, 384).
plate = MultiWellPlate(data=df)

# Read a well value.
value = plate["A", 1]

# Calibrate and measure with a standard curve.
fig, ax, result, table = plate.calibration_and_measurement(
    calibration_values=[0, 0.1, 0.5, 1.0],
    calibration_markers=[("A", 1), ("A", 2), ("A", 3), ("A", 4)],
    measurement_markers=[("B", 1), ("B", 2), ("B", 3)],
    xlabel="Concentration (mM)",
    ylabel="Absorbance",
)
```

Plate data usually arrives through an instrument parser: SoftMax Pro endpoint
reads become `MultiWellPlate` objects, and Multiskan FC exports are parsed into
`MultiWellPlateFC` (a `MultiWellPlate` subclass). See
[SoftMax Pro](instruments/softmax-pro.md) and
[Multiskan FC](instruments/multiscan-fc.md).
