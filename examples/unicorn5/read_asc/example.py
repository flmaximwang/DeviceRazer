"""
Unicorn 5 (ÄKTA) 色谱数据示例 (.asc)
=====================================

使用 GE Healthcare / Cytiva Unicorn 5 软件导出的 .asc 色谱数据。
此处生成一个合成色谱示例，包含 UV (吸光度)、Cond (电导率)、pH 和 Conc B (浓度) 信号。

使用方法::

    python examples/unicorn5/read_asc/example.py
"""

import os
import numpy as np

from dvrazer.instruments import Unicorn5Chrom


def _generate_synthetic_asc(output_path: str):
    """生成一个合成的 Unicorn 5 .asc 色谱数据文件。"""
    import pandas as pd

    # 模拟纯化图谱: 0-30 mL, 包含 UV, Cond, pH, Conc B 四个信号
    volume = np.linspace(0, 30, 600)

    # UV: 梯度洗脱, 在 ~15 mL 处有一个峰
    uv = 50 + 200 * np.exp(-((volume - 15) ** 2) / 2) + 10 * np.random.randn(len(volume))
    # Cond: 从 2 上升到 40 mS/cm (线性梯度)
    cond = 2 + (volume / 30) * 38
    # pH: 从 7.0 缓慢下降到 6.0
    ph = 7.0 - (volume / 30) * 1.0 + 0.05 * np.random.randn(len(volume))
    # Conc B: 从 0% 到 100% 线性梯度
    conc_b = (volume / 30) * 100

    # 构造 .asc 格式 (ISO-8859-15, tab-sep)
    # Row 1 (skip): anything
    # Row 2: signal names (grouped by prefix before _)
    # Row 3: units (axis/value pairs)
    # Row 4+: data
    lines = ["# Unicorn 5 Synthetic Chromatogram\n"]
    # Signal names: Run_001_UV, Run_001_Cond, Run_001_pH, Run_001_Conc
    lines.append("Run_001_UV\tRun_001_Cond\tRun_001_pH\tRun_001_Conc\n")
    lines.append("mL\tmAU\tmL\tmS/cm\tmL\tpH\tmL\t%\n")

    for i in range(len(volume)):
        lines.append(
            f"{volume[i]:.3f}\t{uv[i]:.2f}\t"
            f"{volume[i]:.3f}\t{cond[i]:.2f}\t"
            f"{volume[i]:.3f}\t{ph[i]:.2f}\t"
            f"{volume[i]:.3f}\t{conc_b[i]:.2f}\n"
        )

    with open(output_path, "w", encoding="iso-8859-15") as f:
        f.writelines(lines)

    return output_path


if __name__ == "__main__":
    asc_path = os.path.join(os.path.dirname(__file__), "example.asc")
    _generate_synthetic_asc(asc_path)

    # from_asc 返回单个 Unicorn5Chrom 对象（只有一个色谱组时）
    chrom = Unicorn5Chrom.from_asc(asc_path)
    print(f"色谱: {chrom.name}")
    print("可用信号:", chrom.signal_names)

    chrom.set_default_annotations()
    fig, ax = chrom.plot(mode=1)

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
