"""
SoftMax Pro 光谱吸收示例
========================

使用 Molecular Devices SoftMax Pro 软件导出的光谱吸收数据（.txt 格式）。

使用方法::

    python examples/softmax_pro/plate-spectrum/example.py
"""

import os

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    project = SoftMaxPro_Project.read_txt(txt_path)

    # 获取第一个板（光谱吸收模式）
    plate = project["909_absorb"]
    print(f"板类型: {type(plate).__name__}")
    print(f"信号数量: {len(plate.signal_names)}")

    plate.set_default_annotations()
    fig, ax = plate.plot(mode=0)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
