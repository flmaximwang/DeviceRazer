"""Tests for :func:`dvrazer.bundle_path`.

The default suite runs against the working tree (editable install), so the
top-level ``docs/``, ``examples/`` and ``skills/`` directories are reachable
through the dev-checkout fallback.  The installed-location branch is simulated
with ``tmp_path``: no wheel is built here, the slow build-and-install test
lives in its own ticket.
"""

import importlib.resources
import pathlib
import pydoc

import matplotlib
import pytest

matplotlib.use("Agg")

import dvrazer
from dvrazer import bundle
from dvrazer.bundle import bundle_path

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Every kind accepted by ``bundle_path``.
KINDS = ("docs", "examples", "skills")


def _fake_checkout(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a minimal repository checkout with the three bundle dirs."""
    root = tmp_path / "checkout"
    (root / "dvrazer").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    for kind in KINDS:
        (root / kind).mkdir()
    return root


def _fake_site_packages(
    tmp_path: pathlib.Path, kinds: tuple[str, ...] = KINDS
) -> pathlib.Path:
    """Create a minimal installed ``dvrazer`` package inside site-packages."""
    package = tmp_path / "site-packages" / "dvrazer"
    package.mkdir(parents=True)
    for kind in kinds:
        (package / "_bundle" / kind).mkdir(parents=True)
    return package


@pytest.mark.parametrize("kind", KINDS)
def test_all_kinds_resolve_in_dev_checkout(kind):
    """In this editable checkout every kind maps to the repo's top-level dir."""
    path = bundle_path(kind)

    assert isinstance(path, pathlib.Path)
    assert path == REPO_ROOT / kind
    assert path.is_dir()
    assert any(path.iterdir()), f"{path} should not be empty"


@pytest.mark.parametrize("kind", KINDS)
def test_installed_bundle_wins_over_checkout(tmp_path, monkeypatch, kind):
    """The bundle inside the installed package takes precedence."""
    package = _fake_site_packages(tmp_path)
    checkout = _fake_checkout(tmp_path)

    monkeypatch.setattr(importlib.resources, "files", lambda name: package)
    monkeypatch.setattr(bundle, "__file__", str(checkout / "dvrazer" / "bundle.py"))

    path = bundle_path(kind)

    assert path == package / "_bundle" / kind
    assert path.is_dir()


@pytest.mark.parametrize("kind", KINDS)
def test_dev_checkout_fallback_used_when_installed_bundle_absent(
    tmp_path, monkeypatch, kind
):
    """Without ``dvrazer/_bundle`` in site-packages the checkout is used."""
    package = tmp_path / "site-packages" / "dvrazer"
    package.mkdir(parents=True)  # installed package, but no _bundle directory
    checkout = _fake_checkout(tmp_path)

    monkeypatch.setattr(importlib.resources, "files", lambda name: package)
    monkeypatch.setattr(bundle, "__file__", str(checkout / "dvrazer" / "bundle.py"))

    path = bundle_path(kind)

    assert path == checkout / kind
    assert path.is_dir()


def test_missing_bundle_raises_filenotfound(tmp_path, monkeypatch):
    """Neither an installed bundle nor a checkout is available."""
    package = tmp_path / "isolated" / "site-packages" / "dvrazer"
    package.mkdir(parents=True)

    monkeypatch.setattr(importlib.resources, "files", lambda name: package)
    monkeypatch.setattr(bundle, "__file__", str(package / "bundle.py"))

    with pytest.raises(FileNotFoundError) as excinfo:
        bundle_path("docs")

    message = str(excinfo.value)
    assert "docs" in message
    # The message must explain how the bundle is produced, not just fail.
    assert "wheel" in message
    assert "docs/, examples/ and skills/" in message


@pytest.mark.parametrize("kind", ["", "doc", "Docs", "bundle", "docs ", "skills/"])
def test_unknown_kind_raises_value_error(kind):
    """A misspelled kind is a caller error, not a missing bundle."""
    with pytest.raises(ValueError) as excinfo:
        bundle_path(kind)  # type: ignore[arg-type]

    message = str(excinfo.value)
    for valid in KINDS:
        assert valid in message


@pytest.mark.parametrize("kind", [None, 1, 1.5, b"docs", ["docs"]])
def test_non_string_kind_raises_type_error(kind):
    """``kind`` must be a string."""
    with pytest.raises(TypeError):
        bundle_path(kind)  # type: ignore[arg-type]


def test_invalid_kind_is_rejected_before_filesystem_access(monkeypatch):
    """Validation runs before either lookup branch touches the filesystem."""

    def _fail(package_name):
        raise AssertionError("filesystem lookup must not happen for a bad kind")

    monkeypatch.setattr(importlib.resources, "files", _fail)

    with pytest.raises(ValueError):
        bundle_path("not-a-kind")


def test_bundle_path_is_public():
    """The helper is re-exported from the package and listed in ``__all__``."""
    assert dvrazer.bundle_path is bundle_path
    assert "bundle_path" in dvrazer.__all__


def test_help_mentions_bundle_path():
    """``help(dvrazer)`` documents the discovery API."""
    assert "bundle_path" in pydoc.render_doc(dvrazer)
