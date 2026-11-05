"""
``dvrazer`` --- top-level package for instrument data processing
================================================================

Re-exports the three public API layers in dependency order, so the flat
imports used throughout the documentation work directly::

    from dvrazer import Signal, ContinuousSignal1D      # abstract layer
    from dvrazer import MultiWellPlate, Chrom           # concrete layer
    from dvrazer.instruments import ChemStChrom         # instrument parsers

The import order must stay abstract → instruments → concrete: parser modules
reference abstract-layer classes when they are imported and trigger
initialization of the ``concrete`` package (``concrete/__init__.py`` imports
base classes from ``abstract``).

Agent bundle
------------
Installed distributions also ship the documentation, runnable examples and
agent skills that match the installed version.  :func:`bundle_path` tells you
where they are::

    import dvrazer

    docs = dvrazer.bundle_path("docs")
    examples = dvrazer.bundle_path("examples")
    skills = dvrazer.bundle_path("skills")

``kind`` must be one of ``"docs"``, ``"examples"`` or ``"skills"``.  The copy
installed with the package is preferred; in an editable/dev checkout the
top-level directories of the repository are used instead.  A
``FileNotFoundError`` is raised when neither location has the bundle.
"""

from .abstract import *
from .instruments import *
from .concrete import *
from .utils import *
from .bundle import bundle_path

# The package has always re-exported everything public from its subpackages
# and never restricted ``from dvrazer import *``; keep that surface and make
# the one explicitly public helper part of it.
__all__ = [name for name in globals() if not name.startswith("_")]
