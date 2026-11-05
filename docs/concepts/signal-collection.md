# Signal collections

Beyond a single signal, the most common object is "a group of signals to compare"
(multiple injections, multiple samples). `SignalCollection` makes the group behave
like a **dictionary indexed by name**: `coll[signal_name]` returns a signal and
`keys()` lists the names. Underneath it is still a `list[Signal]`, but
`__index_cache__` caches the name → index mapping so lookups do not scan the list
every time.

```python
@dataclass
class SignalCollection:
    """
    A SignalCollection contains multiple signals and is designed to
    easily compare and visualize them.

    - Dimensions of signals in a signal collection must be the same.
    - Signals in a collection is stored by a dictionary, you can find every signal with its name like SignalCollection[signal_name]

    Properties
    ----------
    signals: list[Signal]
        A dictionary of signals in the collection, with signal names as keys.
    name: str
        The name of the signal collection.
    plot_args: PlotArgs
        The arguments for plotting the signal collection.
    """

    signals: list[Signal] = None
    signal_type: type = Signal
    visible_signal_names: list[str] = None
    name: str = None
    description_annotations: list[DescAnno] = None
    plot_args: SignalPlotArgs = None
    __index_cache__: dict = None

    @property
    def signal_names(self):
        return [signal.name for signal in self.signals]
```

## Working with `Signal1DCollection`

```python
from dvrazer import Signal1DCollection

# Import from a folder of CSV files.
collection = Signal1DCollection.from_folder("data/folder/")

# Create from a list of similar signals (signals are deep-copied, so changing a
# signal inside the collection does not affect the original).
collection = Signal1DCollection.from_similar_signals([sig1, sig2, sig3])
# Rename the copies while creating the collection.
collection = Signal1DCollection.from_similar_signals(
    [sig1, sig2, sig3], signal_names=["A", "B", "C"]
)

# Access signals.
sig = collection["Signal Name"]
collection.rename_signal("old_name", "new_name")
collection.remove_signal("Signal Name")

# Align axes.
collection.align_axes(0, 30)
collection.align_values(["sig1", "sig2"], 0, 1)

# Set default annotations.
collection.set_default_annotations()

# Plot.
fig, ax = collection.plot()  # mode 0: all signals on one plot
```

## See also

- [Plotting](../plotting.md) — modes 0/1/2 and `plot_args`.
- [Signal1D](signal-1d.md) — the signals stored in a collection.
- [Architecture](architecture.md) — where collections sit in the hierarchy.
