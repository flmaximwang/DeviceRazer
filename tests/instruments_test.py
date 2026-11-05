import sys
sys.path.append('..')

import tempfile
import unittest
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from dvrazer.instruments.Agilent.chemstation_processor import (
    ChemStChrom,
    ChemStSig,
)
from dvrazer.instruments.GE_Heathcare.unicorn7 import Unicorn7Project
from dvrazer.instruments.MolecularDevices.softmax_pro import SoftMaxPro_Project

TEST_DATA = Path("tests/data")
OUT_DIR = Path("tests/out")


def save_figure(fig, file_name):
    """Save *fig* under ``tests/out`` (the only allowed output directory) and
    close it so figures do not pile up across tests."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / file_name
    fig.savefig(path)
    plt.close(fig)
    return path


class TestChemStationChromatographyNumericSignal(unittest.TestCase):

    def test_read_and_export(self):
        signal = ChemStSig.from_raw_export(
            str(TEST_DATA / "chemstation_chromatography_1" / "280.CSV")
        )
        # The parser names the signal after the exported file and annotates
        # the two columns (time in min, absorbance in mAU).
        self.assertEqual(signal.name, "280")
        self.assertEqual(signal.axis_annotation.name, "Time")
        self.assertEqual(signal.axis_annotation.unit, "min")
        self.assertEqual(signal.value_annotation.name, "280")
        self.assertEqual(signal.value_annotation.unit, "mAU")
        self.assertGreater(len(signal.data), 0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            export_path = Path(tmp_dir) / "280.csv"
            signal.to_csv(export_path)
            self.assertTrue(export_path.exists())
            exported = pd.read_csv(export_path)
            # Comparing the whole frame also verifies the header labels and
            # the exact round-trip of every value.
            pd.testing.assert_frame_equal(exported, signal.data)


class TestChemStationChromatography(unittest.TestCase):

    def test_read_and_export(self):
        chrom = ChemStChrom.from_exported_directory(
            str(TEST_DATA / "chemstation_chromatography_1")
        )
        self.assertEqual(chrom.name, "chemstation_chromatography_1")
        for signal_name in ("280", "214", "300", "400", "420", "Fraction"):
            self.assertIn(signal_name, chrom.visible_signal_names)

        # The current collection API exports a whole chromatogram with
        # ``to_folder``; there is no ``export(mode=...)`` anymore.
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_dir = Path(tmp_dir) / "chemstation_chromatography_1_export"
            chrom.to_folder(export_dir)
            exported_files = sorted(path.name for path in export_dir.iterdir())
            self.assertEqual(
                exported_files, sorted(f"{name}.csv" for name in chrom.signal_names)
            )
            exported_280 = pd.read_csv(export_dir / "280.csv")
            pd.testing.assert_frame_equal(exported_280, chrom["280"].data)

    def test_plot(self):
        chrom = ChemStChrom.from_exported_directory(
            str(TEST_DATA / "chemstation_chromatography_1")
        )
        chrom.plot_args.ax_size = (15, 5)
        chrom.set_default_annotations()
        chrom.align_axes(0, 30)
        chrom.visible_signal_names = ["280", "214"]
        chrom.plot_args.mode = 0
        fig, ax = chrom.plot()
        self.assertEqual(list(chrom.axis_annotation.limit), [0, 30])
        self.assertEqual(
            [text.get_text() for text in ax.get_legend().get_texts()],
            ["280", "214"],
        )
        self.assertTrue(
            save_figure(fig, "chemstation_chromatography_1_plot.png").exists()
        )

        # Mode 1 shares the x axis and gives every visible continuous signal
        # its own y axis.
        chrom.plot_args.mode = 1
        chrom.plot_args.margin = None  # re-measure the margins for this layout
        fig, axes = chrom.plot()
        self.assertEqual(len(axes), 2)
        self.assertTrue(
            save_figure(
                fig, "chemstation_chromatography_1_plot_mode_1.png"
            ).exists()
        )


class TestUnicornChrom(unittest.TestCase):

    def test_read_and_export(self):
        chroms = Unicorn7Project.read_txt(
            str(TEST_DATA / "unicorn_chrom_1.txt")
        )
        self.assertIsInstance(chroms, list)
        self.assertGreaterEqual(len(chroms), 1)
        chrom = chroms[0]
        self.assertTrue(chrom.name.startswith("unicorn_chrom_1"))
        for signal_name in ("UV", "Cond", "Conc B"):
            self.assertIn(signal_name, chrom.visible_signal_names)

        # Default plot: ChromPlotArgs defaults to mode 1 (shared x axis,
        # per-signal y axes), so the annotations must be set first.
        chrom.plot_args.ax_size = (25, 5)
        chrom.set_default_annotations()
        fig, axes = chrom.plot(fontsize=5)
        self.assertGreaterEqual(len(axes), 2)
        self.assertTrue(
            save_figure(
                fig, "unicorn_chrom_1_preview_with_UnicornChrom.png"
            ).exists()
        )

        # Mode 1 with an explicit axis limit and a peak annotation.
        chrom.set_default_annotations()
        chrom.align_axes(0, 30)
        chrom.plot_args.mode = 1
        chrom.plot_args.margin = None  # re-measure the margins for this layout
        fig, axes = chrom.plot(fontsize=10, axis_shift=0.04)
        self.assertEqual(list(chrom["UV"].axis_annotation.limit), [0, 30])
        uv_signal = chrom["UV"]
        uv_signal.plot_peak_at(axes[0], 10, 15)
        self.assertTrue(
            save_figure(
                fig, "unicorn_chrom_1_preview_with_UnicornChrom_all_values.png"
            ).exists()
        )


class TestSoftMaxProKineticMultiWavelength(unittest.TestCase):

    def test_parse_multi_wavelength_kinetic(self):
        """Multi-wavelength kinetic reads have separator columns between
        wavelength blocks. These must be dropped correctly."""
        project = SoftMaxPro_Project.read_txt(
            "tests/data/softmax_kinetic_multi_wavelength.txt"
        )
        plate = project.blocks[0]
        # Should have 1 Temperature + 12 cols * 2 wl = 25 signals
        self.assertGreater(len(plate.signals), 20)
        # A1_280 should exist with 2 timepoints
        a1_280 = [s for s in plate.signals if s.name == "A1_280"]
        self.assertEqual(len(a1_280), 1)
        signal = a1_280[0]
        self.assertEqual(len(signal.data), 2)
        # The value column is labelled from the read mode ("Absorbance (AU)"),
        # so address it by position instead of a hard-coded label.
        self.assertEqual(signal.value_annotation.name, "Absorbance")
        self.assertEqual(signal.value_annotation.unit, "AU")
        # First timepoint value at 280nm should be ~0.100
        self.assertAlmostEqual(
            float(signal.data.iloc[0, 1]), 0.100, places=3
        )


if __name__ == '__main__':
    unittest.main()
