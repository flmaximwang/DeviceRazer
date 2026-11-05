"""
``dvrazer.instruments.ThermoFisher`` --- Thermo Fisher Scientific 仪器数据解析
==============================================================================

- :mod:`nanodrop2000` : NanoDrop 2000 紫外-可见光谱 (TSV)
- :mod:`multiscan_fc` : Multiskan FC 酶标仪 (TXT)
- :mod:`nanodrop_utils` : NanoDrop 旧版 API (legacy, 不作为公开 API 导出)

公开类型可直接从本包导入::

    from dvrazer.instruments.ThermoFisher import Nanodrop2000Workbook, MultiWellPlateFC
    from dvrazer.instruments import Nanodrop2000Workbook  # 顶层也重新导出
"""

from .nanodrop2000 import Nanodrop2000PlotArgs, Nanodrop2000Workbook
from .multiscan_fc import MultiWellPlateFC

__all__ = [
    "Nanodrop2000PlotArgs",
    "Nanodrop2000Workbook",
    "MultiWellPlateFC",
]
