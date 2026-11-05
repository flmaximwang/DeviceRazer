# Thermo Fisher Multiskan FC

- **Data format**: TXT
- **Module**: `dvrazer.instruments.ThermoFisher.multiscan_fc`
- **Flat import**: `from dvrazer.instruments import MultiWellPlateFC`

```python
class MultiWellPlateFC(MultiWellPlate):

    @staticmethod
    def from_exported_file(txt_path, name="Default Multi-Scan Fluorescence Collection"):
        with open(txt_path, "r") as f:
            flag = False
            data_txt = ""
            for line in f:
                if not flag and "\t1\t2\t3\t4\t5\t6\t7\t8\t9\t10\t11\t12" in line:
                    flag = True
                if flag:
                    data_txt += line
        my_df = pd.read_csv(io.StringIO(data_txt), sep="\t", index_col=0)

        return MultiWellPlateFC(data=my_df, name=name)
```

In a Multiskan FC `.txt` export, a pile of header text precedes the data; the real
data starts only after the line with the 12-column header. `from_exported_file`
does two things: **scan line by line until that header line turns a flag on, then
hand the text after it to pandas**, and finally construct a concrete type from the
parsed DataFrame. The whole parser is about 14 lines — which is exactly how the
architecture pays off: **to support another instrument you only change the small
piece that reads the file into a DataFrame**; the data model, plotting and
interpolation above it need no changes.

`MultiWellPlateFC` is a `MultiWellPlate` subclass, so all plate operations such as
`plate["A", 1]` and `plate.calibration_and_measurement(...)` are available — see
[Multi-well plates](../plates.md).

See the runnable example in `examples/multiscan_fc/`, which uses synthetic 96-well
data (a BSA standard curve).
