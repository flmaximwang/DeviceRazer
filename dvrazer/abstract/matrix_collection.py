"""
``dvrazer.abstract.matrix_collection`` --- 矩阵序列
======================================================================

:class:`MatrixSeries` 是按照一个轴排列的多个矩阵的集合。

例如: 在动力学实验中, 每个时间点读取一个多孔板,
可以表示为 ``MatrixSeries``, 其中 ``data`` 列存储时间,
``matrices`` 存储每个时间点的板数据。

提供到 :class:`~dvrazer.abstract.signal_1d_collection.ContinuousSignal1DCollection`
的便捷转换方法。
"""

import typing
from dataclasses import dataclass, field
import pandas as pd
from .signal import DescAnno
from .signal_1d import ContinuousSignal1D
from .signal_1d_collection import ContinuousSignal1DCollection
from .matrix import Matrix


class _LocIndexer:
    def __init__(self, collection: "MatrixSeries"):
        self.collection = collection

    def __getitem__(self, slice):
        result = []
        for matrix in self.collection.matrices:
            result.append(matrix.loc[slice])
        return result


class _ILocIndexer:
    def __init__(self, collection: "MatrixSeries"):
        self.collection = collection

    def __getitem__(self, slice):
        result = []
        for matrix in self.collection.matrices:
            result.append(matrix.iloc[slice])
        return result


@dataclass
class MatrixSeries:
    """
    A MatrixSeries contains multiple matrices, each of which corresponds to a specific point along an axis.

    Parameters
    ----------
    description_annotations : list[DescAnno]
        Annotations for the axes and values of the matrices in the collection.
        Axis annotation is the first element, and annotation for values in matrices is the last element.
        Middle elements can be used for additional descriptions if self.data has more than 1 columns.
    """

    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    matrices: list[Matrix] = field(default_factory=list)
    description_annotations: list[DescAnno] = field(default_factory=list)

    def __getitem__(self, key: str) -> Matrix:
        return self.matrices[key]

    @property
    def axis(self):
        if pd.api.types.is_numeric_dtype(self.data.iloc[:, 0]):
            return self.data.iloc[:, 0]
        else:
            return self.data.iloc[:, 0].to_numpy()

    @axis.setter
    def axis(self, value):
        self.data.iloc[:, 0] = value

    @property
    def loc(self):
        return _LocIndexer(self)

    @property
    def iloc(self):
        return _ILocIndexer(self)

    @property
    def axis_annotation(self):
        return self.description_annotations[0]

    @property
    def value_annotation(self):
        return self.description_annotations[-1]

    def to_continuous_signal_1d_collection(self):
        signals = []
        for i, col_name in enumerate(self.data.columns[1:]):
            values = self.data[col_name]
            data = pd.DataFrame(
                {
                    "Axis": self.axis,
                    "Value": values,
                }
            )
            signal = ContinuousSignal1D.from_data(
                data=data,
                name=str(col_name),
                axis_name=self.axis_annotation.name,
                axis_unit=self.axis_annotation.unit,
                value_name=self.description_annotations[i + 1].name,
                value_unit=self.description_annotations[i + 1].unit,
            )
            signals.append(signal)
        return ContinuousSignal1DCollection.from_similar_signals(signals)

    def to_continuous_signal_1d_collection_with_locs(self, loc_slice_list: list[tuple]):
        signals = []
        for loc_slice in loc_slice_list:
            values = self.loc[loc_slice]
            data = pd.DataFrame(
                {
                    "Axis": self.axis,
                    "Value": values,
                }
            )
            signal = ContinuousSignal1D.from_data(
                data=data,
                axis_name=self.axis_annotation.name,
                axis_unit=self.axis_annotation.unit,
                value_name=self.value_annotation.name,
                value_unit=self.value_annotation.unit,
            )
            signal.name = str(loc_slice)
            signals.append(signal)
        return ContinuousSignal1DCollection.from_similar_signals(signals)
