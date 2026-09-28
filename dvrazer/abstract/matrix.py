"""
``dvrazer.abstract.matrix`` --- 矩阵
========================================================

:class:`Matrix` 是二维数据表, 以 :class:`pandas.DataFrame` 形式存储。
与 :class:`Signal` 类似带有 ``description_annotations``。

常用于多孔板数据或二维仪器数据。
:class:`~dvrazer.abstract.matrix_collection.MatrixSeries`
可用于管理时间序列中的多个矩阵。
"""

from dataclasses import dataclass, field
import pandas as pd
from .signal import DescAnno


@dataclass
class Matrix:

    name: str = None
    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    description_annotations: list[DescAnno] = field(default_factory=list)

    @classmethod
    def from_csv(cls, csv_file: str, header=None, index_col=None, sep=","):
        return cls(pd.read_csv(csv_file, header=header, index_col=index_col, sep=sep))

    @property
    def loc(self):
        return self.data.loc

    @property
    def iloc(self):
        return self.data.iloc
