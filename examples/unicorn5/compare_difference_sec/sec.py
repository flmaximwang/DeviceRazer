"""SEC chromatogram comparison plotter (Unicorn 5 .asc exports).

Reads two .asc runs from a local ``data/`` directory (``SECNoSalt.asc`` and
``SECSalt.asc``), merges their UV signals into one chromatogram and saves a
comparison PNG next to the data.

Usage:
    cd examples/unicorn5/compare_difference_sec
    python sec.py
"""

from pathlib import Path

import sys
from dvrazer import Chrom
from dvrazer.instruments import Unicorn5Chrom
import matplotlib.pyplot as plt


def add_suffix(chrom: Chrom, suffix: str):
    for signal_name in chrom.signal_names:
        chrom.rename_signal(signal_name, signal_name + suffix)


my_chrom_0 = Unicorn5Chrom.from_asc("data/SECNoSalt.asc")
add_suffix(my_chrom_0, " NoSalt")
my_chrom_1 = Unicorn5Chrom.from_asc("data/SECSalt.asc")
add_suffix(my_chrom_1, " WithSalt")
chrom_merged = Chrom.merge([my_chrom_0, my_chrom_1], signal_renaming=False)
chrom_merged.set_default_annotations()
chrom_merged.plot_args.mode = 0
chrom_merged.visible_signal_names = [
    "UV NoSalt",
    "UV WithSalt",
]
print(chrom_merged.signal_names)
chrom_merged.align_axes(0, 35)
chrom_merged.axis_annotation.ticklabel_space_major = 5
chrom_merged.align_values(["UV NoSalt", "UV WithSalt"], -10, 300)
chrom_merged.value_annotation.ticklabel_space_major = 50
chrom_merged.value_annotation.ticklabel_space_minor = 10
chrom_merged.value_annotation.ticklabel_floor = 0
fig, ax = chrom_merged.plot()
ax.legend(loc="upper right")
fig.savefig("data/SEC_Comparison_202607201122629.png", dpi=300, bbox_inches="tight")
