"""
Tests for SoftMax Pro kinetic multi-wavelength parsing.
"""
import sys
sys.path.append("..")

import unittest
from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
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
        # First timepoint value at 280 nm should be ~0.100
        self.assertAlmostEqual(
            float(signal.data.iloc[0]["Absorbance (AU)"]), 0.100, places=3
        )
