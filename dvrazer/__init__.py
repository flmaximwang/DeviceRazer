"""
``dvrazer`` --- 仪器数据处理库顶层包
=======================================================

按依赖方向重新导出三层公开 API, 因此文档中的扁平导入可直接使用::

    from dvrazer import Signal, ContinuousSignal1D      # abstract 层
    from dvrazer import MultiWellPlate, Chrom           # concrete 层
    from dvrazer.instruments import ChemStChrom         # 仪器解析器

导入顺序必须是 abstract → instruments → concrete: 解析器模块在导入时会
引用 abstract 层的类, 并触发 concrete 包的初始化 (concrete/__init__.py
从 abstract 导入基类)。
"""

from .abstract import *
from .instruments import *
from .concrete import *
from .utils import *
