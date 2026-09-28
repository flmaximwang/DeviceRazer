"""
``instruments.GE_Heathcare.unicorn7`` --- GE Healthcare / Cytiva Unicorn 7 (ÄKTA) 数据解析
============================================================================================

解析 Unicorn 7 软件导出的色谱数据 (UTF-16 LE 编码, tab 分隔的 .txt 文件)。

:class:`Unicorn7Chrom` 继承自 :class:`Chrom`, 解析后返回色谱集合列表
(每个色谱图对应一次进样/运行)。

支持自动识别以下信号类型:
- UV : 紫外吸收
- Cond : 电导率
- Conc B : 缓冲液 B 浓度
- pH
- Injection, Fraction : 进样和馏分标记
- Run Log : 运行日志
"""

import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Mapping
import pandas as pd
from dvrazer.abstract.signal import ContDescAnno, DescAnno
from dvrazer.abstract.signal_1d import (
    ContinuousSignal1D,
    DiscreteSignal1D,
    FractionSignal,
    Signal1D,
)
from ...concrete.chromatography import *


def extract_number_from_chrom(chrom_string):
    """
    从chromatogram的字符串中提取编号
    """
    my_pattern = re.compile(r"Chrom\.(\d+)")
    my_match = my_pattern.match(chrom_string)

    if my_match:
        return int(my_match.group(1)) - 1
    else:
        return None


class Unicorn7Project:

    def read_txt(txt: str | Path, name=None):
        raw_data = pd.read_csv(
            txt, sep="\t", encoding="UTF-16 LE", header=None, na_values=""
        )  # 空字符串不识别为 NaN
        chrom_name = Path(txt).stem if name is None else name
        # 第一行显示 chromatogram 的编号, 第二行显示信号的类型, 第三行为交替的时间和信号值
        results: Mapping[int, list] = {}
        for n, chrom_string in enumerate(raw_data.iloc[0, 0::2]):
            chrom_number = extract_number_from_chrom(chrom_string)
            if not chrom_number in results.keys():
                results[chrom_number] = []
                results[chrom_number].append(n)
            else:
                results[chrom_number].append(n)
        chromatograms: list[Chrom] = []
        signals: list[ChromSig, ChromLog]
        for i in results.keys():
            signals = []
            for n in results[i]:
                signal_data = raw_data.iloc[3:, 2 * n : 2 * n + 2].copy()
                signal_name = raw_data.iloc[1, 2 * n]
                if any(
                    [
                        re.match(pattern, signal_name)
                        for pattern in [
                            "UV",
                            "UV \\d_\\d{3}",
                            "Cond",
                            "Conc B",
                            "UV_CUT_TEMP@100,BASEM",
                            "pH",
                            "PreC pressure",
                            "DeltaC pressure",
                            "PostC pressure",
                            "System pressure",
                            "System flow",
                        ]
                    ]
                ):
                    # 设置 signal_data 的 2 列为 float
                    signal_data = signal_data.astype(float).dropna()
                    if signal_data.empty:
                        continue
                    signal = ChromSig.from_data(
                        data=signal_data,
                        axis_name="Volume",
                        axis_unit="mL",
                        value_name=signal_name,
                        value_unit=raw_data.iloc[2, 2 * n + 1],
                    )
                    signal.name = signal_name
                    signals.append(signal)
                elif raw_data.iloc[1, 2 * n] in ["Injection", "Fraction", "Run Log"]:
                    # 设置 signal_data 的 2 列为 float 和 str
                    signal_data = signal_data.astype(
                        {signal_data.columns[0]: float, signal_data.columns[1]: str}
                    ).dropna()
                    if signal_data.empty:
                        continue
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
                    raise Exception(f"Unknown signal type: {raw_data.iloc[1, 2*n]}")
            if not signals:
                continue  # skip chromatograms with no signals
            chromatograms.append(Chrom.from_similar_signals(signals=signals))
            chromatograms[-1].name = f"{chrom_name}_{i}"

        return chromatograms
