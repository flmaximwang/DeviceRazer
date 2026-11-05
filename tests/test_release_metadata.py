"""Release guards: the version and the declared dependencies stay consistent.

``pyproject.toml`` is the single source of truth for the version.  ``uv.lock``
pins the same version for the editable install, and the installed distribution
metadata has to agree with both, so a release cannot ship three different
version numbers.  The dependency guard protects the documentation: the Unicorn 5
``.xls`` parser calls ``pandas.read_excel``, and pandas reads legacy ``.xls``
workbooks with the ``xlrd`` engine, so ``xlrd`` has to be a declared dependency.
"""

import importlib.metadata
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _declared_version() -> str:
    return _pyproject()["project"]["version"]


def test_installed_version_matches_pyproject():
    try:
        installed = importlib.metadata.version("dvrazer")
    except importlib.metadata.PackageNotFoundError:
        pytest.fail("dvrazer is not installed; run `uv sync` first")

    assert installed == _declared_version(), (
        f"the installed dvrazer is {installed}, but pyproject.toml declares "
        f"{_declared_version()}; run `uv sync` to refresh the environment"
    )


def test_uv_lock_pins_the_declared_version():
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = [p for p in lock["package"] if p["name"] == "dvrazer"]

    assert len(packages) == 1, "uv.lock must contain exactly one dvrazer entry"
    assert packages[0]["version"] == _declared_version(), (
        "uv.lock is out of date; run `uv lock`"
    )


def test_xls_engine_is_a_declared_dependency():
    dependencies = _pyproject()["project"]["dependencies"]

    assert any(dep.startswith("xlrd") for dep in dependencies), (
        "xlrd must be a declared dependency: it is the engine pandas uses to "
        "read the Unicorn 5 .xls exports; declared dependencies: "
        f"{dependencies}"
    )
