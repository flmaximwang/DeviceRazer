"""
SoftMax Pro spectral absorption example
=======================================

Uses spectral absorption data exported by Molecular Devices SoftMax Pro (.txt
format).

Usage::

    python examples/softmax_pro/plate-spectrum/example.py
"""

import os

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    project = SoftMaxPro_Project.read_txt(txt_path)

    # Get the first plate (spectral absorption mode)
    plate = project["909_absorb"]
    print(f"Plate type: {type(plate).__name__}")
    print(f"Number of signals: {len(plate.signal_names)}")

    plate.set_default_annotations()
    fig, ax = plate.plot(mode=0)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
