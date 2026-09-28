"""
``dvrazer.abstract`` --- 抽象数据模型层
=======================================================

该模块定义了整个库的抽象数据模型框架，包括：

信号类层次
----------
:class:`Signal` (基类)
    → :class:`Signal1D` (一维信号: 连续轴 + 任意值)
        → :class:`ContinuousSignal1D` (连续轴 + 连续值, 支持代数运算和插值)
        → :class:`DiscreteSignal1D` (连续轴 + 离散值)
            → :class:`FractionSignal` (馏分信号)
        → :class:`SegmentedSignal1D` (分段信号: 伏安法等)
    → :class:`Signal2D` (二维信号, 框架预留)

集合类层次
----------
:class:`SignalCollection` (基类, 字典式访问)
    → :class:`Signal1DCollection` (1D 信号集合, 批量绘图)
        → :class:`ContinuousSignal1DCollection` (连续信号集合, 支持平均)

描述注释系统
------------
:class:`DescAnno` → 名称 + 单位
:class:`ContDescAnno` → + 范围(limit) + 边距(margin) + 刻度(ticklabels/ticks)
:class:`DiscDescAnno` → + 刻度数/刻度列表

矩阵类
------
:class:`Matrix` (二维数据表)
:class:`MatrixSeries` (按轴排列的矩阵序列)

绘图参数
--------
:class:`SignalPlotArgs` (图大小、配色、图例)
:class:`Signal1DPlotArgs` (+ 绘图模式)

使用模式
--------
1. 直接使用具体信号类型 (concrete module) 进行数据分析
2. 通过仪器解析器 (instruments module) 读取原始数据
3. 自定义子类继承 ``Signal1D`` 扩展新的仪器类型
"""

from .signal import *
from .signal_collection import *
from .signal_1d import (
    Signal1D,
    ContinuousSignal1D,
    DiscreteSignal1D,
    FractionSignal,
)
from .signal_1d_collection import Signal1DCollection, ContinuousSignal1DCollection
from .matrix import Matrix
from .matrix_collection import MatrixSeries
from .display import SignalPlotArgs, Signal1DPlotArgs
