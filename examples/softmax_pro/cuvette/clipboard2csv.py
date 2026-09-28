"""
SoftMax Pro 比色皿 (Cuvette) 数据导出 CSV
===========================================

读取 SoftMax Pro 导出的比色皿 .txt 文件，解析后导出为 CSV。

使用方法::

    # 默认：导出 Raw-Ref (OD) 段
    python examples/softmax_pro/example.py /path/to/data.txt

    # 指定模式为 Transmission (%)
    python examples/softmax_pro/example.py /path/to/data.txt --mode Transmission

    # 指定导出 Ref 段
    python examples/softmax_pro/example.py /path/to/data.txt --section Ref

    # 指定输出路径
    python examples/softmax_pro/example.py /path/to/data.txt -o result.csv
"""

import argparse
import sys
from pathlib import Path

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_CuvetteData,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SoftMax Pro 比色皿数据导出 CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "txt",
        type=str,
        help="SoftMax Pro 导出的比色皿 .txt 文件路径",
    )
    parser.add_argument(
        "-s",
        "--section",
        default="Raw-Ref",
        choices=["Wavelength", "Ref", "Raw-Ref"],
        help="要导出的数据段（默认: Raw-Ref）",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="OD",
        choices=["OD", "Transmission"],
        help="数据类型: OD (吸光度, cm⁻¹) 或 Transmission (透光率, %)，（默认: OD）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="输出 CSV 文件路径（默认: <输入文件名>_<section>_<mode>.csv）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    txt_path = Path(args.txt)
    if not txt_path.exists():
        print(f"错误: 文件不存在: {txt_path}")
        sys.exit(1)

    # 解析数据
    print(f"读取: {txt_path}")
    curve = SoftMaxPro_CuvetteData.from_clipboard(
        txt=str(txt_path),
        section=args.section,
        mode=args.mode,
    )

    print(f"样本: {curve._extra_metadata['sample_name']}")
    print(f"段: {args.section}  |  模式: {args.mode}")
    print(f"温度: {curve._extra_metadata['temperature']} °C")
    print(f"数据点数: {len(curve.data)}")

    # 确定输出路径
    if args.output:
        csv_path = Path(args.output)
    else:
        stem = txt_path.stem
        csv_path = txt_path.with_name(f"{stem}_{args.section}_{args.mode}.csv")

    # 输出 CSV（保留列标题中的单位）
    curve.data.to_csv(csv_path, index=False)
    print(f"已保存: {csv_path}")


if __name__ == "__main__":
    main()
