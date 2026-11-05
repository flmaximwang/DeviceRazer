# Signal1D

`Signal1D` is the most-used type: by convention column 0 is the continuous axis
(wavelength, time, volume, …) and column 1 is the measured value. The two class
attributes at the top of the class body, `axis_annotation_type` /
`value_annotation_type`, are the key — **subclasses override them to tighten the
type constraints** (for example, a continuous signal's axis must be a
`ContDescAnno`). Type checking is therefore declarative instead of being repeated
inside every method.

```python
@dataclass
class Signal1D(Signal):
    axis_annotation_type = ContDescAnno
    value_annotation_type = DescAnno

    """
    1D signals are signals with two descriptions.

    - The first is called axis (which is continuous),
    - The second is called value (which may be continuous or discrete).

    Value describes the property of every point on the axis, like the absorbance of a sample at a certain wavelength.

    Properties
    ----------
    axis_name: str
        The name of the axis description, like "Time", "Volume", "Wavelength".
    axis_unit: str
        The unit of the axis description, like "min", "mL", "nm".
    value_name: str
        The name of the value description, like "Absorbance", "Intensity".
    value_unit: str
        The unit of the value description, like "mAU", "a.u.".
    """
```

## axis / value properties

The `axis` and `value` properties hide `data.iloc[:, 0]` / `data.iloc[:, 1]`, so
callers write `sig.value` instead of a column index. Their setters assign by
column **name**, not position, so changing a column name through an annotation
cannot write to the wrong column. `axis_annotation` / `value_annotation` work the
same way on the annotation list.

```python
    @property
    def axis(self):
        return self.data.iloc[:, 0]

    @axis.setter
    def axis(self, new_axis):
        self.data[self.data.columns[0]] = new_axis.astype(float)

    @property
    def axis_annotation(self):
        axis_annotation: ContDescAnno = self.description_annotations[0]
        return axis_annotation

    @axis_annotation.setter
    def axis_annotation(self, new_axis_annotation):
        self.description_annotations[0] = new_axis_annotation

    @property
    def value_annotation(self):
        value_annotation: DescAnno = self.description_annotations[1]
        return value_annotation

    @value_annotation.setter
    def value_annotation(self, new_value_annotation):
        self.description_annotations[1] = new_value_annotation

    @property
    def value(self):
        return self.data.iloc[:, 1]

    @value.setter
    def value(self, new_value):
        self.data[self.data.columns[1]] = new_value
```

## `_Interpolate`: a view that both interpolates and behaves like an array

This is the most subtle part of the library. `_Interpolate` gives `sig.value` two
identities at once: indexing by axis value runs `np.interp` and returns a linear
interpolation (`sig.value[283.5]` gives the value at that wavelength), while using
it as an array goes through `__array__` / `__len__` / `__iter__` and the full set
of arithmetic operators. **Adding interpolation therefore broke no existing code**
— old code still treats `value` as a numpy array. `_as_axis_values` additionally
reinterprets a `slice` as an axis range (`interp[280:283]` means axis positions
280, 281, 282), which is what spectrum slicing by wavelength needs.

```python
class _Interpolate:
    """A view that linearly interpolates values on a continuous axis.

    It supports both interpolation by axis value (``interp[axis_i]``) and
    array-style access (``len`` / iteration / ``np.asarray`` / arithmetic /
    ``pandas`` and ``numpy`` methods), so
    :attr:`ContinuousSignal1D_Base.value` can return it without breaking
    existing code.
    """

    def __init__(self, axis: typing.Iterable[float], value: typing.Iterable[float]):
        self.axis = np.asarray(axis, dtype=float)
        self.value = np.asarray(value, dtype=float)

    @staticmethod
    def _as_axis_values(axis_i):
        """Interpret a slice as an axis range (``interp[280:283]`` → axis 280, 281, 282);
        a missing step is treated as 1."""
        if isinstance(axis_i, slice):
            step = 1 if axis_i.step is None else axis_i.step
            return np.arange(axis_i.start, axis_i.stop, step)
        return axis_i

    def __getitem__(self, axis_i: int | float | slice | typing.Iterable[float]):
        """
        Get the value at the given axis value using 1D interpolation.
        """
        return np.interp(self._as_axis_values(axis_i), self.axis, self.value)
```

## Working with a continuous signal

```python
from dvrazer import ContinuousSignal1D

# Read from CSV (axis name and unit are detected automatically).
sig = ContinuousSignal1D.from_csv("uv_vis_spectrum.csv")

# Create from a DataFrame.
sig = ContinuousSignal1D.from_data(
    data=df,
    axis_name="Wavelength",
    axis_unit="nm",
    value_name="Absorbance",
    value_unit="AU",
)

# Interpolated access (value / std are both views interpolated by axis value).
value_at_540nm = sig[540]                 # equivalent to sig.value[540]
value_at_540_5nm = sig.value[540.5]
std_at_540_5nm = sig.std[540.5]           # interpolated from the (value ± std) bounds

# The value / std views keep array-style access as well.
sig.value.mean()                          # mean of the raw data
np.asarray(sig.value)                     # raw array (equivalent to sig.data.iloc[:, 1])
sig.value_std                             # raw standard-deviation column (None if absent)

# Peak detection.
peak_axis, peak_value = sig.get_peak_between(500, 600)

# Signal arithmetic.
result = sig1 + sig2      # add after interpolation
result = sig1 * 2         # multiply by a scalar
result = sig1 - blank     # subtract a blank
result = sig1 / sig2      # divide after interpolation

# Filtering.
sig.clean_by_moving_average(z_threshold=3)   # remove outliers
sig.filter_by_moving_average(window=5)        # moving-average smoothing
```

## Important notes

- `signal.value` / `signal.std` are views interpolated by axis value:
  `signal.value[axis_i]` is equivalent to `signal[axis_i]`; `signal.std[axis_i]`
  interpolates the `(value ± std)` upper and lower bounds separately and takes
  `(upper - lower) / 2` (when the bounds are symmetric this matches interpolating
  `value_std` directly). The views still support array-style access (`len`,
  iteration, `np.asarray`, `to_numpy`, arithmetic); use
  `signal.data.iloc[:, 1]` and `signal.value_std` for the raw arrays. Accessing
  `signal.std` on a signal without a std column raises `ValueError` (only signals
  produced by `average()` / `average_similar_signals()` carry a std).
- `DiscreteSignal1D` holds discrete values (fractions); `SegmentedSignal1D`
  (with `SegmentedContinuousSignal1D`) holds multi-segment data such as
  voltammetry.

## See also

- [Description annotations](desc-anno.md) — axis and value annotations.
- [Signal collections](signal-collection.md) — comparing many 1D signals.
- [Plotting](../plotting.md) — plotting modes for collections.
