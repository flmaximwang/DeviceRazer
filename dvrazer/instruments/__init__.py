"""
``dvrazer.instruments`` --- 仪器数据解析层
===========================================================

为各厂商仪器/软件导出文件提供解析器, 解析结果为 :mod:`dvrazer.concrete`
中的具体信号类型。按厂商分子包:

- :mod:`Agilent` : ChemStation HPLC, Cary WinUV
- :mod:`CH_Instruments` : CHI660E 电化学工作站 (CV / EIS)
- :mod:`Cytiva` : ÄKTA / Unicorn 5, 7 (重新导出 :mod:`GE_Heathcare`)
- :mod:`GE_Heathcare` : ÄKTA / Unicorn 5, 7 的真实实现 (目录名保留历史拼写)
- :mod:`MolecularDevices` : SoftMax Pro 酶标仪
- :mod:`ThermoFisher` : NanoDrop 2000, Multiskan FC

所有公开解析类型都可以直接从本包导入 (扁平导入)::

    from dvrazer.instruments import ChemStChrom, chi660eCV, Unicorn5Chrom
    from dvrazer.instruments import Nanodrop2000Workbook, SoftMaxPro_Project

也可以使用完整模块路径, 两种方式等价::

    from dvrazer.instruments.Cytiva.unicorn7 import Unicorn7Project
"""

from .Agilent import (
    CaryAbsSpec,
    CaryAbsSpecCollection,
    CaryAbsSpecPlotArgs,
    ChemStChrom,
    ChemStFrac,
    ChemStSig,
)
from .CH_Instruments import chi660eCV, chi660eEIS
from .Cytiva import Unicorn5Chrom, Unicorn7Chrom, Unicorn7Project
from .MolecularDevices import (
    SoftMaxPro_CuvetteData,
    SoftMaxPro_Group,
    SoftMaxPro_Plate,
    SoftMaxPro_Plate_Endpoint,
    SoftMaxPro_Plate_Kinetic,
    SoftMaxPro_Plate_Spectrum,
    SoftMaxPro_Project,
    SoftMaxPro_Protocol,
)
from .ThermoFisher import (
    MultiWellPlateFC,
    Nanodrop2000PlotArgs,
    Nanodrop2000Workbook,
)

__all__ = [
    # Agilent
    "ChemStChrom",
    "ChemStFrac",
    "ChemStSig",
    "CaryAbsSpec",
    "CaryAbsSpecCollection",
    "CaryAbsSpecPlotArgs",
    # CH Instruments
    "chi660eCV",
    "chi660eEIS",
    # Cytiva / GE Healthcare
    "Unicorn5Chrom",
    "Unicorn7Chrom",
    "Unicorn7Project",
    # Molecular Devices
    "SoftMaxPro_Project",
    "SoftMaxPro_Protocol",
    "SoftMaxPro_Plate",
    "SoftMaxPro_Plate_Endpoint",
    "SoftMaxPro_Plate_Kinetic",
    "SoftMaxPro_Plate_Spectrum",
    "SoftMaxPro_Group",
    "SoftMaxPro_CuvetteData",
    # Thermo Fisher
    "Nanodrop2000Workbook",
    "Nanodrop2000PlotArgs",
    "MultiWellPlateFC",
]
