"""
Unicorn 7 (ÄKTA) chromatography data example (.txt)
===================================================

Reads .txt chromatography data exported by Cytiva Unicorn 7 software
(UTF-16 LE, tab separated).
Put the exported file in this directory and name it ``example.txt``.

Usage::

    python examples/unicorn7/unicorn7_txt/example.py
"""

import os

from dvrazer.instruments.GE_Heathcare.unicorn7 import (
    Unicorn7Chrom,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    chromatograms = Unicorn7Chrom.from_txt(txt_path)

    print(f"Number of chromatograms: {len(chromatograms)}")

    for chrom in chromatograms:
        print(f"  - {chrom.name}: {chrom.signal_names}")

    # Take the first chromatogram
    chrom = chromatograms[0]
    print(f"\nUsing chromatogram: {chrom.name}")
    print("Available signals:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
