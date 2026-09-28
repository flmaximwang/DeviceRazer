import sys

sys.path.append("..")

import unittest
import os
import pandas as pd
import numpy as np
from dvrazer import abstract


class TestSignal(unittest.TestCase):

    def test_from_csv(self):
        abstract.Signal.from_csv("tests/data/table_1.csv")


class TestContDescAnno(unittest.TestCase):

    def test_ticklabel_space_sets_major_and_minor(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = (100, 20)
        self.assertEqual(anno.ticklabel_space_major, 100)
        self.assertEqual(anno.ticklabel_space_minor, 20)

    def test_ticklabel_space_accepts_any_length_2_iterable(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = [0.5, 0.1]
        self.assertEqual(anno.ticklabel_space_major, 0.5)
        self.assertEqual(anno.ticklabel_space_minor, 0.1)
        anno.ticklabel_space = np.array([0.05, 0.01])
        self.assertEqual(anno.ticklabel_space_major, 0.05)
        self.assertEqual(anno.ticklabel_space_minor, 0.01)

    def test_ticklabel_space_getter_returns_pair(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space_major = 100
        anno.ticklabel_space_minor = 20
        self.assertEqual(anno.ticklabel_space, (100, 20))

    def test_ticklabel_space_major_updates_digits(self):
        anno = abstract.ContDescAnno()
        anno.ticklabel_space = (0.05, 0.01)
        self.assertEqual(anno.ticklabel_digits, 2)

    def test_ticklabel_space_rejects_wrong_length(self):
        anno = abstract.ContDescAnno()
        with self.assertRaises(ValueError):
            anno.ticklabel_space = (100,)


class TestSignal1D(unittest.TestCase):

    def test_from_csv(self):
        signal = abstract.Signal1D.from_csv("tests/data/table_1_formatted.csv")
        self.assertEqual(signal.get_axis_name(), "column 1 (unit)")
        self.assertEqual(signal.get_axis_unit(), None)
        self.assertEqual(signal.get_value_name(), "column 2 (unit)")
        self.assertEqual(signal.get_value_unit(), None)
        signal = abstract.Signal1D.from_csv(
            "tests/data/table_1_formatted.csv",
            detect_axis_name_and_unit=True,
            detect_value_name_and_unit=True,
        )
        self.assertEqual(signal.get_axis_name(), "column 1")
        self.assertEqual(signal.get_axis_unit(), "unit")
        self.assertEqual(signal.get_value_name(), "column 2")
        self.assertEqual(signal.get_value_unit(), "unit")

    def test_get_axis(self):
        signal = abstract.Signal1D.from_csv("tests/data/table_2.csv")
        self.assertEqual(signal.get_axis().iloc[0], 1)

    def test_get_values(self):
        signal = abstract.Signal1D.from_csv("tests/data/table_2.csv")
        self.assertEqual(signal.get_values().iloc[0], 2)

    def test_get_axis_between(self):
        signal = abstract.Signal1D.from_csv("tests/data/table_2.csv")
        print("")
        print(signal.get_axis_between(1, 2))
        self.assertEqual(signal.get_axis_between(1, 2).iloc[0], 1.1)

    def test_get_values_between(self):
        signal = abstract.Signal1D.from_csv(
            "tests/data/table_2.csv",
            detect_axis_name_and_unit=False,
            detect_value_name_and_unit=False,
        )
        self.assertEqual(signal.get_values_between(1, 2).iloc[0], 2)

    def test_preview(self):
        signal = abstract.Signal1D.from_csv("tests/data/table_2.csv")
        # 断言以下代码运行时会出现 TypeError
        with self.assertRaises(TypeError):
            signal.preview(
                export_path="tests/out/table_2_preview_with_Signal1D"
            )  # No curve will be observed because the plot_at method is not implemented in the abstract class

    def test_axis_setter_converts_int_to_float(self):
        """Assigning float values to an int64 axis column via setter should not raise TypeError."""
        df = pd.DataFrame({"time_s": [0, 60, 120, 180], "absorbance": [0.1, 0.2, 0.3, 0.4]})
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
        self.assertEqual(signal.axis.iloc[0], 0.0)
        self.assertEqual(signal.axis.iloc[1], 1.0)
        self.assertEqual(signal.axis.dtype, np.float64)


class TestNumericSignal1D(unittest.TestCase):

    def test_get_peak_between(self):
        signal = abstract.ContinuousSignal1DBase.from_csv(
            "tests/data/table_2.csv",
            detect_axis_name_and_unit=False,
            detect_value_name_and_unit=False,
        )
        self.assertEqual(signal.get_peak_between(1, 2), (1.1, 2))

    def test_preview(self):
        signal = abstract.ContinuousSignal1DBase.from_csv("tests/data/UV_Vis_1.csv")
        self.assertEqual(signal.get_axis_name(), "Wavelength (nm)")
        self.assertEqual(signal.get_axis_unit(), None)
        self.assertEqual(signal.get_value_name(), "1mm Absorbance")
        self.assertEqual(signal.get_value_unit(), None)
        signal.set_axis_name("Wavelength")
        signal.set_axis_unit("nm")
        signal.set_value_name("1 mm Absorbance")
        signal.set_value_unit(None)
        self.assertEqual(signal.get_axis_name(), "Wavelength")
        self.assertEqual(signal.get_axis_unit(), "nm")
        self.assertEqual(signal.get_value_name(), "1 mm Absorbance")
        self.assertEqual(signal.get_value_unit(), None)
        signal.preview(export_path="tests/out/UV_Vis_1_preview_with_NumericSignal1D")
        signal = abstract.ContinuousSignal1DBase.from_csv(
            "tests/data/chromatography_UV_1.csv"
        )
        self.assertEqual(signal.get_axis_name(), "ml")
        self.assertEqual(signal.get_axis_unit(), None)
        self.assertEqual(signal.get_value_name(), "mAU")
        self.assertEqual(signal.get_value_unit(), None)
        signal.set_axis_name("Volume")
        signal.set_axis_unit("ml")
        signal.set_value_name("280 nm")
        signal.set_value_unit("mAU")
        signal.preview(
            export_path="tests/out/chromatography_UV_1_preview_with_NumericSignal1D"
        )


class TestFractionSignal(unittest.TestCase):

    def test_preview(self):
        fraction_signal = abstract.FractionSignal.from_csv(
            "tests/data/fraction_1.csv", name=None, axis_unit="ml"
        )
        fraction_signal.set_axis_name("Volume")
        fraction_signal.preview(
            rotation=90,
            text_shift=(0, 0.05),
            export_path="tests/out/fraction_1_preview_with_FractionSignal.png",
        )

    def test_export(self):
        fraction_signal = abstract.FractionSignal.from_csv(
            "tests/data/fraction_1.csv", name=None, axis_unit="ml"
        )
        fraction_signal.set_axis_name("Volume")
        with self.assertRaises(Exception):
            fraction_signal.export(
                "tests/out/fraction_1_export_with_FractionSignal.csv"
            )
        fraction_signal.export(
            "tests/out/fraction_1_export_with_FractionSignal.csv", mode="replace"
        )


class TestContinuousSignal1DValueAndStdView(unittest.TestCase):
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
            self.assertAlmostEqual(signal.value[axis_i], signal[axis_i])
        self.assertAlmostEqual(signal.value[280.5], 0.6)

    def test_value_view_interpolates_between_points(self):
        signal = self.make_signal()
        self.assertAlmostEqual(signal.value[280.0], 0.5)
        self.assertAlmostEqual(signal.value[281.0], 0.7)
        self.assertAlmostEqual(signal.value[280.5], 0.6)
        self.assertAlmostEqual(signal.value[281.5], 0.8)

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
        self.assertEqual(len(signal.value), 3)
        np.testing.assert_allclose(list(signal.value), self.VALUES)
        np.testing.assert_allclose(np.asarray(signal.value), self.VALUES)
        np.testing.assert_allclose(signal.value.to_numpy(), self.VALUES)
        self.assertEqual(signal.value.dtype, np.float64)
        self.assertAlmostEqual(signal.value.mean(), 0.7)
        self.assertAlmostEqual(signal.value.std(), 0.2)
        self.assertAlmostEqual(min(signal.value), 0.5)
        self.assertAlmostEqual(max(signal.value), 0.9)

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
        self.assertAlmostEqual((signal + 1)[280.5], 1.6)
        self.assertAlmostEqual((signal * 2)[280.5], 1.2)
        self.assertAlmostEqual((signal / 2)[280.5], 0.3)
        self.assertAlmostEqual((-signal)[280.5], -0.6)
        self.assertAlmostEqual((signal - signal)[280.5], 0.0)

    def test_value_setter_still_works(self):
        signal = self.make_signal()
        signal.value = [1.0, 2.0, 3.0]
        np.testing.assert_allclose(signal.data.iloc[:, 1], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(signal.value[280.5], 1.5)

    # ---------------- std ----------------

    def test_std_view_returns_data_points(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.std[self.AXIS], self.STDS)

    def test_std_view_interpolates_between_bounds(self):
        """280.5 处的 std 由 280 与 281 的上下限插值得到"""
        signal = self.make_signal()
        # 280: 上下限 0.4 / 0.6; 281: 上下限 0.5 / 0.9
        # 280.5 插值后: 下限 0.45, 上限 0.75 → std = 0.15
        self.assertAlmostEqual(signal.std[280.5], 0.15)
        self.assertAlmostEqual(signal.std[281.5], 0.3)
        # 上下限对称时, 线性插值的结果与直接对 value_std 插值一致
        self.assertAlmostEqual(
            signal.std[280.5], np.interp(280.5, self.AXIS, self.STDS)
        )

    def test_std_view_accepts_axis_list(self):
        signal = self.make_signal()
        np.testing.assert_allclose(signal.std[[280.25, 281.75]], [0.125, 0.35])
        # slice 按 axis 范围解释
        np.testing.assert_allclose(signal.std[280:283], self.STDS)

    def test_std_view_is_array_like(self):
        signal = self.make_signal()
        self.assertEqual(len(signal.std), 3)
        np.testing.assert_allclose(signal.std.to_numpy(), self.STDS)
        np.testing.assert_allclose(signal.value - signal.value_std, [0.4, 0.5, 0.5])

    def test_std_view_uses_bounds_when_asymmetric(self):
        """上下限不对称时, std 由上下限插值给出 (而不是对 std 直接插值)"""
        from dvrazer.abstract.signal_1d import (
            _InterpolateBetweenBounds,
        )

        view = _InterpolateBetweenBounds([0.0, 1.0], lower=[0.0, 0.0], upper=[1.0, 3.0])
        self.assertAlmostEqual(view[0.5], (2.0 - 0.0) / 2)
        self.assertAlmostEqual(view[0.25], (1.5 - 0.0) / 2)

    def test_std_raises_without_std_column(self):
        signal = self.make_signal(with_std=False)
        self.assertIsNone(signal.value_std)
        with self.assertRaises(ValueError):
            signal.std

    # ---------------- 绘图 ----------------

    def test_plot_at_draws_std_band_with_value_view(self):
        import matplotlib.pyplot as plt

        signal = self.make_signal()
        signal.axis_annotation.limit = (280.0, 282.0)
        signal.value_annotation.limit = (0.4, 1.0)
        fig, ax = plt.subplots()
        try:
            handle = signal.plot_at(ax)
            self.assertIsNotNone(handle)
            self.assertEqual(len(ax.collections), 1)
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
