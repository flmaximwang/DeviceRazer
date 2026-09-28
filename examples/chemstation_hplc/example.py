"""
ChemStation HPLC 数据示例
==========================

从 Agilent ChemStation 导出的 HPLC 色谱数据，包含多个波长 (214, 280, 300,
400, 420 nm) 的 UV 吸光度信号以及 Fraction 信号。

使用方法::

    python examples/chemstation_hplc/example.py
"""

import os

from dvrazer.instruments.Agilent.chemstation_processor import (
    ChemStChrom,
)

if __name__ == "__main__":
    # 数据目录相对此脚本
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    chrom = ChemStChrom.from_exported_directory(data_dir)

    # 查看可用的信号通道
    print("可用信号:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
