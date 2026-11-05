# Adding an instrument

Adding an instrument means writing one parser that turns the vendor export into a
`pandas.DataFrame` and hands it to a concrete signal type. Everything above that —
the data model, plotting, interpolation, collections — is reused unchanged.

## A minimal parser

This is the complete Multiskan FC parser. The export has a pile of header lines
before the data; the parser scans for the 12-column header, sends the text after
it to pandas, and constructs a `MultiWellPlateFC` (a `MultiWellPlate` subclass):

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

## Checklist

1. **Put the parser under the vendor package.** Create
   `dvrazer/instruments/<Vendor>/<instrument>.py`. Prefer reusing a concrete type
   (`MultiWellPlate`, `Chrom`, `Spectrum`, `KineticCurve`, …) rather than inventing
   a new one; build it from the parsed DataFrame.
2. **Use a static factory method.** Instrument parsers follow the naming
   convention `from_raw_export()`, `from_exported_directory()`, `from_xls()`,
   `from_asc()`, `from_txt()`, `from_csv()`, etc.
3. **Expose it through both import paths.** Add the class (or classes) to
   `dvrazer/instruments/__init__.py` and its `__all__`, so that
   `from dvrazer.instruments import <Class>` works as well as the full module path.
4. **Add tests.** Put a parser test in `tests/test_<instrument>.py`. Test data
   belongs in `tests/data/` and only very small files (≤ 50 KB) may be committed;
   output goes to `tests/out/`. Synthetic data is preferred.
5. **Add a runnable example.** Create `examples/<instrument>/...` with English
   docstrings and comments; write outputs next to `__file__` so an agent can copy
   the script, tweak it and run it from anywhere.
6. **Document it.** Add `docs/instruments/<instrument>.md` with the data format,
   module path and flat import, then link it from both `docs/index.md` and
   `docs/instruments/index.md` (and add the vendor row to the instrument table).
7. **Update the skills.** A new parser affects the reading instructions in
   `skills/dvrazer`; follow the parser conventions in
   `skills/dvrazer-add-instrument`.

## Keep the layers clean

The dependency direction is one-way: `instruments → concrete → abstract`. A parser
imports a concrete type and produces it; it should not reach into plotting or
analysis internals. Conversely, a new instrument rarely requires touching
`abstract/` or `concrete/` at all — if the data shape does not fit, prefer
extending the concrete layer in a separate change, not bending the parser.

## Commit rules

See [Contributing](contributing.md#commit-rules) for the data and image commit
rules, and
[Architecture](../concepts/architecture.md) for the class hierarchy and key
conventions.
