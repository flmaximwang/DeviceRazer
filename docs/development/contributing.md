# Contributing

## Development environment

DVRazer uses [uv](https://docs.astral.sh/uv/) for the development environment. The
repository pins the dependencies in `uv.lock`; the development dependency group
contains `pytest`.

```bash
# Create/update .venv and install the project with its dev dependencies.
uv sync

# Run the test suite.
uv run pytest

# Build the distribution (sdist + wheel) into dist/.
uv build
```

`uv sync` is the only setup step needed after cloning. `uv run <command>` runs the
command inside the project environment, so `uv run python` and
`uv run pytest` always use the checked-in dependency set. To run a subset of the
tests, pass the paths explicitly:

```bash
uv run pytest tests/test_abstract.py
```

## Repository layout

The package is split into `abstract/` (the core data model), `concrete/` (domain
signal types), `instruments/` (vendor parsers) and `utils/` (helpers), with
dependencies pointing one way: `instruments → concrete → abstract`. See
[Architecture](../concepts/architecture.md) for the full tree and conventions.

## Tests and test data

- Tests live in `tests/`; test data lives in `tests/data/` and test output is
  written to `tests/out/`.
- Tests use `sys.path.append("..")` before importing the package.
- Some instrument modules have an `archive` suffix (legacy code) and some have a
  `processor` suffix (new code); keep that distinction when touching them.
- The `GE_Heathcare/` directory has a typo (it should be `Healthcare`) and is kept
  as-is for compatibility.
- When you change import paths, factory methods, return types or plotting
  behaviour, update the matching files under `skills/` too — see
  [skills/README.md](../../skills/README.md).

## Commit rules

- **Never commit raw data files** (instrument exports such as `.txt`, `.csv`,
  `.tsv`, `.xls`, `.asc`); commit code only.
- **Never commit generated image files** (`.png`, `.jpg`, …), unless the image is
  a diagram required by the documentation and is ≤ 100 KB.
- Example data files in `examples/` (such as `example.txt`, `example.png`) must not
  be committed — examples should use small synthetic data or generate it in code.
- Test data belongs in `tests/data/` and only very small files (≤ 50 KB) may be
  committed; large test data should be managed by CI or external storage.
- Documentation is written in English. Keep `README.md` under 500 lines and every
  page under `docs/` under 2500 lines; these limits are enforced by
  `tests/test_docs_size.py`, which also checks that `docs/index.md` links every
  documentation page.

## See also

- [Adding an instrument](adding-an-instrument.md)
- [Architecture](../concepts/architecture.md)
