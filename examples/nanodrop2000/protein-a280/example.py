"""
NanoDrop 2000 Protein A280 example
==================================

Reads .tsv protein A280 data exported from a NanoDrop 2000 (multiple spectra
separated by blank lines).

``Nanodrop2000Workbook.from_tsv`` only reads the file; it does not modify the
input file.

Usage::

    python examples/nanodrop2000/protein-a280/example.py
"""

import os

from dvrazer.instruments import Nanodrop2000Workbook

if __name__ == "__main__":
    tsv_path = os.path.join(os.path.dirname(__file__), "example.tsv")

    protein_a280 = Nanodrop2000Workbook.from_tsv(tsv_path)
    protein_a280.set_default_annotations(mode="Protein A280")
    fig, ax = protein_a280.plot()
