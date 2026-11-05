"""
``dvrazer.concrete`` --- 具体领域信号类型
===========================================================

在 :mod:`dvrazer.abstract` 的通用信号模型之上, 按领域定义具体类型:

- :mod:`spectroscopy` : 光谱 (``Spectrum``, ``AbsorbSpec`` 及其集合)
- :mod:`chromatography` : 色谱 (``Chrom``, ``ChromSig``, ``ChromLog``)
- :mod:`kinetics` : 动力学 (``KineticCurve`` 集合)
- :mod:`voltammetry` : 伏安法 (``Voltammegram`` 集合)
- :mod:`impedance_spectroscopy` : 阻抗谱 (``ImpedanceSpectrum`` 集合)
- :mod:`multi_well_plates` : 多孔板 (``MultiWellPlate``, ``MultiWellPlateSeries``)

各仪器解析器 (:mod:`dvrazer.instruments`) 返回的就是这里的类型。
所有公开类型同时可以直接从本包顶层导入::

    from dvrazer.concrete import MultiWellPlate, Chrom, AbsorbSpecCollection
    from dvrazer import MultiWellPlate          # 顶层也重新导出
"""

from .spectroscopy import (
    Spectrum,
    SpectrumCollection,
    AbsorbSpec,
    AbsorbSpecCollection,
)
from .chromatography import (
    ChromPlotArgs,
    ChromSig,
    ChromLog,
    Chrom,
)
from .kinetics import KineticCurve, KineticCurveCollection
from .voltammetry import Voltammegram, VoltammegramCollection
from .impedance_spectroscopy import (
    ImpedanceSpectrum,
    ImpedanceSpectrumCollection,
)
from .multi_well_plates import MultiWellPlate, MultiWellPlateSeries

__all__ = [
    # spectroscopy
    "Spectrum",
    "SpectrumCollection",
    "AbsorbSpec",
    "AbsorbSpecCollection",
    # chromatography
    "ChromPlotArgs",
    "ChromSig",
    "ChromLog",
    "Chrom",
    # kinetics
    "KineticCurve",
    "KineticCurveCollection",
    # voltammetry
    "Voltammegram",
    "VoltammegramCollection",
    # impedance spectroscopy
    "ImpedanceSpectrum",
    "ImpedanceSpectrumCollection",
    # multi-well plates
    "MultiWellPlate",
    "MultiWellPlateSeries",
]
