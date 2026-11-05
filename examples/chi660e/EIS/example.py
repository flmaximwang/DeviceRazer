"""
CHI660E electrochemical impedance spectroscopy (EIS) example
============================================================

Reads a .txt file exported from a CH Instruments CHI660E electrochemical
workstation. A synthetic Randles circuit EIS dataset is generated here.

Usage::

    python examples/chi660e/EIS/example.py
"""

import os
import numpy as np

from dvrazer.instruments.CH_Instruments.chi660e import chi660eEIS


def _generate_eis_data(output_path: str):
    """
    Generate synthetic EIS data: Randles circuit model.

    EIS format (CHI660E):
    - First few lines: arbitrary header
    - The line containing "Freq/Hz": header row
    - Following lines: data (comma separated)
    """
    # Randles circuit parameters
    Rs = 50  # solution resistance (ohm)
    Rct = 500  # charge transfer resistance (ohm)
    Cdl = 20e-6  # double-layer capacitance (F)

    # Frequency range: 100 kHz → 0.1 Hz, logarithmically spaced
    frequencies = np.logspace(5, -1, 50)

    # Randles circuit impedance calculation
    omega = 2 * np.pi * frequencies
    # Z_Cdl = 1 / (j * omega * Cdl)
    # Z_total = Rs + (Rct * Z_Cdl) / (Rct + Z_Cdl)
    Z_Cdl_real = 0
    Z_Cdl_imag = -1 / (omega * Cdl)

    # Rct || Cdl
    denominator = Rct**2 + Z_Cdl_imag**2
    Z_parallel_real = (Rct * Z_Cdl_real * Rct + Rct * Z_Cdl_imag * Z_Cdl_imag) / denominator
    Z_parallel_imag = (Rct * Z_Cdl_real * Z_Cdl_imag - Rct * Z_Cdl_imag * Z_Cdl_real) / denominator

    # Actually let me simplify - Rct in parallel with Cdl
    Rct_inv = 1 / Rct
    Cdl_term = 1j * omega * Cdl
    Z_parallel = 1 / (Rct_inv + Cdl_term)
    Z_total = Rs + Z_parallel

    Z_real = np.real(Z_total)
    Z_imag = -np.imag(Z_total)  # -Z" for Nyquist plot (upper quadrant)
    Z_mag = np.sqrt(Z_real**2 + Z_imag**2)
    phase = -np.arctan2(Z_imag, Z_real) * 180 / np.pi

    # Write in CHI660E EIS format
    lines = [
        "Synthetic Randles Cell EIS",
        "",
        "Freq/Hz, Z'/ohm, Z\"/ohm, Z/ohm, Phase/deg",
    ]

    for f, zr, zi, zm, ph in zip(frequencies, Z_real, Z_imag, Z_mag, phase):
        lines.append(f"{f:.6e}, {zr:.6e}, {zi:.6e}, {zm:.6e}, {ph:.6e}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_EIS.txt")
    _generate_eis_data(txt_path)

    eis = chi660eEIS.from_exported_files([txt_path], name="Randles EIS")
    print(f"EIS: {eis.name}")
    print(f"Number of signals: {len(eis.signal_names)}")
    for sig_name in eis.signal_names:
        sig = eis[sig_name]
        print(f"  {sig_name}: {len(sig.data)} frequency points")

    # Plot the Nyquist diagram
    fig, ax = eis.plot_nyquist()

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
