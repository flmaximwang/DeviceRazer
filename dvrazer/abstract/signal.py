"""
``dvrazer.abstract.signal`` --- Signal 基类与描述注释系统
==============================================================================

该模块定义了整个库的两个核心抽象：

1. **描述注释系统** --- 为每个数据维度附加物理含义

   - :class:`DescAnno` : 名称 + 单位
   - :class:`ContDescAnno` : + 连续范围(limit)、边距(margin)、自动刻度(ticks/ticklabels)
   - :class:`DiscDescAnno` : + 离散刻度

2. **Signal 基类** --- 所有数据类型的根

   - 数据以 :class:`pandas.DataFrame` 形式存储
   - 每一列通过 ``description_annotations`` 列表进行注释
   - 提供 :meth:`Signal.from_csv` / :meth:`Signal.to_csv` 进行数据导入导出
   - 提供 :meth:`Signal.rescale` 进行线性缩放

数据在 :class:`~pandas.DataFrame` 中的组织方式:

  ==========  ==========
  Column 0    Column 1   (可选 Column 2 ...)
  ==========  ==========
  axis / x     value / y   value_std (optional)
  ==========  ==========
  第 0 列通常是连续轴 (如波长、时间、体积),
  第 1 列是测量值 (如吸光度、电流),
  第 2 列可选的标准偏差 (用于 :class:`~dvrazer.abstract.signal_1d.ContinuousSignal1D`).
"""

import os, re, time, warnings
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import dvrazer.utils.path_utils as path_utils
from ..utils import transform_utils


@dataclass
class DescAnno:
    """
    Every signal contains multiple descriptions, which is continuous / discrete.
    This class is used to annotate each description for its
    type (like Volume), unit (like mL), limit (like (0, 10)) and ticks (like tick_number = 5)
    """

    name: str = None
    unit: str = None

    @property
    def label(self):
        if self.unit is None:
            return self.name
        else:
            return f"{self.name} ({self.unit})"


@dataclass
class ContDescAnno(DescAnno):
    """
    Continuous description annotation

    Properties
    ----------
    limit: tuple[float, float]
        The (min, max) limits for the continuous description.
    tick_number: int
        The number of ticks to be displayed on the axis.
    margin: tuple[float, float]
        The (lower_margin, upper_margin) as fractions of the total range.
    digits: int
        The number of decimal places for tick labels.
    """

    limit: tuple[float, float] = None
    margin: tuple[float, float] = (0.0, 1.0)
    ticklabel_floor: float = None
    _ticklabel_space_major: float = None
    _ticklabel_space_minor: float = None
    ticklabel_digits: int = 0

    @property
    def ticklabel_space_major(self):
        return self._ticklabel_space_major

    @ticklabel_space_major.setter
    def ticklabel_space_major(self, value):
        self._ticklabel_space_major = value
        if value > 1:
            self.ticklabel_digits = 0
        elif value > 0.1:
            self.ticklabel_digits = 1
        elif value > 0.01:
            self.ticklabel_digits = 2
        elif value > 0.001:
            self.ticklabel_digits = 3
        else:
            self.ticklabel_digits = 4

    @property
    def ticklabel_space_minor(self):
        return self._ticklabel_space_minor

    @ticklabel_space_minor.setter
    def ticklabel_space_minor(self, value):
        self._ticklabel_space_minor = value

    @property
    def ticklabel_space(self):
        return self._ticklabel_space_major, self._ticklabel_space_minor

    @ticklabel_space.setter
    def ticklabel_space(self, value):
        major, minor = value
        self.ticklabel_space_major = major
        self.ticklabel_space_minor = minor

    @property
    def ticklabels(self):
        assert self.limit is not None, "limit is not set"
        assert (
            self.ticklabel_space_major is not None
        ), "ticklabel_space_major is not set"
        assert self.ticklabel_digits is not None, "ticklabel_digits is not set"

        if self.ticklabel_floor is None:
            ticklabel_floor = self.limit[0]
        else:
            ticklabel_floor = self.ticklabel_floor

        numbers = []
        c_number = ticklabel_floor
        while c_number <= self.limit[1]:
            numbers.append(c_number)
            c_number += self.ticklabel_space_major

        strings = [f"{num:.{self.ticklabel_digits}f}" for num in numbers]
        return strings

    @property
    def ticks(self):
        assert self.margin is not None, "margin is not set"

        ticklabels = np.array(list(map(float, self.ticklabels)))
        limit_range = self.limit[1] - self.limit[0]
        if limit_range == 0:
            return np.full_like(ticklabels, (self.margin[0] + self.margin[1]) / 2)
        ticks = (ticklabels - self.limit[0]) / limit_range * (
            self.margin[1] - self.margin[0]
        ) + self.margin[0]
        return ticks

    @property
    def ticks_minor(self):
        """Minor tick positions in normalized [0, 1] coordinates.

        Returns None when *ticklabel_space_minor* is not set, so callers
        can safely skip setting minor ticks on the Axes.
        """
        if self.ticklabel_space_minor is None:
            return None
        assert self.limit is not None, "limit is not set"
        assert self.margin is not None, "margin is not set"

        if self.ticklabel_floor is None:
            ticklabel_floor = self.limit[0]
        else:
            ticklabel_floor = self.ticklabel_floor

        numbers = []
        c_number = ticklabel_floor
        while c_number <= self.limit[1]:
            numbers.append(c_number)
            c_number += self.ticklabel_space_minor

        limit_range = self.limit[1] - self.limit[0]
        if limit_range == 0:
            return np.full_like(
                np.array(numbers), (self.margin[0] + self.margin[1]) / 2
            )
        ticks = (np.array(numbers) - self.limit[0]) / limit_range * (
            self.margin[1] - self.margin[0]
        ) + self.margin[0]
        return ticks


@dataclass
class DiscDescAnno(DescAnno):

    limit: tuple[float, float] = (0, 1)
    tick_number: int = 0
    ticks: list = field(default_factory=lambda: [0])
    ticklabels: list = field(default_factory=lambda: [""])


@dataclass
class Signal:
    """
    a signal is composed of multiple descriptions.
    At least one description is continuous for all instruments.
    These descriptions are represented by columns in a pandas.DataFrame and therefore have equal lengths.
    More specific signals are subclasses that have defined descriptions.

    Properties
    ----------
    data: pd.DataFrame
        A pandas DataFrame containing the signal data. Each column represents a different description.
    name: str
        The name of the signal.
    description_annotations: list[DescAnno]
        A list of DescAnno objects that annotate each description in the data.
    """

    data: pd.DataFrame = None
    name: str = None
    description_annotations: list[DescAnno] = field(default_factory=list)

    @staticmethod
    def get_type_and_unit_from_header(header):
        """
        Returns type and unit from header string
        """
        type_unit_pattern = re.match(r"(.*) \((.*)\)", header)
        if type_unit_pattern is None:
            # No unit found
            return header, None
        else:
            return type_unit_pattern.group(1), type_unit_pattern.group(2)

    @classmethod
    def from_csv(cls, path, name=None, **kwargs):
        """
        See pandas.read_csv for supported kwargs
        """
        if name is None:
            name = path_utils.get_name_from_path(path)
        data = pd.read_csv(path, **kwargs)
        return cls(data, name)

    @staticmethod
    def rescale(
        array: np.ndarray, limit: tuple[float, float], margin: tuple[float, float]
    ):
        """
        Rescale [lower_limit, upper_limit] to [lower_margin, upper_margin] linearly.

        Parameters
        ----------
        array : np.ndarray
        limit : tuple[float, float]
            A tuple specifying the (min, max) limits for rescaling.
        margin : tuple[float, float]
            A tuple specifying the (lower_margin, upper_margin) as fractions of the total range.
        """

        scaled_to_0_1 = transform_utils.rescale_to_0_1(array, limit[0], limit[1])
        scaled_to_margin_range = (margin[1] - margin[0]) * scaled_to_0_1 + margin[0]
        return scaled_to_margin_range

    def to_csv(self, csv: str | Path):
        """
        Export signal to export_path
        """
        csv = Path(csv)
        directory = csv.parent

        if not directory.exists():
            directory.mkdir(parents=True)
        if csv.exists():
            time_stamp = time.strftime("%Y%m%d_%H%M%S")
            csv = csv.with_name(f"{csv.stem}_{time_stamp}{csv.suffix}")
            warnings.warn(f"File {csv} already exists. Renamed to {csv.name}.")
        columns = []
        for desc_anno in self.description_annotations:
            columns.append(desc_anno.label)
        self.data.columns = columns
        self.data.to_csv(csv, index=False)
