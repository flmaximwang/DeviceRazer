"""SEC chromatogram plotter for Unicorn 7 .txt exports.

Usage:
    python examples/unicorn7/sec/sec.py -i <path/to/unicorn7.txt> \
        --column-type "Superdex 200 10/300" --buffer "20 mM Tris" \
        --flow-rate "0.5 mL/min" --sample-name "gammaPFD" --sample-volume "500 uL"

Example:
    python examples/unicorn7/sec/sec.py -i "data/2026-07-06_Purification-001_gammaPFD-Elution.txt" \
        --column-type "10/300" --buffer "Tris" --flow-rate "0.5" \
        --sample-name "gammaPFD" --sample-volume "0.5"
"""

import argparse
from pathlib import Path

import sys
import matplotlib.pyplot as plt
import numpy as np
from dvrazer import Chrom, ContinuousSignal1D
from dvrazer.instruments import Unicorn7Project


def parse_peak_range(text: str) -> tuple[float, float]:
    parts = text.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"{text!r} 格式应为 开始-结束, 例如 5-15")
    return float(parts[0]), float(parts[1])


def parse_args():

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("-i", "--input", type=str, required=True, help="请输入 SEC 的 txt")
    p.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="输出图片路径，默认与输入 txt 相同, 只是后缀改为 txt",
    )
    p.add_argument("--column-type", type=str, required=True, help="柱子的名称")
    p.add_argument("--buffer", type=str, required=True, help="缓冲液成分")
    p.add_argument("--flow-rate", type=str, required=True, help="流速")
    p.add_argument("--sample-name", type=str, required=True, help="样品名称")
    p.add_argument("--sample-volume", type=str, required=True, help="样品体积")
    p.add_argument(
        "--absorbance-channels", type=int, default=1, help="吸收信号通道数量"
    )
    p.add_argument(
        "--peaks",
        type=parse_peak_range,
        nargs="+",
        default=[],
        metavar="START-END",
        help="每个峰的范围 (ml)，格式为 开始-结束；例如 --peaks 5-15 20-30 表示两个峰",
    )
    p.add_argument(
        "--normalize-uvs",
        type=parse_peak_range,
        default=None,
        metavar="START-END",
        help="UV 归一化窗口 (ml)，格式为 开始-结束；设置后每个 UV 通道按窗口内最大值归一化，否则所有 UV 共用同一吸收范围（全 UV 最小值-最大值 ± 10%%）",
    )
    p.add_argument(
        "--baseline",
        type=parse_peak_range,
        default=None,
        metavar="START-END",
        help="UV 基线窗口 (ml)，格式为 开始-结束；以窗口内平均值为各 UV 通道值域下限，span 取各通道 (max-baseline) 的最大值，baseline 下方留空 10%%",
    )

    return p.parse_args()


def parse_output(input: str, output: str | None):
    if output is None:
        return Path(input).with_suffix(".png")
    else:
        return output


def parse_column_type(colume_type: str):

    COLUMN_SPECS = {
        "10/300": {
            "axis_range": 36,
            "axis_space_major": 5,
            "axis_space_minor": 1,
            "axis_digits": 0,
        },
        "16/600": {
            "axis_range": 180,
            "axis_space_major": 20,
            "axis_space_minor": 5,
            "axis_digits": 0,
        },
    }

    flag = False
    for column_spec in COLUMN_SPECS:
        if column_spec in colume_type:
            flag = True
            break
    if not flag:
        raise ValueError(
            f"COLUMN_TYPE must contain a column spec in {list(COLUMN_SPECS.keys())}"
        )

    return colume_type, COLUMN_SPECS[column_spec]


def main():

    args = parse_args()
    column_type, column_spec = parse_column_type(args.column_type)
    output = parse_output(args.input, args.output)

    my_chrom: Chrom = Unicorn7Project.read_txt(args.input)[0]
    my_chrom.set_default_annotations()

    my_chrom.align_axes(0, column_spec["axis_range"])
    my_chrom.axis_annotation.ticklabel_space_major = column_spec["axis_space_major"]
    my_chrom.axis_annotation.ticklabel_space_minor = column_spec["axis_space_minor"]
    my_chrom.axis_annotation.ticklabel_digits = column_spec["axis_digits"]

    visible_signal_names = []

    for i in range(args.absorbance_channels):
        for signal_name in my_chrom.signal_names:
            if f"UV {i+1}" in signal_name:
                visible_signal_names.append(signal_name)
                break

    visible_signal_names.append("Cond")
    if "Fraction" in my_chrom.visible_signal_names:
        visible_signal_names.append("Fraction")

    my_chrom.visible_signal_names = visible_signal_names

    uv_value_arrays = {
        name: my_chrom[name].slice_value_by_axis(0, column_spec["axis_range"])
        for name in visible_signal_names
        if "UV" in name
    }
    if args.normalize_uvs is not None:
        # 归一化模式: 每通道 max 取归一化窗口内最大值
        norm_left, norm_right = args.normalize_uvs
        uv_maxes = {
            name: max(my_chrom[name].slice_value_by_axis(norm_left, norm_right))
            for name in uv_value_arrays
        }
    else:
        # 默认模式: 每通道 max 取显示窗口内最大值
        uv_maxes = {name: max(values) for name, values in uv_value_arrays.items()}

    uv_baselines: dict[str, float] = {}
    if args.baseline is not None:
        base_left, base_right = args.baseline
        for name in uv_value_arrays:
            uv_baselines[name] = float(
                np.mean(my_chrom[name].slice_value_by_axis(base_left, base_right))
            )

    # 每个 UV 通道的 (value_range, ticklabel_space)
    uv_display: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {}
    if args.baseline is not None:
        # baseline 模式: 各通道 baseline 均值作下限, span 取 (max-baseline) 最大值,
        # baseline 下方留空 10%, 各通道区间跨度相同
        uv_D = max(uv_maxes[name] - uv_baselines[name] for name in uv_value_arrays)
        uv_span = 1.1 * uv_D
        uv_ticks = (uv_span / 5, uv_span / 25)
        for name in uv_value_arrays:
            baseline = uv_baselines[name]
            uv_display[name] = (
                (baseline - 0.1 * uv_D, baseline + uv_D),
                uv_ticks,
            )
    elif args.normalize_uvs is not None:
        # 归一化模式: 值域 [0, 窗口内 max]
        for name in uv_value_arrays:
            max_value = uv_maxes[name]
            uv_display[name] = ((0, max_value), (max_value / 5, max_value / 25))
    else:
        # 默认共用范围: 全 UV 最小值-最大值 ± 10%
        uv_min = min(min(values) for values in uv_value_arrays.values())
        uv_max = max(uv_maxes.values())
        uv_difference = uv_max - uv_min
        uv_value_range = (
            uv_min - 0.1 * uv_difference,
            uv_max + 0.1 * uv_difference,
        )
        uv_ticks = (uv_difference / 5, uv_difference / 25)
        for name in uv_value_arrays:
            uv_display[name] = (uv_value_range, uv_ticks)

    for signal_name in visible_signal_names:
        if signal_name in ["Fraction"]:
            continue
        signal: ContinuousSignal1D = my_chrom[signal_name]
        if "UV" in signal_name:
            value_range, ticklabel_space = uv_display[signal_name]
            my_chrom.align_values([signal_name], *value_range)
            signal.value_annotation.ticklabel_space = ticklabel_space
            signal.value_annotation.ticklabel_digits = 2
        elif "Cond" in signal_name:
            sliced_value = signal.slice_value_by_axis(0, column_spec["axis_range"])
            max_value = max(sliced_value)
            min_value = min(sliced_value)
            sliced_value_difference = max_value - min_value
            value_range = (
                min_value - 0.1 * sliced_value_difference,
                max_value + 0.1 * sliced_value_difference,
            )
            ticklabel_space_major = sliced_value_difference / 5
            ticklabel_space_minor = sliced_value_difference / 25
            my_chrom.align_values([signal_name], *value_range)
            signal.value_annotation.ticklabel_space = (
                ticklabel_space_major,
                ticklabel_space_minor,
            )
            signal.value_annotation.ticklabel_digits = 3
        else:
            raise ValueError(f"{signal_name} not supported")

    my_chrom.name = f"[{column_type}] {args.buffer} ({args.flow_rate}): {args.sample_name} ({args.sample_volume})"
    my_chrom.plot_args.ax_size = (21, 7)
    my_chrom.plot_args.axis_shift = 0.11
    fig, axes = my_chrom.plot()

    if args.peaks:
        for i in range(args.absorbance_channels):
            signal: ContinuousSignal1D = my_chrom[visible_signal_names[i]]
            for axis_left, axis_right in args.peaks:
                peak_axis, _ = signal.get_peak_between(axis_left, axis_right)
                if np.isclose(peak_axis, axis_left) or np.isclose(
                    peak_axis, axis_right
                ):
                    # 峰落在窗口边界 -> 真峰在窗外, 不标注
                    continue
                # mode=1 时 fig.axes 顺序 = [主轴] + twins, UV i 对应 fig.axes[i]
                signal.plot_peak_at(fig.axes[i], axis_left, axis_right)

    fig.savefig(output, dpi=300)


if __name__ == "__main__":
    main()
