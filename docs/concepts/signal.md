# Signal

`Signal` is the root of every data type. It holds only three things: a
`pandas.DataFrame` (`data`), a name (`name`), and a list of annotations with one
entry per DataFrame column (`description_annotations`). **The data is a table, and
the meaning lives in the annotations on its columns** — this design makes "add a
dimension" and "name / unit that dimension" two orthogonal actions. The base class
itself provides only the most generic abilities: reading and writing CSV, and
linear rescaling.

```python
@dataclass
class Signal:
    """
    a signal is composed of multiple descriptions.
    At least one description is continuous for all instruments.
    These descriptions are represented by columns in a pandas.DataFrame and therefore have equal lengths.
    More specific signals are subclasses that have defined descriptions.

    Properties
    ----------
    data: pd.DataFrame
        A pandas DataFrame containing the signal data. Each column represents a different description.
    name: str
        The name of the signal.
    description_annotations: list[DescAnno]
        A list of DescAnno objects that annotate each description in the data.
    """

    data: pd.DataFrame = None
    name: str = None
    description_annotations: list[DescAnno] = field(default_factory=list)
```

## Reading and writing

```python
from dvrazer import Signal

# Load from a CSV file.
sig = Signal.from_csv("data.csv")

# Create one yourself.
import pandas as pd
sig = Signal(
    data=pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}),
    name="My Signal",
)

# Export.
sig.to_csv("export.csv")
```

Subclasses define which columns they expect; the most common shape is
[Signal1D](signal-1d.md) with a continuous axis and a value column. Collections of
signals are handled by [SignalCollection](signal-collection.md).

## See also

- [Description annotations](desc-anno.md) — what is stored on each column.
- [Architecture](architecture.md) — where `Signal` sits in the hierarchy.
