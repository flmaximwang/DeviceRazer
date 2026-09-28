"""
``instruments.GE_Heathcare.unicorn5`` --- GE Healthcare / Cytiva Unicorn 5 (ÄKTA) 数据解析
============================================================================================

解析 Unicorn 5 软件 (ÄKTA 纯化系统) 导出的色谱数据。

支持两种文件格式:
- **.xls** : 标准 Excel 导出 (sheet "Curves")
- **.asc** : 文本格式导出 (ISO-8859-15 编码, tab 分隔)

:class:`Unicorn5Chrom` 继承自 :class:`Chrom`, 解析后返回包含 UV、Cond、
Conc B、pH、Fractions 等信号的色谱集合。

使用示例::

    from dvrazer.instruments import Unicorn5Chrom
    chrom = Unicorn5Chrom.from_xls("run_001.xls")
    chrom["UV"].plot_at(ax)
    chrom["Cond"].plot_at(ax)
"""

import os, re
from dataclasses import dataclass, field
from copy import deepcopy
from collections import OrderedDict
from typing import Mapping
import pandas as pd
from dvrazer.abstract.signal_1d import (
    ContinuousSignal1D,
    DiscreteSignal1D,
    FractionSignal,
    Signal1D,
)
from dvrazer.abstract.signal_1d_collection import Signal1DCollection
from dvrazer.utils import path_utils
from ...concrete.chromatography import *


@dataclass
class Unicorn5Chrom(Chrom):

    @staticmethod
    def from_xls(filepath, name=None):
        chrom_df = pd.read_excel(
            filepath,
            sheet_name="Curves",
            skiprows=1,
        )
        signals: list[ChromSig, ChromLog] = []
        for i, col_name in enumerate(chrom_df.columns):
            if re.match(r"Unnamed: \d+", col_name):
                continue
            signal_data = chrom_df.iloc[1:, [i, i + 1]].dropna()
            signal_name = col_name.split("_")[-1]
            if any(
                [
                    re.match(pattern, signal_name)
                    for pattern in [
                        "UV",
                        "Cond",
                        "Conc B",
                        "pH",
                        "Temp",
                        "Pressure",
                        "Flow",
                    ]
                ]
            ):
                signal_data = signal_data.astype(float)
                signal = ChromSig.from_data(
                    data=signal_data,
                    name=signal_name,
                    axis_name="Volume",
                    axis_unit="mL",
                    value_name=signal_name,
                    value_unit=chrom_df.iloc[0, i + 1],
                )
                signals.append(signal)
            elif any([re.match(pattern, signal_name) for pattern in ["Fractions"]]):
                signal_data = signal_data.astype(
                    {signal_data.columns[0]: float, signal_data.columns[1]: str}
                )
                signals.append(
                    ChromLog.from_data(
                        data=signal_data,
                        name=signal_name,
                        axis_name="Volume",
                        axis_unit="mL",
                        value_name=signal_name,
                        value_unit=None,
                    )
                )
            else:
                raise ValueError(
                    f"Unknown signal type: {signal_name} in column {col_name}"
                )
        if name:
            chromatogram = Chrom(signals, name=name)
        else:
            chromatogram = Chrom(
                signals, name="_".join(chrom_df.columns[0].split("_")[:-1])
            )
        return chromatogram

    @classmethod
    def from_asc(cls, asc, names=None):
        with open(asc, "r", encoding="iso-8859-15") as f:
            f.readline()  # skip first line
            signal_names = f.readline().strip().split("\t")
            signal_names = [
                signal_name.strip() for signal_name in signal_names if signal_name
            ]
            grouped_signal_annotations: Mapping[str, list[Mapping]] = OrderedDict()
            for signal_name in signal_names:
                group = signal_name.split("_")[0]
                if group not in grouped_signal_annotations:
                    grouped_signal_annotations[group] = []
                grouped_signal_annotations[group].append(
                    {
                        "axis_name": None,
                        "axis_unit": None,
                        "value_name": signal_name.split("_")[-1],
                        "value_unit": None,
                    }
                )

            units = f.readline().strip().split("\t")
            units = [unit.strip() for unit in units if unit]
            for group, signal_annotations in grouped_signal_annotations.items():
                for j, signal_annotation in enumerate(signal_annotations):
                    axis_unit = units[2 * j]
                    if axis_unit in ["min", "s"]:
                        signal_annotation["axis_name"] = "Time"
                    elif axis_unit in ["mL", "ml"]:
                        signal_annotation["axis_name"] = "Volume"
                    else:
                        raise ValueError(f"Unknown axis unit: {axis_unit}")
                    signal_annotation["axis_unit"] = axis_unit
                    signal_annotation["value_unit"] = units[2 * j + 1]

        data = pd.read_csv(
            asc, sep="\t", skiprows=3, encoding="iso-8859-15", header=None
        )
        res: dict[str, Unicorn5Chrom] = {}
        for i, (group, signal_annotations) in enumerate(
            grouped_signal_annotations.items()
        ):
            signals: list[Signal1D] = []
            for j, signal_annotation in enumerate(signal_annotations):
                row_selector = data.iloc[:, 2 * j].apply(
                    lambda x: (
                        len(x.split()) != 0
                        if isinstance(x, str)
                        else not pd.isna(x)
                    )
                )
                signal_data = data[row_selector].iloc[:, [2 * j, 2 * j + 1]]
                signal_name = signal_annotation["value_name"]
                if any(
                    [
                        re.match(pattern, signal_name)
                        for pattern in [
                            "UV",
                            "Cond",
                            "Conc",
                            "pH",
                            "Temp",
                            "Pressure",
                            "Flow",
                        ]
                    ]
                ):
                    signal_data = signal_data.astype(float)
                    signal = ChromSig.from_data(
                        data=signal_data,
                        axis_name=signal_annotation["axis_name"],
                        axis_unit=signal_annotation["axis_unit"],
                        value_name=signal_annotation["value_name"],
                        value_unit=signal_annotation["value_unit"],
                    )
                    signal.name = signal_name
                    signals.append(signal)
                elif any(
                    [
                        re.match(pattern, signal_name)
                        for pattern in ["Fractions", "Inject", "Logbook"]
                    ]
                ):
                    signal_data = signal_data.astype(
                        {signal_data.columns[0]: float, signal_data.columns[1]: str}
                    )
                    signal = ChromLog.from_data(
                        data=signal_data,
                        name=signal_name,
                        axis_name=signal_annotation["axis_name"],
                        axis_unit=signal_annotation["axis_unit"],
                        value_name=signal_annotation["value_name"],
                        value_unit=None,
                    )
                    signal.name = signal_name
                    signals.append(signal)
                else:
                    raise ValueError(f"Unknown signal type: {signal_name}")
            res_group = cls(
                signals=signals,
                visible_signal_names=[signal.name for signal in signals],
                name=names[i] if names else group,
            )
            res_group.description_annotations = deepcopy(
                res_group["UV"].description_annotations
            )
            if "Conc" in res_group:
                res_group["Conc"].value_annotation.limit = (0, 100)
            if "Flow" in res_group:
                res_group["Flow"].value_annotation.limit = (
                    min(res_group["Flow"].value) - 1,
                    max(res_group["Flow"].value) + 1,
                )
            res[group] = res_group
        if len(res) == 1:
            return res[group]
        else:
            return res
