"""
Tests for the ``dvrazer.abstract`` signal core (current API).

Run with::

    /Applications/DVRazer/bin/python -m pytest tests/test_abstract.py -q

The public API exercised here is the current one:

- ``signal.axis`` (property) and ``signal.data.iloc[:, 1]`` for the data
- ``slice_axis`` / ``slice_value_by_axis``
- ``signal.axis_annotation.name`` / ``.unit`` and
  ``signal.value_annotation.name`` / ``.unit``
- ``Signal1D.from_csv`` / ``ContinuousSignal1D.from_csv`` /
  ``DiscreteSignal1D.from_csv`` / ``FractionSignal.from_csv``
- ``signal.to_csv`` (renames the file with a timestamp if it already exists)
"""

import sys

sys.path.append("..")

import numpy as np
import pandas as pd
import pytest

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D

from dvrazer import abstract
from dvrazer.abstract.signal_1d import _InterpolateBetweenBounds

DATA_DIR = "tests/data"


def make_continuous_signal(
    axis, values, stds=None, name="signal", value_name="Absorbance"
):
    """Build a small ``ContinuousSignal1D`` with Wavelength/Absorbance annotations."""
    data = {"Wavelength": list(axis), value_name: list(values)}
    if stds is not None:
        data["Value_std"] = list(stds)
    return abstract.ContinuousSignal1D.from_data(
        pd.DataFrame(data),
        axis_name="Wavelength",
        axis_unit="nm",
        value_name=value_name,
        value_unit="AU",
        name=name,
    )


class TestSignal:

    def test_from_csv(self):
        signal = abstract.Signal.from_csv(f"{DATA_DIR}/table_1.csv")
        assert isinstance(signal.data, pd.DataFrame)
        assert signal.name == "table_1"
        assert list(signal.data.columns) == ["column 1", "column 2"]

    def test_get_type_and_unit_from_header(self):
        assert abstract.Signal.get_type_and_unit_from_header("Wavelength (nm)") == (
            "Wavelength",
            "nm",
        )
        assert abstract.Signal.get_type_and_unit_from_header("mAU") == ("mAU", None)


class TestContDescAnno:

    def test_ticklabel_space_sets_major_and_minor(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = (100, 20)
        assert anno.ticklabel_space_major == 100
        assert anno.ticklabel_space_minor == 20

    def test_ticklabel_space_accepts_any_length_2_iterable(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = [0.5, 0.1]
        assert anno.ticklabel_space_major == 0.5
        assert anno.ticklabel_space_minor == 0.1
        anno.ticklabel_space = np.array([0.05, 0.01])
        assert anno.ticklabel_space_major == 0.05
        assert anno.ticklabel_space_minor == 0.01

    def test_ticklabel_space_getter_returns_pair(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space_major = 100
        anno.ticklabel_space_minor = 20
        assert anno.ticklabel_space == (100, 20)

    def test_ticklabel_space_major_updates_digits(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = (0.05, 0.01)
        assert anno.ticklabel_digits == 2

    def test_ticklabel_space_rejects_wrong_length(self):
        anno = abstract.ContDescAnno()
        with pytest.raises(ValueError):
            anno.ticklabel_space = (100,)


class TestSignal1D:

    def test_from_csv_detects_names_and_units(self):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_1_formatted.csv")
        assert type(signal) is abstract.Signal1D
        assert signal.name == "table_1_formatted"
        assert signal.axis_annotation.name == "column 1"
        assert signal.axis_annotation.unit == "unit"
        assert signal.value_annotation.name == "column 2"
        assert signal.value_annotation.unit == "unit"

    def test_from_csv_without_detection(self):
        signal = abstract.Signal1D.from_csv(
            f"{DATA_DIR}/table_1_formatted.csv",
            detect_axis_name_and_unit=False,
            detect_value_name_and_unit=False,
        )
        assert signal.axis_annotation.name == "column 1 (unit)"
        assert signal.axis_annotation.unit is None
        assert signal.value_annotation.name == "column 2 (unit)"
        assert signal.value_annotation.unit is None

    def test_from_csv_accepts_explicit_annotations(self):
        signal = abstract.Signal1D.from_csv(
            f"{DATA_DIR}/table_1_formatted.csv",
            name="custom",
            axis_name="Wavelength",
            axis_unit="nm",
            value_name="Absorbance",
            value_unit="AU",
        )
        assert signal.name == "custom"
        assert (signal.axis_annotation.name, signal.axis_annotation.unit) == (
            "Wavelength",
            "nm",
        )
        assert (signal.value_annotation.name, signal.value_annotation.unit) == (
            "Absorbance",
            "AU",
        )

    def test_axis_property(self):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        assert signal.axis.iloc[0] == 1
        np.testing.assert_allclose(
            signal.axis.to_numpy(), [1.0, 1.1, 1.2, 2.1, 2.2]
        )

    def test_value_is_the_second_column(self):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        assert signal.data.iloc[:, 1].iloc[0] == 2
        np.testing.assert_allclose(signal.data.iloc[:, 1].to_numpy(), [2, 2, 2, 2, 2])

    def test_slice_axis(self):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        np.testing.assert_allclose(signal.slice_axis(1.0, 2.0), [1.0, 1.1, 1.2, 2.0])
        np.testing.assert_allclose(
            signal.slice_axis(1.0, 2.0, include_limit=False), [1.0, 1.1, 1.2]
        )
        np.testing.assert_allclose(
            signal.slice_axis(1.05, 1.95), [1.05, 1.1, 1.2, 1.95]
        )

    def test_slice_value_by_axis(self):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        np.testing.assert_allclose(signal.slice_value_by_axis(1, 2), [2, 2, 2])

    def test_axis_setter_converts_int_to_float(self):
        """Assigning float values to an int64 axis column via setter should not raise TypeError."""
        df = pd.DataFrame(
            {
                "time_s": [0, 60, 120, 180],
                "absorbance": [0.1, 0.2, 0.3, 0.4],
            }
        )
        # Force axis column to int64 like SoftMax Pro parsed data
        df.iloc[:, 0] = df.iloc[:, 0].astype(np.int64)
        signal = abstract.Signal1D(
            data=df,
            name="test_signal",
            description_annotations=[
                abstract.ContDescAnno(name="Time", unit="s"),
                abstract.ContDescAnno(name="Absorbance", unit="AU"),
            ],
        )
        # This used to raise pandas.errors.LossySetitemError / TypeError
        signal.axis = signal.axis / 60
        assert signal.axis.iloc[0] == 0.0
        assert signal.axis.iloc[1] == 1.0
        assert signal.axis.dtype == np.float64

    def test_plot_at_is_the_abstract_placeholder(self):
        """``Signal1D.plot_at`` only returns a placeholder line handle."""
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        fig, ax = plt.subplots()
        try:
            handle = signal.plot_at(ax)
            assert type(signal).plot_at is abstract.Signal1D.plot_at
            assert isinstance(handle, Line2D)
            assert len(ax.lines) == 1
            np.testing.assert_allclose(ax.lines[0].get_xdata(), [0])
            np.testing.assert_allclose(ax.lines[0].get_ydata(), [0])
        finally:
            plt.close(fig)

    def test_to_csv(self, tmp_path):
        signal = abstract.Signal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        csv = tmp_path / "table_2_export.csv"
        signal.to_csv(csv)
        assert csv.exists()
        exported = pd.read_csv(csv)
        assert list(exported.columns) == ["column 1", "column 2"]
        assert len(exported) == 5

        # An existing file is renamed with a timestamp instead of overwritten
        with pytest.warns(UserWarning):
            signal.to_csv(csv)
        exported_files = sorted(path.name for path in tmp_path.iterdir())
        assert len(exported_files) == 2
        assert any(name.startswith("table_2_export_") for name in exported_files)


class TestContinuousSignal1D:

    def test_from_csv_detects_names_and_units(self):
        signal = abstract.ContinuousSignal1D.from_csv(f"{DATA_DIR}/UV_Vis_1.csv")
        assert type(signal) is abstract.ContinuousSignal1D
        assert signal.name == "UV_Vis_1"
        assert signal.axis_annotation.name == "Wavelength"
        assert signal.axis_annotation.unit == "nm"
        assert signal.value_annotation.name == "1mm Absorbance"
        assert signal.value_annotation.unit is None

    def test_annotations_can_be_changed(self):
        signal = abstract.ContinuousSignal1D.from_csv(f"{DATA_DIR}/UV_Vis_1.csv")
        signal.axis_annotation.name = "Wavelength"
        signal.axis_annotation.unit = "nm"
        signal.value_annotation.name = "1 mm Absorbance"
        signal.value_annotation.unit = "AU"
        assert signal.axis_annotation.label == "Wavelength (nm)"
        assert signal.value_annotation.label == "1 mm Absorbance (AU)"

    def test_chromatography_annotations(self):
        signal = abstract.ContinuousSignal1D.from_csv(
            f"{DATA_DIR}/chromatography_UV_1.csv"
        )
        assert signal.axis_annotation.name == "ml"
        assert signal.axis_annotation.unit is None
        assert signal.value_annotation.name == "mAU"
        assert signal.value_annotation.unit is None

        signal.axis_annotation.name = "Volume"
        signal.axis_annotation.unit = "ml"
        signal.value_annotation.name = "280 nm"
        signal.value_annotation.unit = "mAU"
        assert signal.axis_annotation.label == "Volume (ml)"
        assert signal.value_annotation.label == "280 nm (mAU)"

    def test_get_peak_between(self):
        signal = abstract.ContinuousSignal1D.from_csv(f"{DATA_DIR}/table_2.csv")
        peak_axis, peak_value = signal.get_peak_between(1, 2)
        assert peak_axis == pytest.approx(1.0)
        assert peak_value == pytest.approx(2.0)

    def test_plot_at_returns_a_line_handle(self):
        signal = abstract.ContinuousSignal1D.from_csv(f"{DATA_DIR}/UV_Vis_1.csv")
        fig, ax = plt.subplots()
        try:
            handle = signal.plot_at(ax)
            assert isinstance(handle, Line2D)
            assert len(ax.lines) == 1
        finally:
            plt.close(fig)


class TestDiscreteSignal1D:

    def test_from_csv(self):
        signal = abstract.DiscreteSignal1D.from_csv(f"{DATA_DIR}/fraction_1.csv")
        assert type(signal) is abstract.DiscreteSignal1D
        assert signal.name == "fraction_1"
        assert signal.axis_annotation.name == "Volume"
        assert signal.axis_annotation.unit == "ml"
        assert signal.value_annotation.name == "Fraction"
        assert signal.value_annotation.unit is None

    def test_from_csv_detection_flags_are_forwarded(self):
        signal = abstract.DiscreteSignal1D.from_csv(
            f"{DATA_DIR}/UV_Vis_1.csv",
            detect_axis_name_and_unit=False,
            detect_value_name_and_unit=True,
            value_name=None,
        )
        assert signal.axis_annotation.name == "Wavelength (nm)"
        assert signal.axis_annotation.unit is None
        assert signal.value_annotation.name == "1mm Absorbance"

    def test_from_csv_name_and_annotations_are_forwarded(self):
        signal = abstract.DiscreteSignal1D.from_csv(
            f"{DATA_DIR}/fraction_1.csv",
            name="fractions",
            axis_name="Volume",
            axis_unit="mL",
            value_name=None,
        )
        assert signal.name == "fractions"
        assert (signal.axis_annotation.name, signal.axis_annotation.unit) == (
            "Volume",
            "mL",
        )
        assert signal.value_annotation.name == "Fraction"


class TestFractionSignal:

    def test_from_csv(self):
        signal = abstract.FractionSignal.from_csv(
            f"{DATA_DIR}/fraction_1.csv", axis_unit="ml"
        )
        assert type(signal) is abstract.FractionSignal
        assert signal.name == "fraction_1"
        assert (signal.axis_annotation.name, signal.axis_annotation.unit) == (
            "Volume",
            "ml",
        )
        assert signal.value_annotation.name == "Fraction"
        np.testing.assert_array_equal(
            np.asarray(signal.value),
            ["Bottle 1", "waste", "Bottle 2", "waste"],
        )

    def test_from_csv_accepts_name_and_annotations(self):
        signal = abstract.FractionSignal.from_csv(
            f"{DATA_DIR}/fraction_1.csv",
            name="fractions",
            axis_name="Volume",
            axis_unit="mL",
        )
        assert signal.name == "fractions"
        assert (signal.axis_annotation.name, signal.axis_annotation.unit) == (
            "Volume",
            "mL",
        )

    def test_to_csv_roundtrip(self, tmp_path):
        signal = abstract.FractionSignal.from_csv(
            f"{DATA_DIR}/fraction_1.csv", axis_unit="ml"
        )
        signal.axis_annotation.name = "Volume"
        csv = tmp_path / "fraction_export.csv"
        signal.to_csv(csv)
        assert csv.exists()
        exported = pd.read_csv(csv)
        assert list(exported.columns) == ["Volume (ml)", "Fraction"]
        assert exported["Fraction"].tolist() == [
            "Bottle 1",
            "waste",
            "Bottle 2",
            "waste",
        ]

    def test_plot_at_draws_fraction_marks(self):
        signal = abstract.FractionSignal.from_csv(
            f"{DATA_DIR}/fraction_1.csv", axis_unit="ml"
        )
        fig, ax = plt.subplots()
        try:
            handle = signal.plot_at(ax)
            assert isinstance(handle, Line2D)
            assert len(ax.collections) == 1  # vertical marks
            assert len(ax.texts) == len(signal.data)  # one annotation per fraction
        finally:
            plt.close(fig)


class TestContinuousSignal1DArithmetic:
    """Regression tests for ``__mul__`` / ``__truediv__`` between two signals."""

    def test_multiplication_without_std(self):
        signal = make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="s")
        result = signal * signal
        assert result.data.shape[1] == 2  # no empty ``y_std`` column
        np.testing.assert_allclose(np.asarray(result.value), [4.0, 16.0, 64.0])
        assert result.name == "(s) * (s)"

    def test_division_without_std(self):
        signal = make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="s")
        result = signal / signal
        assert result.data.shape[1] == 2
        np.testing.assert_allclose(np.asarray(result.value), [1.0, 1.0, 1.0])

    def test_multiplication_with_std_propagates_std(self):
        a = make_continuous_signal(
            [0.0, 1.0, 2.0], [2.0, 4.0, 8.0], stds=[0.2, 0.4, 0.8], name="a"
        )
        b = make_continuous_signal(
            [0.0, 1.0, 2.0], [1.0, 2.0, 4.0], stds=[0.1, 0.2, 0.4], name="b"
        )
        result = a * b
        assert result.data.shape[1] == 3
        assert result.value_std is not None
        expected_value = np.array([2.0, 8.0, 32.0])
        expected_std = np.abs(expected_value) * np.sqrt(
            (np.array([0.2, 0.4, 0.8]) / np.array([2.0, 4.0, 8.0])) ** 2
            + (np.array([0.1, 0.2, 0.4]) / np.array([1.0, 2.0, 4.0])) ** 2
        )
        np.testing.assert_allclose(np.asarray(result.value), expected_value)
        np.testing.assert_allclose(np.asarray(result.value_std), expected_std)

    def test_division_with_std_propagates_std(self):
        a = make_continuous_signal(
            [0.0, 1.0, 2.0], [2.0, 4.0, 8.0], stds=[0.2, 0.4, 0.8], name="a"
        )
        b = make_continuous_signal(
            [0.0, 1.0, 2.0], [1.0, 2.0, 4.0], stds=[0.1, 0.2, 0.4], name="b"
        )
        result = a / b
        assert result.data.shape[1] == 3
        expected_value = np.array([2.0, 2.0, 2.0])
        expected_std = np.abs(expected_value) * np.sqrt(
            (np.array([0.2, 0.4, 0.8]) / np.array([2.0, 4.0, 8.0])) ** 2
            + (np.array([0.1, 0.2, 0.4]) / np.array([1.0, 2.0, 4.0])) ** 2
        )
        np.testing.assert_allclose(np.asarray(result.value), expected_value)
        np.testing.assert_allclose(np.asarray(result.value_std), expected_std)

    def test_multiplication_uses_union_axis(self):
        a = make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="a")
        b = make_continuous_signal([0.0, 1.5, 2.0], [1.0, 2.0, 4.0], name="b")
        result = a * b
        np.testing.assert_allclose(np.asarray(result.axis), [0.0, 1.0, 1.5, 2.0])
        np.testing.assert_allclose(
            np.asarray(result.value), [2.0, 4.0 * (1.0 + 1.0 / 1.5), 12.0, 32.0]
        )

    def test_division_uses_union_axis(self):
        a = make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="a")
        b = make_continuous_signal([0.0, 1.5, 2.0], [1.0, 2.0, 4.0], name="b")
        result = a / b
        np.testing.assert_allclose(np.asarray(result.axis), [0.0, 1.0, 1.5, 2.0])
        np.testing.assert_allclose(
            np.asarray(result.value), [2.0, 4.0 / (1.0 + 1.0 / 1.5), 3.0, 2.0]
        )

    def test_std_is_interpolated_on_the_union_axis(self):
        a = make_continuous_signal(
            [0.0, 1.0, 2.0], [2.0, 4.0, 8.0], stds=[0.2, 0.4, 0.8], name="a"
        )
        b = make_continuous_signal(
            [0.0, 1.5, 2.0], [1.0, 2.0, 4.0], stds=[0.1, 0.2, 0.4], name="b"
        )
        result = a * b
        b_std_at_1 = np.interp(1.0, [0.0, 1.5, 2.0], [0.1, 0.2, 0.4])
        b_value_at_1 = np.interp(1.0, [0.0, 1.5, 2.0], [1.0, 2.0, 4.0])
        expected_at_1 = abs(4.0 * b_value_at_1) * np.sqrt(
            (0.4 / 4.0) ** 2 + (b_std_at_1 / b_value_at_1) ** 2
        )
        np.testing.assert_allclose(
            np.asarray(result.value_std)[1], expected_at_1, rtol=1e-12
        )

    def test_different_annotations_raise(self):
        a = make_continuous_signal([0.0, 1.0], [1.0, 2.0], name="a")
        b = make_continuous_signal(
            [0.0, 1.0], [1.0, 2.0], name="b", value_name="Transmittance"
        )
        with pytest.raises(ValueError):
            a * b
        with pytest.raises(ValueError):
            a / b

    def test_division_by_zero_raises(self):
        a = make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="a")
        b = make_continuous_signal([0.0, 1.0, 2.0], [1.0, 0.0, 4.0], name="b")
        with pytest.raises(ValueError):
            a / b


class TestIntegrateBetween:
    """Regression tests for ``ContinuousSignal1D.integrate_between``."""

    @staticmethod
    def triangle():
        # Triangle with base 2 and height 1 -> area = 1/2 * 2 * 1 = 1
        return make_continuous_signal([0.0, 1.0, 2.0], [0.0, 1.0, 0.0], name="triangle")

    def test_triangle_area(self):
        assert self.triangle().integrate_between(0, 2) == pytest.approx(0.5 * 2 * 1)

    def test_partial_range_area(self):
        assert self.triangle().integrate_between(0, 1) == pytest.approx(0.5)

    def test_scalar_baseline_is_subtracted(self):
        assert self.triangle().integrate_between(0, 2, baseline=0.5) == pytest.approx(
            0.0
        )

    def test_iterable_baseline(self):
        assert self.triangle().integrate_between(
            0, 2, baseline=[0.0, 0.5, 0.0]
        ) == pytest.approx(0.5)

    def test_wrong_baseline_length_raises(self):
        with pytest.raises(ValueError, match="Baseline"):
            self.triangle().integrate_between(0, 2, baseline=[0.0, 0.0])

    def test_no_data_in_range_raises(self):
        with pytest.raises(ValueError):
            self.triangle().integrate_between(5, 6)

    def test_draws_the_integrated_region(self):
        signal = self.triangle()
        fig, ax = plt.subplots()
        try:
            area = signal.integrate_between(0, 2, ax=ax, color="C1", alpha=0.3)
            assert area == pytest.approx(1.0)
            # filled region (PolyCollection) + boundary lines (LineCollection)
            assert any(isinstance(c, PolyCollection) for c in ax.collections)
            assert any(isinstance(c, LineCollection) for c in ax.collections)
        finally:
            plt.close(fig)


class TestFilterByMovingAverage:
    """Regression tests for ``ContinuousSignal1D.filter_by_moving_average``."""

    AXIS = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    VALUES = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def make_signal(self, stds=None):
        return make_continuous_signal(self.AXIS, self.VALUES, stds=stds, name="signal")

    @pytest.mark.parametrize("window", [1, 2, 3, 4, 5, 6])
    def test_output_length_axis_and_values(self, window):
        signal = self.make_signal()
        signal.filter_by_moving_average(window)
        weights = np.ones(window) / window
        assert len(signal.data) == len(self.VALUES) - window + 1
        np.testing.assert_allclose(
            np.asarray(signal.axis), np.convolve(self.AXIS, weights, mode="valid")
        )
        np.testing.assert_allclose(
            np.asarray(signal.data.iloc[:, 1]),
            np.convolve(self.VALUES, weights, mode="valid"),
        )

    def test_known_values_for_window_3(self):
        signal = self.make_signal()
        signal.filter_by_moving_average(3)
        np.testing.assert_allclose(np.asarray(signal.value), [2.0, 3.0, 4.0, 5.0])
        np.testing.assert_allclose(np.asarray(signal.axis), [1.0, 2.0, 3.0, 4.0])

    def test_std_column_is_filtered(self):
        stds = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        signal = self.make_signal(stds=stds)
        signal.filter_by_moving_average(2)
        assert signal.value_std is not None
        assert signal.data.shape[1] == 3
        np.testing.assert_allclose(
            np.asarray(signal.value_std),
            np.convolve(stds, np.ones(2) / 2, mode="valid"),
        )

    def test_no_std_column_stays_two_columns(self):
        signal = self.make_signal()
        signal.filter_by_moving_average(2)
        assert signal.value_std is None
        assert signal.data.shape[1] == 2

    def test_window_larger_than_signal_raises(self):
        with pytest.raises(ValueError):
            self.make_signal().filter_by_moving_average(len(self.VALUES) + 1)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            self.make_signal().filter_by_moving_average(0)


class TestRescaleBetween:
    """Regression tests for ``ContinuousSignal1D.rescale_between``."""

    def make_signal(self):
        return make_continuous_signal([0.0, 1.0, 2.0], [2.0, 4.0, 8.0], name="signal")

    def test_returns_rescaled_values_without_mutating(self):
        signal = self.make_signal()
        values = signal.rescale_between(2, 8)
        np.testing.assert_allclose(values, [0.0, 1.0 / 3.0, 1.0])
        np.testing.assert_allclose(np.asarray(signal.data.iloc[:, 1]), [2.0, 4.0, 8.0])

    def test_inplace_writes_the_rescaled_values_back(self):
        signal = self.make_signal()
        returned = signal.rescale_between(2, 8, inplace=True)
        np.testing.assert_allclose(returned, [0.0, 1.0 / 3.0, 1.0])
        np.testing.assert_allclose(
            np.asarray(signal.data.iloc[:, 1]), [0.0, 1.0 / 3.0, 1.0]
        )

    def test_inplace_promotes_an_integer_column_to_float(self):
        data = pd.DataFrame({"axis": [0.0, 1.0, 2.0], "values": [2, 4, 8]})
        signal = abstract.ContinuousSignal1D.from_data(
            data, axis_name="axis", value_name="values"
        )
        signal.rescale_between(2, 8, inplace=True)
        np.testing.assert_allclose(
            np.asarray(signal.data.iloc[:, 1]), [0.0, 1.0 / 3.0, 1.0]
        )
        assert signal.data.iloc[:, 1].dtype == np.float64

    def test_identical_targets_raise(self):
        with pytest.raises(ValueError):
            self.make_signal().rescale_between(1, 1)


class TestContinuousSignal1DValueAndStdView:
    """``signal.value[axis]`` / ``signal.std[axis]`` 插值视图"""

    AXIS = np.array([280.0, 281.0, 282.0])
    VALUES = np.array([0.5, 0.7, 0.9])
    STDS = np.array([0.1, 0.2, 0.4])

    def make_signal(self, with_std=True):
        data = {"Wavelength": self.AXIS.copy(), "Abs": self.VALUES.copy()}
        if with_std:
            data["Value_std"] = self.STDS.copy()
        return abstract.ContinuousSignal1D.from_data(
            pd.DataFrame(data),
            axis_name="Wavelength",
            axis_unit="nm",
            value_name="Abs",
            value_unit="AU",
        )

    # ---------------- value ----------------

    def test_value_view_equals_getitem(self):
        signal = self.make_signal()
        for axis_i in (280.0, 280.5, 281.5, 282.0):
            assert np.isclose(signal.value[axis_i], signal[axis_i])
        assert np.isclose(signal.value[280.5], 0.6)

    def test_value_view_interpolates_between_points(self):
        signal = self.make_signal()
        assert np.isclose(signal.value[280.0], 0.5)
        assert np.isclose(signal.value[281.0], 0.7)
        assert np.isclose(signal.value[280.5], 0.6)
        assert np.isclose(signal.value[281.5], 0.8)

    def test_value_view_accepts_axis_list_and_slice(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.value[[280.5, 281.5]], [0.6, 0.8])
        # slice 按 axis 范围解释
        np.testing.assert_allclose(signal.value[280:283], self.VALUES)
        np.testing.assert_allclose(
            signal.value[280.0:283.0:0.5], [0.5, 0.6, 0.7, 0.8, 0.9, 0.9]
        )

    def test_value_view_is_array_like(self):
        signal = self.make_signal()
        assert len(signal.value) == 3
        np.testing.assert_allclose(list(signal.value), self.VALUES)
        np.testing.assert_allclose(np.asarray(signal.value), self.VALUES)
        np.testing.assert_allclose(signal.value.to_numpy(), self.VALUES)
        assert signal.value.dtype == np.float64
        assert np.isclose(signal.value.mean(), 0.7)
        assert np.isclose(signal.value.std(), 0.2)
        assert np.isclose(min(signal.value), 0.5)
        assert np.isclose(max(signal.value), 0.9)

    def test_value_view_supports_arithmetic(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.value + 1, [1.5, 1.7, 1.9])
        np.testing.assert_allclose(1 + signal.value, [1.5, 1.7, 1.9])
        np.testing.assert_allclose(signal.value * 2, [1.0, 1.4, 1.8])
        np.testing.assert_allclose(signal.value / 2, [0.25, 0.35, 0.45])
        np.testing.assert_allclose(2 - signal.value, [1.5, 1.3, 1.1])
        np.testing.assert_allclose(-signal.value, [-0.5, -0.7, -0.9])
        np.testing.assert_allclose(
            np.convolve(signal.value, np.ones(2) / 2, mode="valid"), [0.6, 0.8]
        )

    def test_value_view_keeps_signal_arithmetic_working(self):
        signal = self.make_signal()
        assert np.isclose((signal + 1)[280.5], 1.6)
        assert np.isclose((signal * 2)[280.5], 1.2)
        assert np.isclose((signal / 2)[280.5], 0.3)
        assert np.isclose((-signal)[280.5], -0.6)
        assert np.isclose((signal - signal)[280.5], 0.0)

    def test_value_setter_still_works(self):
        signal = self.make_signal()
        signal.value = [1.0, 2.0, 3.0]
        np.testing.assert_allclose(signal.data.iloc[:, 1], [1.0, 2.0, 3.0])
        assert np.isclose(signal.value[280.5], 1.5)

    # ---------------- std ----------------

    def test_std_view_returns_data_points(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.std[self.AXIS], self.STDS)

    def test_std_view_interpolates_between_bounds(self):
        """280.5 处的 std 由 280 与 281 的上下限插值得到"""
        signal = self.make_signal()
        # 280: 上下限 0.4 / 0.6; 281: 上下限 0.5 / 0.9
        # 280.5 插值后: 下限 0.45, 上限 0.75 → std = 0.15
        assert np.isclose(signal.std[280.5], 0.15)
        assert np.isclose(signal.std[281.5], 0.3)
        # 上下限对称时, 线性插值的结果与直接对 value_std 插值一致
        assert np.isclose(signal.std[280.5], np.interp(280.5, self.AXIS, self.STDS))

    def test_std_view_accepts_axis_list(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.std[[280.25, 281.75]], [0.125, 0.35])
        # slice 按 axis 范围解释
        np.testing.assert_allclose(signal.std[280:283], self.STDS)

    def test_std_view_is_array_like(self):
        signal = self.make_signal()
        assert len(signal.std) == 3
        np.testing.assert_allclose(signal.std.to_numpy(), self.STDS)
        np.testing.assert_allclose(signal.value - signal.value_std, [0.4, 0.5, 0.5])

    def test_std_view_uses_bounds_when_asymmetric(self):
        """上下限不对称时, std 由上下限插值给出 (而不是对 std 直接插值)"""
        view = _InterpolateBetweenBounds([0.0, 1.0], lower=[0.0, 0.0], upper=[1.0, 3.0])
        assert np.isclose(view[0.5], (2.0 - 0.0) / 2)
        assert np.isclose(view[0.25], (1.5 - 0.0) / 2)

    def test_std_raises_without_std_column(self):
        signal = self.make_signal(with_std=False)
        assert signal.value_std is None
        with pytest.raises(ValueError):
            signal.std

    # ---------------- 绘图 ----------------

    def test_plot_at_draws_std_band_with_value_view(self):
        signal = self.make_signal()
        signal.axis_annotation.limit = (280.0, 282.0)
        signal.value_annotation.limit = (0.4, 1.0)
        fig, ax = plt.subplots()
        try:
            handle = signal.plot_at(ax)
            assert handle is not None
            assert len(ax.collections) == 1
        finally:
            plt.close(fig)
