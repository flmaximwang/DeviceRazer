"""
``dvrazer.concrete.kinetics`` --- 动力学数据
================================================================

动力学曲线相关的具体信号类型:

- :class:`KineticCurve` : 时间过程测量曲线
- :class:`KineticCurveCollection` : 动力学曲线集合

用于表示时间分辨的测量数据, 如酶动力学、细胞生长曲线等。
"""

from ..abstract.signal_1d import ContinuousSignal1D
from ..abstract.signal_1d_collection import ContinuousSignal1DCollection


class KineticCurve(ContinuousSignal1D):
    pass


class KineticCurveCollection(ContinuousSignal1DCollection):
    pass
