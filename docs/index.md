# DVRazer documentation

DVRazer (import name `dvrazer`) is a Python library for processing, analyzing and
visualizing data from many kinds of scientific instruments. It provides a unified
data model and processing framework for experimental data.

## What it gives you

- **A unified data model** — a layered abstraction `Signal` → `Signal1D` /
  `Signal2D` → instrument-specific signal classes, so all instrument data is
  handled the same way.
- **A built-in description-annotation system** — every data dimension carries its
  physical meaning (name, unit, limit, tick labels), which keeps plotting and
  presentation simple.
- **Automated plotting** — several plotting modes (overlaid lines, multiple axes,
  faceted panels) with automatic axis scaling and labels.
- **Data operations** — signal arithmetic (add / subtract / multiply / divide),
  interpolation (`sig[axis]`, `sig.value[axis]`, `sig.std[axis]`), peak detection,
  region integration, smoothing and baseline correction.
- **Instrument data parsing** — built-in importers for data exported by several
  instrument vendors.

## Documentation map

New here? Start with [Getting started](getting-started.md).

### Guides

| Page | What it covers |
|------|----------------|
| [Getting started](getting-started.md) | Installation, a first example, and the bundled example scripts |
| [Plotting](plotting.md) | The three plotting modes and `plot_args` |
| [Multi-well plates](plates.md) | Reading plate data and calibration |

### Core concepts

| Page | What it covers |
|------|----------------|
| [Architecture](concepts/architecture.md) | The package layers, class hierarchy and key conventions |
| [Description annotations](concepts/desc-anno.md) | `DescAnno` / `ContDescAnno`: names, units, limits and ticks |
| [Signal](concepts/signal.md) | The `Signal` base class: `data`, `name`, `description_annotations` |
| [Signal1D](concepts/signal-1d.md) | The one-dimensional signal family, interpolation and arithmetic |
| [Signal collections](concepts/signal-collection.md) | Managing and comparing multiple signals |

### Instruments

| Page | Instrument / software |
|------|-----------------------|
| [Supported instruments](instruments/index.md) | The full instrument table, import paths and data-type coverage |
| [Agilent ChemStation](instruments/chemstation.md) | ChemStation HPLC exports |
| [Agilent Cary WinUV](instruments/cary-winuv.md) | Cary 100/300 absorbance scans |
| [Unicorn (ÄKTA)](instruments/unicorn.md) | Cytiva / GE Healthcare Unicorn 5 and 7 |
| [SoftMax Pro](instruments/softmax-pro.md) | Molecular Devices plate-reader data and post-processing |
| [NanoDrop 2000](instruments/nanodrop2000.md) | Thermo Fisher NanoDrop 2000 TSV exports |
| [CHI660E](instruments/chi660e.md) | CH Instruments electrochemical workstation |
| [Multiskan FC](instruments/multiscan-fc.md) | Thermo Fisher Multiskan FC plate-reader exports |

### Development

| Page | What it covers |
|------|----------------|
| [Contributing](development/contributing.md) | The uv workflow (`uv sync`, `uv run pytest`, `uv build`) and repository rules |
| [Adding an instrument](development/adding-an-instrument.md) | How to write a new instrument parser |

## Docs, examples and skills ship with the package

The documentation, runnable examples and agent skills are bundled inside the
installed `dvrazer` package, so an agent (or a human) can always find the material
that matches the installed version:

```python
import dvrazer

docs = dvrazer.bundle_path("docs")          # .../dvrazer/_bundle/docs
examples = dvrazer.bundle_path("examples")  # .../dvrazer/_bundle/examples
skills = dvrazer.bundle_path("skills")      # .../dvrazer/_bundle/skills
```

`dvrazer.bundle_path(kind)` accepts `"docs"`, `"examples"` or `"skills"`. It looks
in the installed package first and falls back to the repository checkout for
editable / development installs; if neither exists it raises `FileNotFoundError`.

## Agent skills

The `skills/` directory contains Agent Skills (`SKILL.md` plus reference documents)
for coding agents such as Claude Code:

| Skill | Purpose |
|-------|---------|
| `skills/dvrazer` | Using the library: reading each instrument's export (with the correct import paths), interpolation / arithmetic / averaging / peak finding, plotting modes and axis annotations |
| `skills/dvrazer-add-instrument` | Adding or fixing an instrument parser inside this repository: code locations, parser conventions, synthetic-data tests, examples, docs and commit rules |

To install them in Claude Code, symlink the skill directories (run from the
repository root; symlinks keep the skills in sync with the checkout):

```bash
mkdir -p ~/.claude/skills && ln -s "$(pwd)/skills/dvrazer" "$(pwd)/skills/dvrazer-add-instrument" ~/.claude/skills/
```

The repository already carries `.claude/skills/dvrazer` as a checked-in symlink to
`skills/dvrazer`, so Claude Code finds the main skill as soon as you open the
checkout; the command above only adds it to other projects.

When you change import paths, factory methods, return types or plotting behaviour,
update the matching files under `skills/` too — see
[skills/README.md](../skills/README.md).

## License

DVRazer is released under the terms in the [LICENSE](../LICENSE) file.
