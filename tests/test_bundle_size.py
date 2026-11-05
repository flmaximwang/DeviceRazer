"""Guards for the agent bundle shipped inside the wheel.

The build backend copies the top-level ``docs/``, ``examples/`` and ``skills/``
directories into ``dvrazer/_bundle/`` inside the wheel (see
``[tool.hatch.build.targets.wheel.force-include]`` in ``pyproject.toml``), so a
``pip install dvrazer`` also carries the docs, runnable examples and agent
skills that match the installed version.

These tests only look at the source tree that feeds that copy.  They use
``pathlib`` and stdlib ``tomllib`` on purpose: no build, no network, no imports
of the package under test, so they stay fast enough for the default suite.
"""

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Top-level directories bundled into the wheel under ``dvrazer/_bundle/``.
BUNDLE_DIRS = ("docs", "examples", "skills")

#: Hard cap for the bundle sources: docs + examples + skills.
MAX_BUNDLE_BYTES = 5 * 1024 * 1024  # 5 MB

#: Directories that never reach the wheel: hatchling skips bytecode caches and
#: these are local-only build/venv caches.
IGNORED_DIRS = frozenset({"__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".venv"})


def _bundle_files():
    """Yield every source file that feeds the agent bundle."""
    for name in BUNDLE_DIRS:
        for path in (REPO_ROOT / name).rglob("*"):
            if not path.is_file():
                continue
            if IGNORED_DIRS.intersection(path.relative_to(REPO_ROOT).parts):
                continue
            yield path


@pytest.mark.parametrize("name", BUNDLE_DIRS)
def test_bundle_source_dir_exists(name):
    """The bundle sources stay at the top level of the repository."""
    assert (REPO_ROOT / name).is_dir(), f"{name}/ is missing from the checkout"


def test_bundle_size_is_under_5_mb():
    """docs + examples + skills must stay under 5 MB.

    The bundle is copied into every wheel, so a regression here makes the
    distribution heavy to download and to install.
    """
    files = list(_bundle_files())
    total = sum(path.stat().st_size for path in files)
    largest = sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:5]

    assert files, "the agent bundle has no source files"
    assert total < MAX_BUNDLE_BYTES, (
        f"agent bundle sources are {total / 1024 / 1024:.2f} MB, "
        f"over the {MAX_BUNDLE_BYTES / 1024 / 1024:.0f} MB budget; "
        "largest files:\n"
        + "\n".join(
            f"  {path.stat().st_size / 1024:.1f} KB  {path.relative_to(REPO_ROOT)}" for path in largest
        )
    )


def test_pyproject_bundles_docs_examples_and_skills():
    """The wheel target force-includes the three bundle directories."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert force_include == {
        "docs": "dvrazer/_bundle/docs",
        "examples": "dvrazer/_bundle/examples",
        "skills": "dvrazer/_bundle/skills",
    }


def test_gitignore_keeps_generated_files_out_of_the_bundle():
    """Generated plots and bytecode are gitignored.

    ``uv build`` builds the wheel from the sdist, and the sdist file selection
    honours ``.gitignore``.  Ignoring generated ``*.png`` files is therefore
    what keeps the example scripts' plots (they write next to ``__file__``) out
    of the shipped bundle.
    """
    patterns = {
        line.strip()
        for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    for pattern in ("*.png", "*.pyc", ".DS_Store"):
        assert pattern in patterns, f".gitignore must keep `{pattern}` out of the bundle"
