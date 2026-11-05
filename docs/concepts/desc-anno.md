# Description annotations

## `DescAnno`

The first building block of the framework is `DescAnno`. It does one thing: binds
a data column to a **name + unit**, and combines them into the label used for
plotting and export (for example `Absorbance (a.u.)`). `unit` may be `None` — then
`label` falls back to the bare name, so columns without a unit work naturally too.

```python
@dataclass
class DescAnno:
    """
    Every signal contains multiple descriptions, which is continuous / discrete.
    This class is used to annotate each description for its
    type (like Volume), unit (like mL), limit (like (0, 10)) and ticks (like tick_number = 5)
    """

    name: str = None
    unit: str = None

    @property
    def label(self):
        if self.unit is None:
            return self.name
        else:
            return f"{self.name} ({self.unit})"
```

## `ContDescAnno`

`ContDescAnno` adds what a continuous dimension needs on top of `DescAnno`: the
range (`limit`), the plotting margin (`margin`) and the tick spacing. The clever
part is the `ticklabel_space_major` setter — **it chooses the number of decimal
places automatically from the tick spacing**: a spacing greater than 1 uses 0
decimals, greater than 0.1 uses 1 decimal, and so on. Axis labels therefore always
have exactly the precision they need, with no manual tuning. `ticklabels` starts at
`ticklabel_floor`, steps up by the spacing until `limit[1]`, and formats each
number with the chosen precision.

```python
from dvrazer import ContDescAnno

axis_annotation = ContDescAnno(
    name="Wavelength",           # physical quantity name
    unit="nm",                   # unit
    limit=(200, 800),            # data range
    margin=(0.05, 0.95),         # plotting margins
)
axis_annotation.ticklabel_space_major = 100  # tick labels are computed automatically
axis_annotation.ticklabel_space = (100, 20)  # set major and minor spacing at once
print(axis_annotation.ticklabels)      # ['200', '300', '400', ...]
print(axis_annotation.ticks)           # tick positions after scaling to margin
```

The `ticklabels` property:

```python
    @property
    def ticklabels(self):
        assert self.limit is not None, "limit is not set"
        assert (
            self.ticklabel_space_major is not None
        ), "ticklabel_space_major is not set"
        assert self.ticklabel_digits is not None, "ticklabel_digits is not set"

        if self.ticklabel_floor is None:
            ticklabel_floor = self.limit[0]
        else:
            ticklabel_floor = self.ticklabel_floor

        numbers = []
        c_number = ticklabel_floor
        while c_number <= self.limit[1]:
            numbers.append(c_number)
            c_number += self.ticklabel_space_major

        strings = [f"{num:.{self.ticklabel_digits}f}" for num in numbers]
        return strings
```

## See also

- [Signal](signal.md) — how annotations are stored per column.
- [Signal1D](signal-1d.md) — `axis_annotation` / `value_annotation` accessors.
- [Plotting](../plotting.md) — how limits and margins become figure coordinates.
