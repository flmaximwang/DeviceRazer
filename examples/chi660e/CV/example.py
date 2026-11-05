"""
CHI660E cyclic voltammetry (CV) example
=======================================

Reads a .txt file exported from a CH Instruments CHI660E electrochemical
workstation. A synthetic ferricyanide CV dataset (two full cycles) is generated
here.

Usage::

    python examples/chi660e/CV/example.py
"""

import os
import numpy as np

from dvrazer.instruments.CH_Instruments.chi660e import chi660eCV


def _generate_cv_data(output_path: str):
    """
    Generate synthetic CV data: ferricyanide CV over two cycles.
    Potential range: 0.5 V → -0.3 V → 0.5 V → -0.3 V → 0.5 V
    """
    # Scan parameters
    scan_rate = 0.1  # V/s
    total_time_per_segment = 8.0  # s (0.5 -> -0.3 is 0.8 V, at 0.1 V/s = 8 s)

    # Potential sequence: 0.5 → -0.3 → 0.5 → -0.3 → 0.5
    segments_potential = [
        np.linspace(0.5, -0.3, 200),   # 1st forward
        np.linspace(-0.3, 0.5, 200),   # 1st reverse
        np.linspace(0.5, -0.3, 200),   # 2nd forward
        np.linspace(-0.3, 0.5, 200),   # 2nd reverse
    ]

    all_potential = np.concatenate(segments_potential)

    # Generate synthetic current: reversible ferricyanide peak shape
    E0 = 0.1  # formal potential (V vs Ag/AgCl)
    # Anodic peak (oxidation) and cathodic peak (reduction)
    current = (
        -0.8e-4 * np.exp(-((all_potential - (E0 + 0.15)) ** 2) / (2 * 0.02**2))
        + 0.8e-4 * np.exp(-((all_potential - (E0 - 0.15)) ** 2) / (2 * 0.02**2))
        + 0.05e-4 * all_potential  # baseline capacitive current
        + 0.02e-4 * np.random.randn(len(all_potential))  # noise
    )

    # Write in CHI660E format
    lines = [
        "Synthetic Ferricyanide CV",
        "",
        "Potential/V, Current/A",
    ]
    for p, c in zip(all_potential, current):
        lines.append(f"{p:.6f}, {c:.8e}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_CV.txt")
    _generate_cv_data(txt_path)

    cv = chi660eCV.from_exported_files([txt_path], name="Ferricyanide CV")
    print(f"CV: {cv.name}")
    print(f"Scan segments: {len(cv.signal_names)}")

    cv.set_default_annotations()
    fig, ax = cv.plot(mode=0)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
