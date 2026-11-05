"""
SoftMax Pro 动力学分析示例
=========================

使用 Molecular Devices SoftMax Pro 软件导出的动力学数据（.txt 格式），
演示紫外-可见吸收动力学曲线的处理与分析。

数据说明：
- 样品：32 μM 蛋白 + 50 μM Hemin，20 mM Tris 缓冲液
- 检测波长：398, 408, 418 nm（Soret 带）和 530, 563, 740 nm（可见光区）
- 温度：24.2°C 恒温

使用方法::

    python examples/softmax_pro/plate-kinetics/example.py
"""

import os

import matplotlib.pyplot as plt

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
)

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example.txt")

    project = SoftMaxPro_Project.read_txt(txt_path)
    plate = project["Plate1"]

    # 移除温度信号（不影响绘图）
    plate.remove_signal("Temperature")

    # 按信号名称中的波长编号合并重复信号（取均值）
    plate = plate.average_similar_signals(lambda x: x.split("_")[1])

    # 将时间轴从秒转换为分钟
    for signal in plate.signals:
        signal.axis /= 60

    plate.axis_annotation.unit = "min"
    plate.set_default_annotations()
    plate.axis_annotation.ticklabel_space_major = 60

    # ===== Soret 带（398, 408, 418 nm）=====
    plate.visible_signal_names = ["398", "408", "418"]
    plate.align_values(plate.visible_signal_names, 1.1, 1.61)
    plate.value_annotation.ticklabel_space_major = 0.1
    fig, ax = plate.plot()
    fig.tight_layout()
    soret_path = os.path.join(os.path.dirname(__file__), "example_soret.png")
    fig.savefig(soret_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {soret_path}")
    plt.close(fig)

    # ===== 可见光区（530, 563, 740 nm）=====
    plate.visible_signal_names = ["530", "563", "740"]
    plate.align_values(plate.visible_signal_names, 0.1, 0.35)
    plate.value_annotation.ticklabel_space_major = 0.05
    fig, ax = plate.plot()
    fig.tight_layout()
    ir_path = os.path.join(os.path.dirname(__file__), "example_visible.png")
    fig.savefig(ir_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {ir_path}")
    plt.close(fig)
