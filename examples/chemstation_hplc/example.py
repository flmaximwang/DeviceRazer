"""
ChemStation HPLC data example
=============================

HPLC chromatographic data exported from Agilent ChemStation, containing UV
absorbance signals at multiple wavelengths (214, 280, 300, 400, 420 nm) plus a
Fraction signal.

Usage::

    python examples/chemstation_hplc/example.py
"""

import os

from dvrazer.instruments.Agilent.chemstation_processor import (
    ChemStChrom,
)

if __name__ == "__main__":
    # Data directory relative to this script
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    chrom = ChemStChrom.from_exported_directory(data_dir)

    # Inspect the available signal channels
    print("Available signals:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
