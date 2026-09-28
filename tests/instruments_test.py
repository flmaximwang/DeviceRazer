import sys
sys.path.append('..')

import unittest
import os
import pandas as pd
import matplotlib.pyplot as plt
from dvrazer import instruments

class TestChemStationChromatographyNumericSignal(unittest.TestCase):
    
    def test_read_and_export(self):
        chemstation_chromatography_numeric_signal = instruments.ChemStationChromatographyNumericSignal.from_raw_export(
            'tests/data/chemstation_chromatography_1/280.CSV'
        )
        chemstation_chromatography_numeric_signal.set_value_name("280 nm")
        with self.assertRaises(Exception):
            chemstation_chromatography_numeric_signal.export("tests/out/chromatography_UV_1_export_with_ChemStationChromatographyNumericSignal.csv")
        chemstation_chromatography_numeric_signal.export("tests/out/chromatography_UV_1_export_with_ChemStationChromatographyNumericSignal.csv", mode="replace")

class TestChemStationChromatography(unittest.TestCase):
    
    def test_read_and_export(self):
        chemstation_chromatography = instruments.ChemStationChromatography.from_raw_directory(
            'tests/data/chemstation_chromatography_1'
        )
        with self.assertRaises(Exception):
            chemstation_chromatography.export("tests/out/chemstation_chromatography_1")
        chemstation_chromatography.export("tests/out/chemstation_chromatography_1", mode="replace")

    def test_plot(self):
        chemstation_chromatography = instruments.ChemStationChromatography.from_raw_directory(
            'tests/data/chemstation_chromatography_1'
        )
        chemstation_chromatography.set_figsize((15, 5))
        chemstation_chromatography.align_signal_axes((0, 30))
        chemstation_chromatography.set_main_signal("280")
        chemstation_chromatography.set_visible_signals("280", "214")
        chemstation_chromatography.set_display_mode(0)
        chemstation_chromatography.plot()

class TestUnicornChrom(unittest.TestCase):
    
    def test_read_and_export(self):
        unicorn_chroms = instruments.read_uni_chroms_from_raw_export('tests/data/unicorn_chrom_1.txt')
        unicorn_chrom = unicorn_chroms[0]
        unicorn_chrom.set_figsize((25, 5))
        fig, axes = unicorn_chrom.plot(fontsize=5)
        fig.savefig("/Users/maxim/Documents/VSCode/instrumental-data-processer/tests/out/unicorn_chrom_1_preview_with_UnicornChrom.png")
        unicorn_chrom.set_display_mode(1)
        unicorn_chrom.align_signal_axes((0, 30))
        fig, axes = unicorn_chrom.plot(fontsize=10, axis_shift=0.04)
        a: instruments.UnicornContinuousSignal1D = unicorn_chrom["UV"]
        a.plot_peak_at(axes[0], 10, 15)
        fig.savefig("/Users/maxim/Documents/VSCode/instrumental-data-processer/tests/out/unicorn_chrom_1_preview_with_UnicornChrom_all_values.png")

class TestSoftMaxProKineticMultiWavelength(unittest.TestCase):

    def test_parse_multi_wavelength_kinetic(self):
        """Multi-wavelength kinetic reads have separator columns between
        wavelength blocks. These must be dropped correctly."""
        from dvrazer.instruments.MolecularDevices.softmax_pro import (
            SoftMaxPro_Project,
        )
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
        # First timepoint value at 280nm should be ~0.100
        self.assertAlmostEqual(
            float(signal.data.iloc[0]["Absorbance"]), 0.100, places=3
        )


if __name__ == '__main__':
    unittest.main()
    