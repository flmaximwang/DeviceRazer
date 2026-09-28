"""
Thermo Fisher Multiskan FC 酶标仪数据示例
==========================================

使用 Multiskan FC 酶标仪导出的 .txt 文件。
此处生成一个合成 96 孔板吸光度数据 (BSA 蛋白定量标准曲线)。

使用方法::

    python examples/multiscan_fc/example.py
"""

import os
import numpy as np

from dvrazer.instruments.ThermoFisher.multiscan_fc import (
    MultiWellPlateFC,
)


def _generate_plate_data(output_path: str):
    """
    生成合成 Multiskan FC 数据

    格式:
    - 表头行: \\t1\\t2\\t3\\t4\\t5\\t6\\t7\\t8\\t9\\t10\\t11\\t12
    - 数据行: A-H 行标签, 随后是 12 列 tab 分隔的数值

    模拟 BSA 标准曲线: A1-A8 为标准品 (0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0 mg/mL)
    其余为未知样本 (随机吸光度)。
    """
    rows = ["A", "B", "C", "D", "E", "F", "G", "H"]

    # 标准品吸光度 (BSA, 562 nm)
    standard_conc = [0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]  # mg/mL
    standard_abs = [0.05, 0.12, 0.22, 0.40, 0.55, 0.70, 0.95, 1.20]  # OD

    lines = ["\t1\t2\t3\t4\t5\t6\t7\t8\t9\t10\t11\t12"]

    for row_idx, row_label in enumerate(rows):
        values = []
        for col in range(1, 13):
            if row_idx == 0 and col <= 8:
                # 标准品行 (A1-A8)
                val = standard_abs[col - 1] + np.random.normal(0, 0.01)
            elif row_idx == 0 and col <= 8:
                val = standard_abs[col - 1] + np.random.normal(0, 0.01)
            else:
                # 模拟未知样本 (随机吸光度 0.1-1.0)
                val = 0.1 + 0.9 * np.random.random()
            values.append(f"{val:.4f}")
        lines.append(f"{row_label}\t" + "\t".join(values))

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_plate.txt")
    _generate_plate_data(txt_path)

    plate = MultiWellPlateFC.from_exported_file(txt_path, name="BSA Standard Curve")
    print(f"板类型: {plate.name}")
    print(f"板尺寸: {plate.data.shape}")
    print(f"行索引: {list(plate.data.index)}")
    print(f"列索引: {list(plate.data.columns)}")
    print(f"A1 = {plate['A', 1]:.4f}")
    print(f"A8 = {plate['A', 8]:.4f}")
    print(f"H12 = {plate['H', 12]:.4f}")

    # 使用 calibration_and_measurement 绘制标准曲线
    fig, ax, result, result_table = plate.calibration_and_measurement(
        calibration_values=[0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
        calibration_markers=[("A", 1), ("A", 2), ("A", 3), ("A", 4),
                             ("A", 5), ("A", 6), ("A", 7), ("A", 8)],
        measurement_markers=[("B", 1), ("C", 3), ("D", 5)],
        xlabel="BSA Concentration (mg/mL)",
        ylabel="Absorbance at 562 nm",
    )
    print(f"斜率 = {result.slope:.4f}, 截距 = {result.intercept:.4f}, R² = {result.rvalue**2:.4f}")

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
