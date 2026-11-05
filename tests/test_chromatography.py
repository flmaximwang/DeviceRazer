"""
Tests for :class:`dvrazer.concrete.chromatography.Chrom`.

Regression tests for the missing ``get_data()`` / ``super().get_signal()``
calls in ``Chrom.correct_conc`` and ``Chrom.get_signal``.
"""

import pandas as pd
import pytest

from dvrazer.concrete.chromatography import Chrom, ChromLog, ChromSig


def _make_signal(
    name: str, axis_values, value_values, *, value_unit: str = "mAU"
) -> ChromSig:
    return ChromSig.from_data(
        data=pd.DataFrame({0: axis_values, 1: value_values}),
        axis_name="Volume",
        axis_unit="mL",
        value_name=name,
        value_unit=value_unit,
        name=name,
    )


@pytest.fixture
def chrom() -> Chrom:
    uv = _make_signal("UV", [0.0, 1.0, 2.0], [100.0, 200.0, 300.0])
    cond = _make_signal("Cond", [0.0, 1.0, 2.0], [1.0, 2.0, 3.0], value_unit="mS/cm")
    conc_b = _make_signal("Conc B", [0.0, 1.0, 2.0], [10.0, 20.0, 30.0], value_unit="%")
    return Chrom.from_similar_signals([uv, cond, conc_b], name="run_1")


def test_correct_conc_shifts_the_axis_column(chrom: Chrom):
    chrom.correct_conc(1.5)

    assert chrom["Conc B"].data.iloc[:, 0].tolist() == pytest.approx([1.5, 2.5, 3.5])
    # the value column is untouched
    assert chrom["Conc B"].data.iloc[:, 1].tolist() == pytest.approx([10.0, 20.0, 30.0])
    # and other channels are untouched
    assert chrom["UV"].data.iloc[:, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert chrom["Cond"].data.iloc[:, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])


def test_correct_conc_accepts_negative_delay(chrom: Chrom):
    chrom.correct_conc(-0.5)

    assert chrom["Conc B"].data.iloc[:, 0].tolist() == pytest.approx([-0.5, 0.5, 1.5])


def test_get_signal_returns_the_same_object_as_getitem(chrom: Chrom):
    signal = chrom.get_signal("Conc B")

    assert signal is chrom["Conc B"]
    assert signal.data.equals(chrom["Conc B"].data)
    assert signal.name == "Conc B"


def test_get_signal_returns_discrete_signals_too(chrom: Chrom):
    fractions = ChromLog.from_data(
        data=pd.DataFrame({0: [1.0, 2.0], 1: ["1", "2"]}),
        name="Fractions",
        axis_name="Volume",
        axis_unit="mL",
        value_name="Fractions",
        value_unit=None,
    )
    chrom.append(fractions)

    assert chrom.get_signal("Fractions") is chrom["Fractions"]
    assert chrom.get_signal("Fractions") is fractions


def test_get_signal_raises_keyerror_for_unknown_signal(chrom: Chrom):
    with pytest.raises(KeyError):
        chrom.get_signal("does not exist")
