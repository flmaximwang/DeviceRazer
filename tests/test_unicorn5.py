"""
Tests for Unicorn 5 (.xls) parsing.

Reading .xls files requires an Excel engine: python-calamine.  These tests
skip automatically when the engine is not installed.
"""

from pathlib import Path

import pytest

pytest.importorskip("python_calamine")

from dvrazer.concrete.chromatography import Chrom, ChromLog, ChromSig
from dvrazer.instruments.GE_Heathcare.unicorn5 import Unicorn5Chrom

DATA_DIR = Path(__file__).resolve().parent / "data"
XLS_FILE = DATA_DIR / "04PR0Z01-02-FL1.xls"


@pytest.mark.skipif(not XLS_FILE.exists(), reason="unicorn 5 example .xls is missing")
def test_from_xls_returns_a_chrom_with_signals():
    chrom = Unicorn5Chrom.from_xls(XLS_FILE)

    # from_xls keeps returning a plain Chrom built from the parsed signals
    assert isinstance(chrom, Chrom)

    signal_names = list(chrom.keys())
    for expected in ("UV", "Cond", "Pressure", "Flow", "Fractions"):
        assert expected in signal_names, (
            f"Expected {expected!r} in signals, got {signal_names}"
        )

    assert isinstance(chrom["UV"], ChromSig)
    assert isinstance(chrom["Fractions"], ChromLog)


@pytest.mark.skipif(not XLS_FILE.exists(), reason="unicorn 5 example .xls is missing")
def test_from_xls_signals_are_self_consistent():
    chrom = Unicorn5Chrom.from_xls(XLS_FILE)

    for signal_name in chrom.keys():
        signal = chrom[signal_name]
        # key and signal name agree and every signal is a 2-column frame
        assert signal.name == signal_name
        assert signal.data.shape[1] == 2
        # the axis is volume in mL for every signal of this export
        assert signal.axis_annotation.name == "Volume"
        assert signal.axis_annotation.unit == "mL"

    uv_signal = chrom["UV"]
    assert uv_signal.data.shape[0] > 100
    assert chrom["Fractions"].data.shape[0] > 0


@pytest.mark.skipif(not XLS_FILE.exists(), reason="unicorn 5 example .xls is missing")
def test_from_xls_accepts_a_name_override():
    chrom = Unicorn5Chrom.from_xls(XLS_FILE, name="renamed_run")

    assert isinstance(chrom, Chrom)
    assert chrom.name == "renamed_run"
