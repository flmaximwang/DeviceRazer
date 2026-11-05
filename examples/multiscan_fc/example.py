"""
Thermo Fisher Multiskan FC microplate reader data example
=========================================================

Reads a .txt file exported from a Multiskan FC microplate reader. A synthetic
96-well plate absorbance dataset (BSA protein quantification standard curve) is
generated here.

Usage::

    python examples/multiscan_fc/example.py
"""

import os
import numpy as np

from dvrazer.instruments.ThermoFisher.multiscan_fc import (
    MultiWellPlateFC,
)


def _generate_plate_data(output_path: str):
    """
    Generate synthetic Multiskan FC data.

    Format:
    - Header line: \\t1\\t2\\t3\\t4\\t5\\t6\\t7\\t8\\t9\\t10\\t11\\t12
    - Data lines: row label A-H followed by 12 tab-separated values

    Simulates a BSA standard curve: A1-A8 are standards (0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0 mg/mL)
    The rest are unknown samples (random absorbance).
    """
    rows = ["A", "B", "C", "D", "E", "F", "G", "H"]

    # Standard absorbance (BSA, 562 nm)
    standard_conc = [0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]  # mg/mL
    standard_abs = [0.05, 0.12, 0.22, 0.40, 0.55, 0.70, 0.95, 1.20]  # OD

    lines = ["\t1\t2\t3\t4\t5\t6\t7\t8\t9\t10\t11\t12"]

    for row_idx, row_label in enumerate(rows):
        values = []
        for col in range(1, 13):
            if row_idx == 0 and col <= 8:
                # Standard row (A1-A8)
                val = standard_abs[col - 1] + np.random.normal(0, 0.01)
            elif row_idx == 0 and col <= 8:
                val = standard_abs[col - 1] + np.random.normal(0, 0.01)
            else:
                # Simulate unknown samples (random absorbance 0.1-1.0)
                val = 0.1 + 0.9 * np.random.random()
            values.append(f"{val:.4f}")
        lines.append(f"{row_label}\t" + "\t".join(values))

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_plate.txt")
    _generate_plate_data(txt_path)

    plate = MultiWellPlateFC.from_exported_file(txt_path, name="BSA Standard Curve")
    print(f"Plate type: {plate.name}")
    print(f"Plate size: {plate.data.shape}")
    print(f"Row index: {list(plate.data.index)}")
    print(f"Column index: {list(plate.data.columns)}")
    print(f"A1 = {plate['A', 1]:.4f}")
    print(f"A8 = {plate['A', 8]:.4f}")
    print(f"H12 = {plate['H', 12]:.4f}")

    # Plot the standard curve with calibration_and_measurement
    fig, ax, result, result_table = plate.calibration_and_measurement(
        calibration_values=[0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
        calibration_markers=[("A", 1), ("A", 2), ("A", 3), ("A", 4),
                             ("A", 5), ("A", 6), ("A", 7), ("A", 8)],
        measurement_markers=[("B", 1), ("C", 3), ("D", 5)],
        xlabel="BSA Concentration (mg/mL)",
        ylabel="Absorbance at 562 nm",
    )
    print(f"slope = {result.slope:.4f}, intercept = {result.intercept:.4f}, R² = {result.rvalue**2:.4f}")

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
