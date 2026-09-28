"""
``dvrazer.concrete.voltammetry`` --- 伏安法数据
====================================================================

电化学伏安法相关的具体信号类型:

- :class:`Voltammegram` : 循环伏安图
  - 继承 :class:`SegmentedContinuousSignal1D`
  - 电位 (Potential, V) 作为轴, 电流 (Current, A) 作为值
  - 数据按扫描段 (Segment) 组织

- :class:`VoltammegramCollection` : 伏安图集合

数据格式约定:
  ============  ============  =========  ========
  Sequence      Potential (V) Current(A) Segment
  ============  ============  =========  ========
  0             0.2           0.2        1
  1             0.22          0.3        1
  ...           ...           ...        ...
  10            0.4           0.4        1
  11            0.38          0.38       2
  ...           ...           ...        ...
  ============  ============  =========  ========
"""

from dvrazer.abstract.signal_1d import ContinuousSignal1D
from ..abstract.signal_1d import SegmentedContinuousSignal1D
from ..abstract.signal_1d_collection import (
    Signal1DCollection,
    ContinuousSignal1DCollection,
)
from ..abstract import DescAnno, ContDescAnno
import pandas as pd
import matplotlib.pyplot as plt


class Voltammegram(SegmentedContinuousSignal1D):

    def __init__(self, data: pd.DataFrame, name: str = "Voltammegram"):
        """
        A voltammetry signal should looks like\n
        Sequence,Potential (V),Current (A),Segment\n
        0,0.2,0.2,1\n
        1,0.22,0.3,1\n
        ...\n
        10,0.4,0.4,1\n
        11,0.38,0.38,2\n
        ...\n
        """
        axis_anno = ContDescAnno(name="Potential", unit="V")
        value_anno = ContDescAnno(name="Current", unit="A")
        super().__init__(
            data=data,
            name=name,
            description_annotations=[axis_anno, value_anno],
        )
        self.active_segments = "all"

    def get_current_limit(self):
        return self.get_axis_limit()

    def get_voltage_limit(self):
        return self.get_value_limit()


class VoltammegramCollection(ContinuousSignal1DCollection):

    def __init__(
        self,
        signals: list[Voltammegram] = None,
        name: str = "Default Voltammegram Collection",
        visible_signal_names: list[str] = None,
        figsize=None,
    ):
        if signals is None:
            signals = []
        axis_anno = ContDescAnno(
            name="Potential",
            unit="V",
            limit=(0, 0),
            margin=(0.1, 0.9),
        )
        value_anno = ContDescAnno(
            name="Current",
            unit="A",
            limit=(0, 0),
            margin=(0.1, 0.9),
        )
        description_annotations = [axis_anno, value_anno]
        if visible_signal_names is None:
            visible_signal_names = [sig.name for sig in signals]
        super().__init__(
            signals=signals,
            name=name,
            description_annotations=description_annotations,
            visible_signal_names=visible_signal_names,
        )
        self.set_default_annotations()

    def __getitem__(self, key: str):
        res: Voltammegram = super().__getitem__(key)
        return res
