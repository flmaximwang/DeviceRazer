"""
``dvrazer.concrete.spectroscopy`` --- 光谱数据
=================================================================

光谱相关的具体信号类型:

- :class:`Spectrum` : 通用光谱 (ContinuousSignal1D 的别名)
- :class:`SpectrumCollection` : 光谱集合
- :class:`AbsorbSpec` : 吸收光谱
- :class:`AbsorbSpecCollection` : 吸收光谱集合

这些类本身没有额外行为, 主要提供语义化的类型名称,
使得代码更具可读性。
"""

from dataclasses import dataclass, field
from ..abstract import (
    ContinuousSignal1D,
    ContinuousSignal1DCollection,
    ContDescAnno,
)


@dataclass
class Spectrum(ContinuousSignal1D):

    pass


@dataclass
class SpectrumCollection(ContinuousSignal1DCollection):

    pass


@dataclass
class AbsorbSpec(ContinuousSignal1D):

    pass


@dataclass
class AbsorbSpecCollection(ContinuousSignal1DCollection):

    pass
