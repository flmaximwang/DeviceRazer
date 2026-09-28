import sys
sys.path.append("..")

import matplotlib
matplotlib.use("Agg")

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
)


def test_parse_multi_wavelength_kinetic():
    """分隔列在多波长动力学数据中位于波长块之间，不能误删数据列。"""
    project = SoftMaxPro_Project.read_txt(
        "tests/data/softmax_kinetic_multi_wavelength.txt"
    )
    plate = project["TestPlate"]
    assert "A1_280" in plate
    signal = plate["A1_280"]
    assert len(signal.data) == 2
    assert float(signal.data.iloc[0]["Absorbance"]) == 0.100
