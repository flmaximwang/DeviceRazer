"""
``dvrazer.instruments.Agilent`` --- Agilent 仪器数据解析
==========================================================

- :mod:`chemstation_processor` : ChemStation HPLC 色谱 (当前实现)
- :mod:`cary_winuv` : Cary WinUV (Cary 100/300) ``Scan`` 导出 CSV
- :mod:`chemstation_archive` : ChemStation 旧版解析 (legacy, 不作为公开 API 导出)

公开类型可直接从本包导入::

    from dvrazer.instruments.Agilent import ChemStChrom, CaryAbsSpecCollection
    from dvrazer.instruments import ChemStChrom          # 顶层也重新导出
"""

from .chemstation_processor import ChemStChrom, ChemStFrac, ChemStSig
from .cary_winuv import CaryAbsSpec, CaryAbsSpecCollection, CaryAbsSpecPlotArgs

__all__ = [
    "ChemStChrom",
    "ChemStFrac",
    "ChemStSig",
    "CaryAbsSpec",
    "CaryAbsSpecCollection",
    "CaryAbsSpecPlotArgs",
]
