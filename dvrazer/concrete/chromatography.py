"""
``dvrazer.concrete.chromatography`` --- 色谱数据
====================================================================

色谱相关的具体信号类型:

- :class:`ChromSig` : 连续色谱信号 (UV, Cond, pH, 压力, 流速等)
- :class:`ChromLog` : 离散色谱日志 (馏分收集、进样标记)
- :class:`Chrom` : 完整的色谱图, 包含多个信号通道

默认绘图配置:
  模式 1 (多轴对比), 图大小 (20, 6)

色谱集合中的典型信号:
  - UV : 紫外吸收 (mAU)
  - Cond : 电导率 (mS/cm)
  - Conc B : 缓冲液 B 浓度 (%)
  - pH
  - Fractions : 馏分收集记录
"""

from dataclasses import dataclass, field
from ..abstract import (
    Signal1D,
    ContinuousSignal1D,
    DiscreteSignal1D,
    Signal1DCollection,
    Signal1DPlotArgs,
)


@dataclass(slots=True)
class ChromPlotArgs(Signal1DPlotArgs):

    def __post_init__(self):
        self.mode = 1
        self.ax_size = (16, 5)


@dataclass
class ChromSig(ContinuousSignal1D):
    pass


@dataclass
class ChromLog(DiscreteSignal1D):
    pass


@dataclass
class Chrom(Signal1DCollection):

    signal_type: type = ChromSig | ChromLog
    plot_args: ChromPlotArgs = field(default_factory=ChromPlotArgs)

    def correct_conc(self, conc_delay):
        """
        校正浓度信号, 因为浓度信号和实际的盐浓度有一定的延迟
        """
        data = self["Conc B"].get_data()
        data.iloc[:, 0] += conc_delay

    def get_signal(
        self, signal_name: str
    ) -> Signal1D | ContinuousSignal1D | DiscreteSignal1D:
        return super().get_signal(signal_name)
