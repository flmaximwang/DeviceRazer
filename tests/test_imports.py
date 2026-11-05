"""
Tests for the documented (flat) import paths.

DVRazer advertises two equivalent import styles:

- the short/flat form, e.g. ``from dvrazer import MultiWellPlate`` or
  ``from dvrazer.instruments import ChemStChrom``;
- the full module path, e.g.
  ``from dvrazer.instruments.Cytiva.unicorn7 import Unicorn7Chrom``.

These tests pin the public names that README / docstrings / skills refer to so
that a missing re-export fails here instead of in a user script.
"""

import importlib
import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

# Make the working-tree package importable even when the test is run from the
# repository root without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

#: Names re-exported by ``dvrazer`` (abstract + concrete layers).
DVRAZER_NAMES = [
    # abstract layer
    "Signal",
    "Signal1D",
    "ContinuousSignal1D",
    "DiscreteSignal1D",
    "FractionSignal",
    "SignalCollection",
    "Signal1DCollection",
    "ContinuousSignal1DCollection",
    "DescAnno",
    "ContDescAnno",
    "DiscDescAnno",
    "Matrix",
    "MatrixSeries",
    "SignalPlotArgs",
    "Signal1DPlotArgs",
    # concrete layer
    "Chrom",
    "ChromSig",
    "ChromLog",
    "AbsorbSpec",
    "AbsorbSpecCollection",
    "Spectrum",
    "MultiWellPlate",
    "MultiWellPlateSeries",
    "Voltammegram",
    "ImpedanceSpectrum",
    "KineticCurve",
]

#: Names re-exported by ``dvrazer.instruments`` (short import form).
INSTRUMENT_NAMES = [
    # Agilent
    "ChemStChrom",
    "ChemStSig",
    "ChemStFrac",
    "CaryAbsSpec",
    "CaryAbsSpecCollection",
    # CH Instruments
    "chi660eCV",
    "chi660eEIS",
    # Cytiva / GE Healthcare
    "Unicorn5Chrom",
    "Unicorn7Project",
    "Unicorn7Chrom",
    # Molecular Devices
    "SoftMaxPro_Project",
    "SoftMaxPro_Protocol",
    "SoftMaxPro_Plate",
    "SoftMaxPro_Plate_Endpoint",
    "SoftMaxPro_Plate_Kinetic",
    "SoftMaxPro_Plate_Spectrum",
    "SoftMaxPro_Group",
    "SoftMaxPro_CuvetteData",
    # Thermo Fisher
    "Nanodrop2000Workbook",
    "MultiWellPlateFC",
]


@pytest.mark.parametrize("name", DVRAZER_NAMES)
def test_dvrazer_top_level_export(name):
    """``from dvrazer import <name>`` must work."""
    import dvrazer

    assert hasattr(dvrazer, name)


@pytest.mark.parametrize("name", INSTRUMENT_NAMES)
def test_instruments_flat_export(name):
    """``from dvrazer.instruments import <name>`` must work."""
    import dvrazer.instruments

    assert hasattr(dvrazer.instruments, name)


def test_instruments_all_matches_exports():
    """Everything listed in ``__all__`` must actually be importable."""
    import dvrazer.instruments as instruments

    for name in instruments.__all__:
        assert hasattr(instruments, name), name


def test_concrete_all_matches_exports():
    """Every name in ``dvrazer.concrete.__all__`` must be importable."""
    import dvrazer.concrete as concrete

    for name in concrete.__all__:
        assert hasattr(concrete, name), name


def test_documented_full_module_paths():
    """Full module paths used in README/docstrings/skills must import."""
    modules = [
        "dvrazer.abstract",
        "dvrazer.concrete",
        "dvrazer.concrete.spectroscopy",
        "dvrazer.concrete.chromatography",
        "dvrazer.concrete.multi_well_plates",
        "dvrazer.instruments",
        "dvrazer.instruments.Agilent",
        "dvrazer.instruments.Agilent.chemstation_processor",
        "dvrazer.instruments.Agilent.cary_winuv",
        "dvrazer.instruments.CH_Instruments",
        "dvrazer.instruments.CH_Instruments.chi660e",
        "dvrazer.instruments.Cytiva",
        "dvrazer.instruments.Cytiva.unicorn5",
        "dvrazer.instruments.Cytiva.unicorn7",
        "dvrazer.instruments.GE_Heathcare",
        "dvrazer.instruments.GE_Heathcare.unicorn5",
        "dvrazer.instruments.GE_Heathcare.unicorn7",
        "dvrazer.instruments.MolecularDevices",
        "dvrazer.instruments.MolecularDevices.softmax_pro",
        "dvrazer.instruments.ThermoFisher",
        "dvrazer.instruments.ThermoFisher.nanodrop2000",
        "dvrazer.instruments.ThermoFisher.multiscan_fc",
        "dvrazer.utils",
        "dvrazer.utils.name_utils",
        "dvrazer.utils.path_utils",
        "dvrazer.utils.transform_utils",
    ]
    for module_name in modules:
        assert importlib.import_module(module_name) is not None


def test_short_and_long_imports_are_same_object():
    """The flat re-export must be the same class object, not a copy."""
    from dvrazer.instruments import Unicorn7Chrom, chi660eCV
    from dvrazer.instruments.CH_Instruments.chi660e import chi660eCV as long_chi660eCV
    from dvrazer.instruments.Cytiva.unicorn7 import Unicorn7Chrom as long_unicorn7
    from dvrazer.instruments.GE_Heathcare.unicorn7 import (
        Unicorn7Chrom as ge_unicorn7,
    )

    assert chi660eCV is long_chi660eCV
    assert Unicorn7Chrom is long_unicorn7 is ge_unicorn7


def test_one_liner_documented_imports():
    """The exact import statements printed in README/docstrings must run."""
    from dvrazer import ContinuousSignal1D, MultiWellPlate, Signal1DCollection
    from dvrazer.instruments import (
        CaryAbsSpecCollection,
        ChemStChrom,
        MultiWellPlateFC,
        Nanodrop2000Workbook,
        SoftMaxPro_Project,
        SoftMaxPro_Protocol,
        Unicorn5Chrom,
        Unicorn7Chrom,
        Unicorn7Project,
        chi660eCV,
        chi660eEIS,
    )

    assert MultiWellPlate is not None
    assert ContinuousSignal1D is not None
    assert Signal1DCollection is not None
    for cls in (
        ChemStChrom,
        chi660eCV,
        chi660eEIS,
        Nanodrop2000Workbook,
        Unicorn5Chrom,
        Unicorn7Chrom,
        Unicorn7Project,
        SoftMaxPro_Project,
        SoftMaxPro_Protocol,
        CaryAbsSpecCollection,
        MultiWellPlateFC,
    ):
        assert cls is not None
