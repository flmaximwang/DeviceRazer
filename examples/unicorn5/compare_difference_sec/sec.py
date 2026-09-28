"""SEC chromatogram plotter.

Usage:
    python sec.py <path/to/unicorn7.txt>

Example:
    python sec.py "data/2026-07-06_Purification-001_gammaPFD-Elution.txt"
"""

from pathlib import Path

import sys
from dvrazer.instruments.Cytiva.unicorn5 import Unicorn5Chrom, Chrom
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
