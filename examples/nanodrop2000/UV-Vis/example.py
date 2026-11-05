"""
NanoDrop 2000 UV-Vis full-spectrum example
==========================================

Reads .tsv full-spectrum data exported from a NanoDrop 2000 (multiple spectra
separated by blank lines).
Put the exported file in this directory and name it ``example.tsv``.

``Nanodrop2000Workbook.from_tsv`` only reads the file; it does not modify the
input file.

Usage::

    python examples/nanodrop2000/UV-Vis/example.py
"""

import os

from dvrazer.instruments import Nanodrop2000Workbook


def main():
    tsv_path = os.path.join(os.path.dirname(__file__), "example.tsv")

    uv_vis = Nanodrop2000Workbook.from_tsv(tsv_path)
    uv_vis = uv_vis.average_similar_signals()
    uv_vis.set_default_annotations(mode="UV-Vis")
    uv_vis.align_values(uv_vis.signal_names, 0, 1)
    uv_vis.value_annotation.ticklabel_space = (0.2, 0.04)
    fig, ax = uv_vis.plot()
    uv_vis[uv_vis.signal_names[0]].plot_peak_at(ax, 400, 420)


if __name__ == "__main__":
    main()
