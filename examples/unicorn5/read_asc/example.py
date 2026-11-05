"""
Unicorn 5 (ÄKTA) chromatography data example (.asc)
===================================================

Reads .asc chromatography data exported by GE Healthcare / Cytiva Unicorn 5
software. A synthetic chromatogram is generated here, containing UV
(absorbance), Cond (conductivity), pH and Conc B (concentration) signals.

Usage::

    python examples/unicorn5/read_asc/example.py
"""

import os
import numpy as np

from dvrazer.instruments import Unicorn5Chrom


def _generate_synthetic_asc(output_path: str):
    """Generate a synthetic Unicorn 5 .asc chromatography data file."""
    import pandas as pd

    # Simulate a purification trace: 0-30 mL with four signals: UV, Cond, pH, Conc B
    volume = np.linspace(0, 30, 600)

    # UV: gradient elution with a peak at ~15 mL
    uv = 50 + 200 * np.exp(-((volume - 15) ** 2) / 2) + 10 * np.random.randn(len(volume))
    # Cond: rises from 2 to 40 mS/cm (linear gradient)
    cond = 2 + (volume / 30) * 38
    # pH: slowly decreases from 7.0 to 6.0
    ph = 7.0 - (volume / 30) * 1.0 + 0.05 * np.random.randn(len(volume))
    # Conc B: linear gradient from 0% to 100%
    conc_b = (volume / 30) * 100

    # Build the .asc format (ISO-8859-15, tab-sep)
    # Row 1 (skip): anything
    # Row 2: signal names (grouped by prefix before _)
    # Row 3: units (axis/value pairs)
    # Row 4+: data
    lines = ["# Unicorn 5 Synthetic Chromatogram\n"]
    # Signal names: Run_001_UV, Run_001_Cond, Run_001_pH, Run_001_Conc
    lines.append("Run_001_UV\tRun_001_Cond\tRun_001_pH\tRun_001_Conc\n")
    lines.append("mL\tmAU\tmL\tmS/cm\tmL\tpH\tmL\t%\n")

    for i in range(len(volume)):
        lines.append(
            f"{volume[i]:.3f}\t{uv[i]:.2f}\t"
            f"{volume[i]:.3f}\t{cond[i]:.2f}\t"
            f"{volume[i]:.3f}\t{ph[i]:.2f}\t"
            f"{volume[i]:.3f}\t{conc_b[i]:.2f}\n"
        )

    with open(output_path, "w", encoding="iso-8859-15") as f:
        f.writelines(lines)

    return output_path


if __name__ == "__main__":
    asc_path = os.path.join(os.path.dirname(__file__), "example.asc")
    _generate_synthetic_asc(asc_path)

    # from_asc returns a single Unicorn5Chrom object
    # (when there is only one chromatography group)
    chrom = Unicorn5Chrom.from_asc(asc_path)
    print(f"Chromatogram: {chrom.name}")
    print("Available signals:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
