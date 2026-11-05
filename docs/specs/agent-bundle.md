# Agent bundle: docs, examples and skills with dvrazer 0.6.0

Status: implemented on `feat/agent-bundle`, targeting `dvrazer` 0.6.0. This
long-form spec records what was built and verified, not the preliminary plan.

## Motivation

`pip install dvrazer` / `uv add dvrazer` installs code. Before 0.6.0 the docs
(`README.md` + `WALKTHROUGH.md`, both Chinese), the runnable `examples/` and the
agent skills existed only in the repository, so an agent could not find material
matching its installed version. The bundle fixes that: every wheel carries
English docs, runnable examples and skills, and `bundle_path()` reports where.

## Goals and non-goals

Goals: ship docs/examples/skills in the wheel; expose one small Python discovery
API; keep the top-level checkout layout browsable; guard size, structure,
language and a real wheel install.

Non-goals: publishing to an index, a CLI or skill installer, a `src/` layout, or
bundling generated artifacts (plots, bytecode, OS metadata).

## Layout

The repository layout is unchanged; the wheel gets a copy of the three
directories at build time:

```
dvrazer/                 package source (abstract/, concrete/, instruments/, utils/)
docs/                    English documentation
examples/                runnable per-instrument scripts
skills/                  Agent Skills
tests/                   test suite and bundle guards
pyproject.toml           packaging and pytest configuration
```

```
dvrazer/_bundle/docs/       copy of top-level docs/
dvrazer/_bundle/examples/   copy of top-level examples/
dvrazer/_bundle/skills/     copy of top-level skills/
```

`[tool.hatch.build.targets.wheel.force-include]` maps them exactly; the mapping
is asserted by `tests/test_bundle_size.py`:

| Source directory | Wheel destination |
|------------------|-------------------|
| `docs` | `dvrazer/_bundle/docs` |
| `examples` | `dvrazer/_bundle/examples` |
| `skills` | `dvrazer/_bundle/skills` |

## Packaging with hatchling

`pyproject.toml` uses `hatchling` (`build-backend = "hatchling.build"`) instead
of `poetry-core`. Metadata lives in one standard `[project]` table, and the
version is declared there exactly once (`0.6.0`). `uv.lock` pins the same version
for the editable install; `tests/test_release_metadata.py` checks that the
installed metadata, `pyproject.toml` and `uv.lock` agree.

### Build-time exclusions

```toml
[tool.hatch.build]
exclude = ["/.claude", "/.beads"]
skip-excluded-dirs = true
```

- `/.claude` is excluded because `.claude/skills/dvrazer` is a tracked symlink to
  `skills/dvrazer`. Hatchling de-duplicates directories by inode; if the walker
  visits the symlink first, it prunes the real `skills/dvrazer` from the sdist,
  and the wheel then silently loses the main skill. Excluding `.claude` up front
  and not descending into it (`skip-excluded-dirs = true`) keeps the real
  directory. The slow wheel test proves the sdist contains
  `skills/dvrazer/SKILL.md` and no `.claude` entry.
- `/.beads` is the local Dolt issue-tracker database. Its backup files are
  ignored by the nested `.beads/.gitignore`, which the sdist file selection does
  not read, so an explicit exclusion keeps them out of the distribution.

### Generated-file exclusions

The wheel target also excludes bytecode, OS metadata and generated plots:

```toml
[tool.hatch.build.targets.wheel]
exclude = ["**/*.pyc", "**/.DS_Store", "**/*.png"]
```

Hatchling already skips `__pycache__/` and `.DS_Store` unconditionally; the
patterns cover the rest. These target-level patterns do not prune the
force-included directories, so the repository `.gitignore` is what keeps
generated files out of the sdist, and therefore out of the wheel:

- `*.png` and `.DS_Store` come from the "Generated plots and OS metadata" block
  in `.gitignore`; example scripts write plots next to `__file__`, so the files
  exist locally but are never committed.
- `*.pyc` (plus `__pycache__/`) comes from the Python-cache block.

The bare `data` pattern in `.gitignore` would also hide the measured fixtures
that the ChemStation example reads, so `.gitignore` re-includes exactly one
directory:

```gitignore
data
!examples/chemstation_hplc/data/
```

Everything else named `data` (the repository-level `data/`, `tests/data/`, other
examples' scratch directories) stays ignored. `tests/test_wheel_bundle.py`
asserts the two fixtures are present in the installed bundle.

`tests/test_bundle_size.py` asserts all three patterns are present.

### Build order and size

`uv build` builds the source distribution first and then builds the wheel from
that sdist (its output says `Building source distribution...` followed by
`Building wheel from source distribution...`). That is why `.gitignore` and the
sdist exclusions matter for the wheel too.

- Bundle budget: 5 MiB (`tests/test_bundle_size.py`). Its walk over the
  checkout's three directories reports roughly 2.0 MiB (59 files), leaving ample
  headroom.
- v0.6.0 wheel: about 460 KiB (472,780 bytes for the local build). Most of it is
  the ChemStation fixtures the example reads; plots and bytecode are excluded.

## Discovery API

`dvrazer/bundle.py` implements the public helper:

```python
def bundle_path(kind: Literal["docs", "examples", "skills"]) -> pathlib.Path
```

Resolution order:

1. **Installed location first.** `importlib.resources.files("dvrazer")` locates
   the package, then `_bundle/<kind>` is returned if it is a directory. If
   `files()` yields a non-filesystem `Traversable` (for example a package
   imported from a zip), the `TypeError` from `pathlib.Path(...)` is handled and
   the fallback runs.
2. **Development-checkout fallback.** Starting at the directory containing
   `bundle.py`, the code walks up until it finds a root that has both
   `pyproject.toml` and `<kind>/`, and returns `<root>/<kind>`, so editable and
   development installs work.
3. Otherwise it raises `FileNotFoundError` with a message that explains both
   expected locations and how the bundle is produced.

Validation happens before any filesystem access: a non-string `kind` raises
`TypeError`; an unknown string (including wrong case or a trailing slash) raises
`ValueError` listing `"docs"`, `"examples"` and `"skills"`.

`dvrazer/__init__.py` re-exports the function (`from .bundle import bundle_path`)
and includes it in `dvrazer.__all__`; the package docstring and `help(dvrazer)`
document it. There is **no CLI**: `pyproject.toml` declares no
`[project.scripts]`/console entry point, so agents call the API from their own
Python process.

```python
import dvrazer

docs = dvrazer.bundle_path("docs")          # .../dvrazer/_bundle/docs when installed
examples = dvrazer.bundle_path("examples")  # .../dvrazer/_bundle/examples
skills = dvrazer.bundle_path("skills")      # .../dvrazer/_bundle/skills

(docs / "index.md").read_text(encoding="utf-8")
```

## Documentation

The documentation is English-only and split from the old `README.md` +
`WALKTHROUGH.md` into 20 pages:

```
docs/index.md
docs/getting-started.md
docs/plotting.md
docs/plates.md
docs/concepts/{architecture,desc-anno,signal,signal-1d,signal-collection}.md
docs/instruments/{index,chemstation,cary-winuv,unicorn,softmax-pro,nanodrop2000,chi660e,multiscan-fc}.md
docs/development/{contributing,adding-an-instrument}.md
docs/specs/agent-bundle.md        # this page
```

`README.md` is the entry point (overview, install, quickstart, `bundle_path`
note, agent skills, links into the docs); it is currently 121 lines. Budgets are
enforced by `tests/test_docs_size.py`: `README.md` ≤ 500 lines and every
`docs/**/*.md` ≤ 2500 lines. The same test checks that every page exists and is
linked from `docs/index.md`; `tests/test_docs_links.py` checks that every
relative link in `README.md` and `docs/` resolves on disk.

Removed by this work: `WALKTHROUGH.md`, the old
`docs/Instruments/List of instruments or softwares.md` (its content moved into
`docs/instruments/index.md`), and the empty `docs/1-Dimensional Signals/` and
`docs/Matrix Signals/` directories.

## Examples

- One or more runnable scripts per instrument/read mode under `examples/`;
  every supported instrument except the Agilent Cary WinUV has one.
- The ChemStation example ships the six measured `.CSV` fixtures it reads
  (`examples/chemstation_hplc/data/`), so it runs from an installed package.
  The other scripts either generate their input in code or expect the caller to
  supply a file, which the script's help text says.
- Docstrings, comments and printed labels are English; a CJK sweep over
  `examples/**/*.py` is enforced by `tests/test_examples_language.py`.
- Scripts resolve input paths relative to `__file__` and write output next to
  themselves (`example.png`, `example_*.png`), so an agent can copy a script and
  run it from any directory. Generated PNGs are never committed (`*.png` ignored).

## Skills

Two Agent Skills ship in `skills/` and in the wheel:

| Skill | Purpose |
|-------|---------|
| `skills/dvrazer` | Using the library: imports, instrument parsers, analysis, plotting, and finding the installed bundle. References: `references/instruments.md`, `references/plotting.md`. |
| `skills/dvrazer-add-instrument` | Working in the repository: adding or fixing a parser, its tests, example and docs. |

- `skills/dvrazer/SKILL.md` has a "Finding installed docs, examples and skills"
  section with runnable `bundle_path(...)` calls;
  `tests/test_skill_symlink.py` executes the documented lookups.
- `.claude/skills/dvrazer` is a tracked relative symlink
  (`120000`, `../../skills/dvrazer`), so Claude Code loads the live skill in a
  fresh checkout. The test asserts it stays a symlink and resolves to
  `skills/dvrazer`.
- No installer is shipped. Users point their skill manager at `skills/`, at
  `dvrazer.bundle_path("skills")`, or at the checked-in Claude Code symlink.

## Test guards

| File | What it protects |
|------|------------------|
| `tests/test_bundle_size.py` | The three source directories exist; the force-include mapping is exact; `*.png`/`*.pyc`/`.DS_Store` are gitignored; docs+examples+skills stay under 5 MiB. |
| `tests/test_bundle_path.py` | All three kinds resolve in a dev checkout; an installed bundle wins over the checkout; the fallback works; `FileNotFoundError`, `ValueError` and `TypeError` paths; validation before filesystem access; public re-export and `help(dvrazer)`. |
| `tests/test_docs_size.py` | Every docs page exists and is linked from `docs/index.md`; `README.md` ≤ 500 lines; each `docs/**/*.md` ≤ 2500 lines. |
| `tests/test_docs_links.py` | Every relative link in `README.md` and `docs/` resolves on disk. |
| `tests/test_examples_language.py` | No CJK characters in any `examples/**/*.py`. |
| `tests/test_skill_symlink.py` | `.claude/skills/dvrazer` is a symlink to `skills/dvrazer`; the skill documents and runs the three `bundle_path(...)` lookups; the paths contain the expected files. |
| `tests/test_wheel_bundle.py` | Fast: `.claude` and `.beads` are build-excluded and `skip-excluded-dirs` is on. Slow: `uv build` produces one wheel and one sdist; the sdist ships `skills/dvrazer/SKILL.md` and no `.claude`; the wheel installs into a temp venv, `bundle_path()` resolves inside that venv (not the checkout), and the bundles contain the required files and no `.pyc`/`.png`/`.DS_Store`/`__pycache__`. |
| `tests/test_release_metadata.py` | Installed metadata, `pyproject.toml` and `uv.lock` agree on 0.6.0; `xlrd` is declared because pandas uses it for the Unicorn 5 `.xls` files. |

The wheel test is marked `slow`; `addopts = ["-m", "not slow"]` deselects it by
default, and `uv run pytest -m slow` runs it.

## Development environment

The project uses uv (dependency groups in `pyproject.toml`, lockfile
`uv.lock`):

```bash
uv sync                       # create/update .venv and install the project
uv run pytest                 # fast suite (slow wheel test deselected)
uv run pytest -m slow         # the wheel build/install test
uv build                      # sdist first, then wheel from the sdist
```

`AGENTS.md` was removed; its rules no longer apply. Dependencies include `xlrd`
(the engine pandas uses for legacy `.xls`, needed by the Unicorn 5 parser).
`python-calamine` is still declared (it predates the switch of the `.xls` path to
pandas + `xlrd`) but has no call sites in `dvrazer/`; it is kept for now and
flagged as a follow-up below.

## Decisions

| Decision | Rejected alternative | Why |
|----------|----------------------|-----|
| hatchling | keep `poetry-core` | Standard `[project]` metadata and a declarative force-include mapping; no second packaging configuration. |
| Keep top-level directories, copy them into `dvrazer/_bundle/` at build time | Move them under `dvrazer/` or publish a separate bundle package | The checkout stays browsable; one wheel carries everything; nothing extra to version. |
| `dvrazer.bundle_path()` function | A CLI command | Agents and notebooks already run Python; no console script to maintain. |
| Installed copy first, checkout fallback | Installed-only or checkout-only | Installed answers match the installed version; editable installs keep working. |
| English docs tree | Keep the Chinese `README.md` + `WALKTHROUGH.md` | Bundled docs must be usable by agents and the wider project; the size guards keep the tree maintainable. |
| Track the `.claude/skills/dvrazer` symlink | Copy the skill directory | Claude Code loads the live skill, never a stale copy; one source of truth. |
| Examples write output beside `__file__` | A central `outputs/` directory | An agent can copy an example, run it and read the result next to it. |
| No skill installer | Ship an installer/CLI | Existing skill managers already handle discovery; the package only exposes paths. |

## Verification

Run these from the repository root; expected results are from the 0.6.0 branch.

```bash
uv sync
uv run pytest -q
# 306 passed, 1 deselected   (fast suite; the slow wheel test is deselected)
uv run pytest -m slow -q
# 1 passed                   (builds the wheel, installs it into a temp venv)
uv build --out-dir /tmp/dvrazer-dist
# Building source distribution...
# Building wheel from source distribution...
# /tmp/dvrazer-dist/dvrazer-0.6.0.tar.gz
# /tmp/dvrazer-dist/dvrazer-0.6.0-py3-none-any.whl   (~460 KiB)
uv run python -c 'import dvrazer; print(dvrazer.bundle_path("docs"))'
# prints the checkout's docs/ directory in an editable install
```

To inspect an installed wheel directly, unzip it and look for
`dvrazer/_bundle/{docs,examples,skills}`; the slow test does the equivalent in a
fresh virtual environment and fails if any `.pyc`, `.png`, `.DS_Store` or
`__pycache__` entry is present, or if `docs/index.md`,
`examples/chemstation_hplc/data/214.CSV` and `skills/dvrazer/SKILL.md` are
missing.

## Known gaps and follow-ups

- `tests/data/` is mostly untracked (only
  `tests/data/unicorn_empty_fraction.txt` is committed). Many tests read the
  local fixtures directly, so a bare clone has to provide `tests/data/` before
  the suite is meaningful; a few tests skip when their example fixture is
  missing.
- There is no CI workflow yet (`.github/workflows` does not exist); the guards in
  this spec are enforced by running `uv run pytest` locally.
- `python-calamine` is still declared although the `.xls` path now goes through
  pandas + `xlrd`; remove it or document a remaining consumer.
