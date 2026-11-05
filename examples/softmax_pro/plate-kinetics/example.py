"""
SoftMax Pro kinetic analysis example
====================================

Uses kinetic data exported by Molecular Devices SoftMax Pro (.txt format) to
demonstrate processing and analysis of UV-Vis absorption kinetic curves.

Data description:
- Sample: 32 μM protein + 50 μM Hemin in 20 mM Tris buffer
- Detection wavelengths: 398, 408, 418 nm (Soret band) and 530, 563, 740 nm (visible region)
- Temperature: constant 24.2°C

Usage::

    python examples/softmax_pro/plate-kinetics/example.py
"""

import os

import matplotlib.pyplot as plt

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    project = SoftMaxPro_Project.read_txt(txt_path)
    plate = project["Plate1"]

    # Remove the temperature signal (does not affect plotting)
    plate.remove_signal("Temperature")

    # Merge duplicate signals by wavelength number in the signal name (take the mean)
    plate = plate.average_similar_signals(lambda x: x.split("_")[1])

    # Convert the time axis from seconds to minutes
    for signal in plate.signals:
        signal.axis /= 60

    plate.axis_annotation.unit = "min"
    plate.set_default_annotations()
    plate.axis_annotation.ticklabel_space_major = 60

    # ===== Soret band (398, 408, 418 nm) =====
    plate.visible_signal_names = ["398", "408", "418"]
    plate.align_values(plate.visible_signal_names, 1.1, 1.61)
    plate.value_annotation.ticklabel_space_major = 0.1
    fig, ax = plate.plot()
    fig.tight_layout()
    soret_path = os.path.join(os.path.dirname(__file__), "example_soret.png")
    fig.savefig(soret_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {soret_path}")
    plt.close(fig)

    # ===== Visible region (530, 563, 740 nm) =====
    plate.visible_signal_names = ["530", "563", "740"]
    plate.align_values(plate.visible_signal_names, 0.1, 0.35)
    plate.value_annotation.ticklabel_space_major = 0.05
    fig, ax = plate.plot()
    fig.tight_layout()
    ir_path = os.path.join(os.path.dirname(__file__), "example_visible.png")
    fig.savefig(ir_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {ir_path}")
    plt.close(fig)
