"""
Unicorn 7 (ÄKTA) 色谱数据示例 (.txt)
=====================================

使用 Cytiva Unicorn 7 软件导出的 .txt 色谱数据。

使用方法::

    python examples/unicorn7_txt/example.py
"""

import os

from dvrazer.instruments.GE_Heathcare.unicorn7 import (
    Unicorn7Chrom,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    chromatograms = Unicorn7Chrom.from_txt(txt_path)

    print(f"色谱图数量: {len(chromatograms)}")

    for chrom in chromatograms:
        print(f"  - {chrom.name}: {chrom.signal_names}")

    # 取第一个色谱图
    chrom = chromatograms[0]
    print(f"\n使用色谱: {chrom.name}")
    print("可用信号:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
