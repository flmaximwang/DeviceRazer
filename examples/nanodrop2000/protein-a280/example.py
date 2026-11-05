"""
NanoDrop 2000 Protein A280 示例
================================

使用 NanoDrop 2000 导出的 .tsv 蛋白 A280 数据 (多个 spectrum 之间以空行分隔)。

``Nanodrop2000Workbook.from_tsv`` 只读取文件, 不会修改输入文件。

使用方法::

    python examples/nanodrop2000/protein-a280/example.py
"""

import os

from dvrazer.instruments import Nanodrop2000Workbook

if __name__ == "__main__":
    tsv_path = os.path.join(os.path.dirname(__file__), "example.tsv")

    protein_a280 = Nanodrop2000Workbook.from_tsv(tsv_path)
    protein_a280.set_default_annotations(mode="Protein A280")
    fig, ax = protein_a280.plot()
