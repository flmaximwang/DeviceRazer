"""
CHI660E 电化学阻抗谱 (EIS) 示例
=================================

使用 CH Instruments CHI660E 电化学工作站导出的 .txt 文件。
此处生成一个合成 Randles 电路 EIS 数据。

使用方法::

    python examples/chi660e_eis/example.py
"""

import os
import numpy as np

from dvrazer.instruments.CHI.chi660e import chi660eEIS


def _generate_eis_data(output_path: str):
    """
    生成合成 EIS 数据: Randles 电路模型

    EIS 格式 (CHI660E):
    - 前几行: 任意表头
    - 包含 "Freq/Hz" 的行: 表头行
    - 后续行: 数据 (逗号分隔)
    """
    # Randles 电路参数
    Rs = 50  # 溶液电阻 (ohm)
    Rct = 500  # 电荷转移电阻 (ohm)
    Cdl = 20e-6  # 双电层电容 (F)

    # 频率范围: 100 kHz → 0.1 Hz, 对数分布
    frequencies = np.logspace(5, -1, 50)

    # Randles 电路阻抗计算
    omega = 2 * np.pi * frequencies
    # Z_Cdl = 1 / (j * omega * Cdl)
    # Z_total = Rs + (Rct * Z_Cdl) / (Rct + Z_Cdl)
    Z_Cdl_real = 0
    Z_Cdl_imag = -1 / (omega * Cdl)

    # Rct || Cdl
    denominator = Rct**2 + Z_Cdl_imag**2
    Z_parallel_real = (Rct * Z_Cdl_real * Rct + Rct * Z_Cdl_imag * Z_Cdl_imag) / denominator
    Z_parallel_imag = (Rct * Z_Cdl_real * Z_Cdl_imag - Rct * Z_Cdl_imag * Z_Cdl_real) / denominator

    # Actually let me simplify - Rct in parallel with Cdl
    Rct_inv = 1 / Rct
    Cdl_term = 1j * omega * Cdl
    Z_parallel = 1 / (Rct_inv + Cdl_term)
    Z_total = Rs + Z_parallel

    Z_real = np.real(Z_total)
    Z_imag = -np.imag(Z_total)  # -Z" for Nyquist plot (upper quadrant)
    Z_mag = np.sqrt(Z_real**2 + Z_imag**2)
    phase = -np.arctan2(Z_imag, Z_real) * 180 / np.pi

    # 写入 CHI660E EIS 格式
    lines = [
        "Synthetic Randles Cell EIS",
        "",
        "Freq/Hz, Z'/ohm, Z\"/ohm, Z/ohm, Phase/deg",
    ]

    for f, zr, zi, zm, ph in zip(frequencies, Z_real, Z_imag, Z_mag, phase):
        lines.append(f"{f:.6e}, {zr:.6e}, {zi:.6e}, {zm:.6e}, {ph:.6e}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "example_EIS.txt")
    _generate_eis_data(txt_path)

    eis = chi660eEIS.from_exported_files([txt_path], name="Randles EIS")
    print(f"EIS: {eis.name}")
    print(f"信号数量: {len(eis.signal_names)}")
    for sig_name in eis.signal_names:
        sig = eis[sig_name]
        print(f"  {sig_name}: {len(sig.data)} 个频率点")

    # 绘制 Nyquist 图
    fig, ax = eis.plot_nyquist()

    output_path = os.path.join(os.path.dirname(__file__), "example.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {output_path}")
