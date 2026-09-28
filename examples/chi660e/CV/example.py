"""
CHI660E 循环伏安法 (CV) 示例
=============================

使用 CH Instruments CHI660E 电化学工作站导出的 .txt 文件。
此处生成一个合成铁氰化物 CV 数据（两个完整循环）。

使用方法::

    python examples/chi660e_cv/example.py
"""

import os
import numpy as np

from dvrazer.instruments.CHI.chi660e import chi660eCV


def _generate_cv_data(output_path: str):
    """
    生成合成 CV 数据: 两个循环的铁氰化物 CV
    电位范围: 0.5 V → -0.3 V → 0.5 V → -0.3 V → 0.5 V
    """
    # 扫描参数
    scan_rate = 0.1  # V/s
    total_time_per_segment = 8.0  # s (0.5 -> -0.3 is 0.8 V, at 0.1 V/s = 8 s)

    # 电位序列: 0.5 → -0.3 → 0.5 → -0.3 → 0.5
    segments_potential = [
        np.linspace(0.5, -0.3, 200),   # 1st forward
        np.linspace(-0.3, 0.5, 200),   # 1st reverse
        np.linspace(0.5, -0.3, 200),   # 2nd forward
        np.linspace(-0.3, 0.5, 200),   # 2nd reverse
    ]

    all_potential = np.concatenate(segments_potential)

    # 生成合成电流: 铁氰化物可逆峰形状
    E0 = 0.1  # 形式电位 (V vs Ag/AgCl)
    # 阳极峰 (氧化) 和 阴极峰 (还原)
    current = (
        -0.8e-4 * np.exp(-((all_potential - (E0 + 0.15)) ** 2) / (2 * 0.02**2))
        + 0.8e-4 * np.exp(-((all_potential - (E0 - 0.15)) ** 2) / (2 * 0.02**2))
        + 0.05e-4 * all_potential  # 基线电容电流
        + 0.02e-4 * np.random.randn(len(all_potential))  # 噪声
    )

    # 写入 CHI660E 格式
    lines = [
        "Synthetic Ferricyanide CV",
        "",
        "Potential/V, Current/A",
    ]
    for p, c in zip(all_potential, current):
        lines.append(f"{p:.6f}, {c:.8e}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_CV.txt")
    _generate_cv_data(txt_path)

    cv = chi660eCV.from_exported_files([txt_path], name="Ferricyanide CV")
    print(f"CV: {cv.name}")
    print(f"扫描段数: {len(cv.signal_names)}")

    cv.set_default_annotations()
    fig, ax = cv.plot(mode=0)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
