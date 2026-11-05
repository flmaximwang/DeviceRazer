# Unicorn (ÄKTA)

- **Data formats**: XLS, ASC, TXT (UTF-16 LE)
- **Modules**: `dvrazer.instruments.Cytiva.unicorn5`,
  `dvrazer.instruments.Cytiva.unicorn7` (re-exports of
  `dvrazer.instruments.GE_Heathcare.unicorn5/7`; both are equivalent)
- **Flat imports**: `Unicorn5Chrom`, `Unicorn7Project`, `Unicorn7Chrom`

## Unicorn 5

```python
from dvrazer.instruments import Unicorn5Chrom

chrom = Unicorn5Chrom.from_xls("chromatogram.xls")
# or
chrom = Unicorn5Chrom.from_asc("chromatogram.asc")

uv_signal = chrom["UV"]
cond_signal = chrom["Cond"]
```

## Unicorn 7

One Unicorn 7 export (`.txt`, UTF-16 LE) can contain several chromatograms. The
result is a `list[Chrom]` (grouped by `Chrom.N` in the file, with names
`<file name>_<N>`):

```python
from dvrazer.instruments import Unicorn7Project, Unicorn7Chrom

chroms = Unicorn7Project.read_txt("run.txt")   # -> list[Chrom]
chrom = chroms[0]

# Alias kept for compatibility with the old API (equivalent to
# Unicorn7Project.read_txt, also returns list[Chrom]).
chroms = Unicorn7Chrom.from_txt("run.txt")
```

`Unicorn7Chrom` is a subclass of `Chrom` that only provides the `from_txt` class
method; the actual parsing logic still lives in `Unicorn7Project.read_txt`, and
both return the same list of chromatograms. `instruments.Cytiva.unicorn5/7` and
`instruments.GE_Heathcare.unicorn5/7` point at the same implementation (the Cytiva
modules simply re-export it).

## Examples

- `examples/unicorn5/read_asc/` — synthetic ASC data (UV, Cond, pH, Conc)
- `examples/unicorn5/compare_difference_sec/` — compare two runs (bring your own
  ASC files)
- `examples/unicorn7/read_txt/` — read a TXT export (bring your own `example.txt`)
- `examples/unicorn7/sec/` — SEC plotting (TXT passed on the command line)
