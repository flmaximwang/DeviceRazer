"""Locate the docs/examples/skills bundle that ships with ``dvrazer``.

The wheel stores the agent bundle under ``dvrazer/_bundle/`` (see
``[tool.hatch.build.targets.wheel.force-include]`` in ``pyproject.toml``), so
an installation made with ``pip install dvrazer`` / ``uv add dvrazer`` also
carries the documentation, runnable examples and agent skills for exactly the
installed version.  During development the package is imported straight from
the checkout, where the same material lives in the top-level ``docs/``,
``examples/`` and ``skills/`` directories instead.  :func:`bundle_path` hides
that difference from callers.
"""

import importlib.resources
import pathlib
from typing import Literal, get_args

__all__ = ["bundle_path"]

#: Bundle directories that can be requested from :func:`bundle_path`.
BundleKind = Literal["docs", "examples", "skills"]

_BUNDLE_KINDS: tuple[str, ...] = get_args(BundleKind)
_VALID_KINDS = ", ".join(_BUNDLE_KINDS)


def _validate_kind(kind: object) -> str:
    """Return ``kind`` as a string, rejecting invalid values early.

    Validation happens before any filesystem access so a typo cannot be
    mistaken for a missing bundle.
    """
    if not isinstance(kind, str):
        raise TypeError(
            "bundle_path() argument 'kind' must be a string, "
            f"got {type(kind).__name__}; valid kinds are: {_VALID_KINDS}"
        )
    if kind not in _BUNDLE_KINDS:
        raise ValueError(
            f"unknown bundle kind {kind!r}; valid kinds are: {_VALID_KINDS}"
        )
    return kind


def _installed_bundle(kind: str) -> pathlib.Path | None:
    """Return ``dvrazer/_bundle/<kind>`` of the installed package, if any."""
    package = importlib.resources.files("dvrazer")
    try:
        bundle_dir = pathlib.Path(package) / "_bundle" / kind
    except TypeError:
        # ``files()`` can return a non-filesystem ``Traversable`` (e.g. for a
        # package imported from a zip archive); there is no path to hand out.
        return None
    return bundle_dir if bundle_dir.is_dir() else None


def _checkout_bundle(kind: str) -> pathlib.Path | None:
    """Return the top-level ``<checkout>/<kind>`` directory, if any."""
    package_dir = pathlib.Path(__file__).resolve().parent
    for root in (package_dir, *package_dir.parents):
        candidate = root / kind
        if (root / "pyproject.toml").is_file() and candidate.is_dir():
            return candidate
    return None


def bundle_path(kind: BundleKind) -> pathlib.Path:
    """Return the directory holding one part of the shipped agent bundle.

    Parameters
    ----------
    kind:
        Which bundle to locate: ``"docs"``, ``"examples"`` or ``"skills"``.

    Returns
    -------
    pathlib.Path
        Directory containing the documentation, runnable examples or agent
        skills that match the installed ``dvrazer`` version.

    Raises
    ------
    TypeError
        If ``kind`` is not a string.
    ValueError
        If ``kind`` is not one of the supported bundle names.
    FileNotFoundError
        If the bundle is present neither in the installed package nor in a
        development checkout.

    Notes
    -----
    Resolution order:

    1. the installed location, ``dvrazer/_bundle/<kind>``, discovered through
       :mod:`importlib.resources`;
    2. the repository checkout that contains the imported package (editable /
       development installs), i.e. ``<project-root>/<kind>``;
    3. otherwise :class:`FileNotFoundError`.
    """
    kind = _validate_kind(kind)

    installed = _installed_bundle(kind)
    if installed is not None:
        return installed

    checkout = _checkout_bundle(kind)
    if checkout is not None:
        return checkout

    raise FileNotFoundError(
        f"the dvrazer {kind!r} bundle was not found; looked for an installed "
        f"copy at dvrazer/_bundle/{kind} and for a development checkout at "
        f"<project-root>/{kind}. Installed distributions ship the bundle from "
        "the wheel build (for example `uv build` or `pip install .`); in a "
        "source checkout keep docs/, examples/ and skills/ at the project root."
    )
