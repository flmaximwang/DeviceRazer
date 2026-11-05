"""
``dvrazer.abstract.signal_1d`` --- 一维信号
================================================================

该模块实现了 ``Signal`` 的一维子类层次, 包括:

- :class:`Signal1D` : 基础一维信号, 具有 连续轴(axis) + 值(value)
- :class:`ContinuousSignal1D_Base` : axis 和 value 都连续
  - 支持通过 ``__getitem__`` 插值
  - ``value`` / ``std`` 是按 axis 值插值的视图 (``sig.value[axis_i]`` / ``sig.std[axis_i]``)
  - 支持算术运算 (+, -, *, /)
  - 支持峰检测、积分、平均
- :class:`ContinuousSignal1D_Process` : 信号处理 (平滑、去噪)
- :class:`ContinuousSignal1D` : 最终具体的连续信号类
- :class:`DiscreteSignal1D` : 连续轴 + 离散值
- :class:`SegmentedSignal1D` : 分段信号 (带 Segment 列)
- :class:`SegmentedContinuousSignal1D` : 分段连续信号
- :class:`FractionSignal` : 馏分信号 (特殊的离散信号)

辅助类:
- :class:`_Interpolate` : 在一维数据上通过 ``np.interp`` 进行插值
- :class:`_InterpolateBetweenBounds` : 由上下限插值得到标准偏差的插值视图

数据约定:
  DataFrame 的第 0 列是 axis (连续), 第 1 列是 value,
  第 2 列 (可选) 是 value_std (标准偏差).

插值访问:
  ``signal[axis_i]`` 与 ``signal.value[axis_i]`` 等价, 都按 axis 值插值;
  ``signal.std[axis_i]`` 由上下限插值得到 (见 :class:`_InterpolateBetweenBounds`).
"""

import typing
from dataclasses import dataclass
from pathlib import Path
from copy import deepcopy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from .signal import *
from ..utils import path_utils, transform_utils

chromatographic_units_map_types = {
    "min": "Time",
    "mL": "Volume",
    "ml": "Volume",
    "mAU": "Absorbance",
}

spectroscopic_units_map_types = {
    "nm": "Wavelength",
    "": "Absorbance",
}

units_map_types = [chromatographic_units_map_types, spectroscopic_units_map_types]


class _Interpolate:
    """在连续 axis 上对 value 做线性插值的视图。

    既可以按 axis 值插值访问 (``interp[axis_i]``), 也保留数组式访问
    (``len`` / 迭代 / ``np.asarray`` / 算术运算 / ``pandas`` 与 ``numpy`` 的方法),
    因此 :attr:`ContinuousSignal1D_Base.value` 可以直接返回它而不破坏既有代码。
    """

    def __init__(self, axis: typing.Iterable[float], value: typing.Iterable[float]):
        self.axis = np.asarray(axis, dtype=float)
        self.value = np.asarray(value, dtype=float)

    @staticmethod
    def _as_axis_values(axis_i):
        """把 slice 解释为 axis 范围 (``interp[280:283]`` → axis 280, 281, 282);
        未给 step 时按 1 处理。"""
        if isinstance(axis_i, slice):
            step = 1 if axis_i.step is None else axis_i.step
            return np.arange(axis_i.start, axis_i.stop, step)
        return axis_i

    def __getitem__(self, axis_i: int | float | slice | typing.Iterable[float]):
        """
        Get the value at the given axis value using 1D interpolation.
        """
        return np.interp(self._as_axis_values(axis_i), self.axis, self.value)

    def __repr__(self):
        return f"{type(self).__name__}({len(self.value)} points)"

    # ------------------------------------------------------------------
    # 数组式访问: 保持 ``signal.value`` 作为数组使用的向后兼容
    # ------------------------------------------------------------------
    def __array__(self, dtype=None, copy=None):
        array = self.value if dtype is None else self.value.astype(dtype, copy=False)
        return array.copy() if copy else array

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __getattr__(self, name):
        # __getattr__ 只在常规属性查找失败时被调用;
        # 下划线开头的名称 (如 __deepcopy__) 直接报 AttributeError, 避免干扰
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(pd.Series(self.value), name)

    def __add__(self, other):
        return pd.Series(self.value) + other

    def __radd__(self, other):
        return other + pd.Series(self.value)

    def __sub__(self, other):
        return pd.Series(self.value) - other

    def __rsub__(self, other):
        return other - pd.Series(self.value)

    def __mul__(self, other):
        return pd.Series(self.value) * other

    def __rmul__(self, other):
        return other * pd.Series(self.value)

    def __truediv__(self, other):
        return pd.Series(self.value) / other

    def __rtruediv__(self, other):
        return other / pd.Series(self.value)

    def __neg__(self):
        return -pd.Series(self.value)

    def __abs__(self):
        return abs(pd.Series(self.value))


class _InterpolateBetweenBounds(_Interpolate):
    """以 (下限, 上限) 两条边界插值定义的连续视图, 用于标准偏差。

    每个数据点的边界由 ``value ± value_std`` 给出; 插值时分别对上限与下限做
    线性插值, 再取两者之差的一半作为插值点的标准偏差::

        std(x) = (upper(x) - lower(x)) / 2

    上下限不对称时该定义依然成立 (线性插值下, 若上下限对称则与直接对
    ``value_std`` 插值的结果一致)。
    """

    def __init__(
        self,
        axis: typing.Iterable[float],
        lower: typing.Iterable[float],
        upper: typing.Iterable[float],
    ):
        self.lower = np.asarray(lower, dtype=float)
        self.upper = np.asarray(upper, dtype=float)
        super().__init__(axis, (self.upper - self.lower) / 2)

    def __getitem__(self, axis_i: int | float | slice | typing.Iterable[float]):
        """
        分别在上下限上插值, 返回 (上限 - 下限) / 2
        """
        axis_values = self._as_axis_values(axis_i)
        lower = np.interp(axis_values, self.axis, self.lower)
        upper = np.interp(axis_values, self.axis, self.upper)
        return (upper - lower) / 2


@dataclass
class Signal1D(Signal):
    axis_annotation_type = ContDescAnno
    value_annotation_type = DescAnno

    """
    1D signals are signals with two descriptions.

    - The first is called axis (which is continuous),
    - The second is called value (which may be continuous or discrete).

    Value describes the property of every point on the axis, like the absorbance of a sample at a certain wavelength.

    Properties
    ----------
    axis_name: str
        The name of the axis description, like "Time", "Volume", "Wavelength".
    axis_unit: str
        The unit of the axis description, like "min", "mL", "nm".
    value_name: str
        The name of the value description, like "Absorbance", "Intensity".
    value_unit: str
        The unit of the value description, like "mAU", "a.u.".
    """

    @property
    def axis(self):
        return self.data.iloc[:, 0]

    @axis.setter
    def axis(self, new_axis):
        self.data[self.data.columns[0]] = new_axis.astype(float)

    @property
    def axis_annotation(self):
        axis_annotation: ContDescAnno = self.description_annotations[0]
        return axis_annotation

    @axis_annotation.setter
    def axis_annotation(self, new_axis_annotation):
        self.description_annotations[0] = new_axis_annotation

    @property
    def value_annotation(self):
        value_annotation: DescAnno = self.description_annotations[1]
        return value_annotation

    @value_annotation.setter
    def value_annotation(self, new_value_annotation):
        self.description_annotations[1] = new_value_annotation

    @property
    def value(self):
        return self.data.iloc[:, 1]

    @value.setter
    def value(self, new_value):
        self.data[self.data.columns[1]] = new_value

    @classmethod
    def from_data(
        cls,
        data: pd.DataFrame,
        axis_name=None,
        axis_unit=None,
        value_name=None,
        value_unit=None,
        detect_axis_name_and_unit=False,
        detect_value_name_and_unit=False,
        name="Untitled",
    ):
        """
        Given a dataframe with two/three columns, create a Signal1D object.
        """
        if detect_axis_name_and_unit:
            axis_name_temp, axis_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[0]
            )
        else:
            axis_name_temp = data.columns[0]
            axis_unit_temp = None
        if not axis_name and axis_name_temp:
            axis_name = axis_name_temp
        if not axis_unit and axis_unit_temp:
            axis_unit = axis_unit_temp

        if detect_value_name_and_unit:
            value_name_temp, value_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[1]
            )
        else:
            value_name_temp = data.columns[1]
            value_unit_temp = None
        if not value_name and value_name_temp:
            value_name = value_name_temp
        if not value_unit and value_unit_temp:
            value_unit = value_unit_temp

        description_annotations = [
            ContDescAnno(
                name=axis_name,
                unit=axis_unit,
            ),
            ContDescAnno(
                name=value_name,
                unit=value_unit,
            ),
        ]
        res = cls(data=data, name=name, description_annotations=description_annotations)
        res.update_data_headers()
        return res

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        name=None,
        detect_axis_name_and_unit=True,
        detect_value_name_and_unit=True,
        axis_name=None,
        axis_unit=None,
        value_name=None,
        value_unit=None,
    ):
        """
        Read a signal from a csv file.

        Parameters
        ----------
        path : str | Path
            Path of the csv file (the first line is used as the header).
        name : str, optional
            Name of the resulting signal. Defaults to the file stem.
        detect_axis_name_and_unit : bool
            If True (default), split the axis header like ``"Wavelength (nm)"``
            into the axis name and unit.
        detect_value_name_and_unit : bool
            If True (default), split the value header into name and unit.
        axis_name, axis_unit, value_name, value_unit : str, optional
            Explicit annotations. They take precedence over the detected ones.
        """
        csv_path = Path(path)
        data = pd.read_csv(csv_path)
        if name is None:
            name = csv_path.stem
        return cls.from_data(
            data=data,
            name=name,
            detect_axis_name_and_unit=detect_axis_name_and_unit,
            detect_value_name_and_unit=detect_value_name_and_unit,
            axis_name=axis_name,
            axis_unit=axis_unit,
            value_name=value_name,
            value_unit=value_unit,
        )

    def slice_axis(self, left_limit: float, right_limit: float, include_limit=True):
        """
        Return part of the axis where it is between left_limit & right_limit
        """
        res = self.data.iloc[:, 0][
            (self.data.iloc[:, 0] >= left_limit) & (self.data.iloc[:, 0] <= right_limit)
        ].to_numpy()
        if include_limit:
            if left_limit < min(res):
                res = np.concatenate([[left_limit], res])
            if right_limit > max(res):
                res = np.concatenate([res, [right_limit]])
        return res

    def slice_value_by_axis(self, left_limit: float, right_limit: float):
        """
        Return part of the value where the corresponding axis is between left_limit & right_limit
        """
        return self.data.iloc[:, 1][
            (self.data.iloc[:, 0] >= left_limit) & (self.data.iloc[:, 0] <= right_limit)
        ].to_numpy()

    def update_data_headers(self):
        old_columns = self.data.columns
        new_columns = [self.axis_annotation.label, self.value_annotation.label]
        self.data.rename(columns=dict(zip(old_columns, new_columns)), inplace=True)

    def update_type_and_unit_from_data(
        self, detect_axis_name_and_unit=True, detect_value_name_and_unit=True
    ):
        if detect_axis_name_and_unit:
            axis_name, axis_unit = self.get_type_and_unit_from_header(
                self.data.columns[0]
            )
        else:
            axis_name, axis_unit = self.data.columns[0], None
        if detect_value_name_and_unit:
            value_name, value_unit = self.get_type_and_unit_from_header(
                self.data.columns[1]
            )
        else:
            value_name, value_unit = self.data.columns[1], None
        self.axis_annotation.name = axis_name
        self.axis_annotation.unit = axis_unit
        self.value_annotation.name = value_name
        self.value_annotation.unit = value_unit

    def plot_at(self, ax: plt.Axes, label=None, **kwargs):
        """
        The method to plot a signal should only be implemented when the form of signal has been well defined.
        Such a method should retrun a Line2D
        """
        (handle,) = ax.plot([0], [0], label=label, **kwargs)
        return handle


@dataclass
class ContinuousSignal1D_Base(Signal1D):
    """
    ContinuousSignal1D 是 Signal1D 的子类, 用于表示 axis 与 value 都是连续的 Signal1D
    """

    value_annotation_type = ContDescAnno

    @property
    def value_std(self):
        try:
            return self.data.iloc[:, 2]
        except IndexError:
            return None

    @property
    def value(self):
        """
        连续值的插值视图, ``signal.value[axis_i]`` 与 ``signal[axis_i]`` 等价。

        该视图同时保留数组式访问 (``len`` / 迭代 / ``np.asarray`` / ``to_numpy`` /
        算术运算 / ``pandas`` 与 ``numpy`` 的方法), 原始数组为 ``signal.data.iloc[:, 1]``。
        """
        return _Interpolate(self.axis, self.data.iloc[:, 1])

    @value.setter
    def value(self, new_value):
        self.data[self.data.columns[1]] = new_value

    @property
    def value_annotation(self):
        value_annotation: ContDescAnno = self.description_annotations[1]
        return value_annotation

    @property
    def value_limit(self):
        return self.value_annotation.limit

    @value_limit.setter
    def value_limit(self, new_value_limit):
        self.value_annotation.limit = new_value_limit

    def get_value_limit(self):
        return self.value_limit

    def get_value_margin(self):
        return self.value_margin

    def get_axis_limit(self):
        return self.axis_annotation.limit

    def get_axis_margin(self):
        return self.axis_annotation.margin

    @property
    def value_margin(self):
        return self.value_annotation.margin

    @value_margin.setter
    def value_margin(self, new_value_margin):
        self.value_annotation.margin = new_value_margin

    def slice_value_by_axis(self, left_limit, right_limit, include_limit: bool = True):
        sliced_axis = self.slice_axis(
            left_limit=left_limit, right_limit=right_limit, include_limit=include_limit
        )
        sliced_value = self[sliced_axis]
        return sliced_value

    @classmethod
    def from_data(
        cls,
        data: pd.DataFrame,
        axis_name=None,
        axis_unit=None,
        value_name=None,
        value_unit=None,
        detect_axis_name_and_unit=False,
        detect_value_name_and_unit=False,
        name="Untitled",
    ):
        """
        Given a dataframe with two/three columns, create a Signal1D object.
        """
        if detect_axis_name_and_unit:
            axis_name_temp, axis_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[0]
            )
        else:
            axis_name_temp = data.columns[0]
            axis_unit_temp = None
        if not axis_name and axis_name_temp:
            axis_name = axis_name_temp
        if not axis_unit and axis_unit_temp:
            axis_unit = axis_unit_temp

        if detect_value_name_and_unit:
            value_name_temp, value_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[1]
            )
        else:
            value_name_temp = data.columns[1]
            value_unit_temp = None
        if not value_name and value_name_temp:
            value_name = value_name_temp
        if not value_unit and value_unit_temp:
            value_unit = value_unit_temp

        description_annotations = [
            ContDescAnno(
                name=axis_name,
                unit=axis_unit,
                limit=(
                    (min(data.iloc[:, 0]), max(data.iloc[:, 0]))
                    if len(data) > 0
                    else (0, 1)
                ),
                margin=(0, 1),
            ),
            ContDescAnno(
                name=value_name,
                unit=value_unit,
                limit=(
                    (min(data.iloc[:, 1]), max(data.iloc[:, 1]))
                    if len(data) > 0
                    else (0, 1)
                ),
                margin=(0, 1),
            ),
        ]
        res = cls(data=data, description_annotations=description_annotations, name=name)
        res.update_data_headers()
        return res

    def __getitem__(self, axis_i: int | float | slice | typing.Iterable[float]):
        """
        Get the value at the given axis value using 1D interpolation.
        """
        interpolator = _Interpolate(self.axis, self.data.iloc[:, 1])
        return interpolator[axis_i]

    @property
    def std(self):
        """
        标准偏差的插值视图, ``signal.std[axis_i]`` 给出该 axis 位置的标准偏差。

        插值按上下限进行: 每个数据点的上下限由 ``value ± value_std`` 得到,
        然后分别对上限与下限做线性插值, 取 ``(上限 - 下限) / 2`` (见
        :class:`_InterpolateBetweenBounds`)。

        Raises
        ------
        ValueError
            信号没有 std 列 (只有 :meth:`average` / ``average_similar_signals()``
            平均得到的信号才带标准偏差)。
        """
        value_std = self.value_std
        if value_std is None:
            raise ValueError(
                f"Signal '{self.name}' has no std column; "
                "only averaged signals (average() / average_similar_signals()) carry a value_std"
            )
        values = np.asarray(self.data.iloc[:, 1], dtype=float)
        stds = np.asarray(value_std, dtype=float)
        return _InterpolateBetweenBounds(self.axis, values - stds, values + stds)

    @classmethod
    def average(
        cls,
        signals: list["ContinuousSignal1D"],
    ):
        """
        Averaging multiple ContinuousSignal1D signals into one ContinuousSignal1D signal.
        An extra std column will be added to the data to represent the standard deviation of the values at the same axis.
        """
        list_of_axes = [signal.axis for signal in signals]
        merged_axis = np.unique(np.concatenate(list_of_axes))
        merged_axis.sort()
        merged_value = np.zeros_like(merged_axis, dtype=float)
        value_std = np.zeros_like(merged_axis, dtype=float)
        for i, axis_i in enumerate(merged_axis):
            values = [signal[axis_i] for signal in signals]
            merged_value[i] = np.mean(values)
            value_std[i] = np.std(values)
        axis_name = signals[0].axis_annotation.name
        axis_unit = signals[0].axis_annotation.unit
        value_name = signals[0].value_annotation.name
        value_unit = signals[0].value_annotation.unit
        merged_data = pd.DataFrame(
            {"Axis": merged_axis, "Values": merged_value, "Value_std": value_std}
        )
        return cls.from_data(
            merged_data,
            axis_name=axis_name,
            axis_unit=axis_unit,
            value_name=value_name,
            value_unit=value_unit,
        )

    def __add__(self, the_other, name=None):
        if isinstance(the_other, (int, float)):
            new_value = self.value + the_other
            new_data = self.data.copy()
            new_data.iloc[:, 1] = new_value
            if self.value_std is not None:
                new_data.iloc[:, 2] = self.value_std
            result = type(self)(
                data=new_data,
                name=f"({self.name}) + ({the_other})" if name is None else name,
                description_annotations=deepcopy(self.description_annotations),
            )
            return result
        elif isinstance(the_other, ContinuousSignal1D):
            if (
                self.axis_annotation.name != the_other.axis_annotation.name
                or self.axis_annotation.unit != the_other.axis_annotation.unit
                or self.value_annotation.name != the_other.value_annotation.name
                or self.value_annotation.unit != the_other.value_annotation.unit
            ):
                raise ValueError(
                    "Only ContinuousSignal1D with the same axis and value name and unit can be added"
                )
            list_of_axes = [self.axis, the_other.axis]
            merged_axis = np.unique(np.concatenate(list_of_axes))
            merged_axis.sort()
            merged_value = np.zeros_like(merged_axis)
            for i, axis_i in enumerate(merged_axis):
                merged_value[i] = self[axis_i] + the_other[axis_i]
            merged_data = pd.DataFrame({"Axis": merged_axis, "Values": merged_value})
            result = ContinuousSignal1D.from_data(
                merged_data,
                axis_name=self.axis_annotation.name,
                axis_unit=self.axis_annotation.unit,
                value_name=self.value_annotation.name,
                value_unit=self.value_annotation.unit,
            )
            result.name = (
                f"({self.name}) + ({the_other.name})" if name is None else name
            )
            return result
        else:
            raise ValueError(
                f"Unsupported type for addition: {type(the_other)}, only int, float and ContinuousSignal1D are supported"
            )

    def __neg__(self, name=None):
        negated_data = self.data.copy()
        negated_data.iloc[:, 1] = -negated_data.iloc[:, 1]
        if self.value_std is not None:
            negated_data.iloc[:, 2] = self.value_std
        return type(self)(
            data=negated_data,
            name=f"-({self.name})" if name is None else name,
            description_annotations=deepcopy(self.description_annotations),
        )

    def __sub__(self, the_other, name=None):
        return self.__add__(-the_other, name=name)

    def _validate_same_descriptions(self, other: "ContinuousSignal1D", operation: str):
        """Raise if *other* cannot be combined element-wise with ``self``."""
        if (
            self.axis_annotation.name != other.axis_annotation.name
            or self.axis_annotation.unit != other.axis_annotation.unit
            or self.value_annotation.name != other.value_annotation.name
            or self.value_annotation.unit != other.value_annotation.unit
        ):
            raise ValueError(
                f"Only ContinuousSignal1D with the same axis and value name and unit can be {operation}"
            )

    @staticmethod
    def _merged_axis(*signals: "ContinuousSignal1D") -> np.ndarray:
        """Union of the axes of several signals (sorted, without duplicates)."""
        axes = [np.asarray(signal.axis, dtype=float) for signal in signals]
        merged_axis = np.unique(np.concatenate(axes))
        merged_axis.sort()
        return merged_axis

    @staticmethod
    def _propagated_std(value, operands) -> np.ndarray:
        """Standard deviation of a product / ratio from relative errors.

        For both ``value = a * b`` and ``value = a / b`` the relative error
        propagates as ``std(value) / |value| = sqrt((sa/a)^2 + (sb/b)^2)``.

        Parameters
        ----------
        value : np.ndarray
            Result of the product / ratio.
        operands : iterable of (operand_value, operand_std)
        """
        value = np.asarray(value, dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            relative_variance = np.zeros(value.shape, dtype=float)
            for operand_value, operand_std in operands:
                relative_variance = relative_variance + (
                    np.asarray(operand_std, dtype=float)
                    / np.asarray(operand_value, dtype=float)
                ) ** 2
        return np.abs(value) * np.sqrt(relative_variance)

    def __mul__(self, other, name=None):
        if isinstance(other, (int, float)):
            new_value = self.value * other
            new_data = self.data.copy()
            new_data.iloc[:, 1] = new_value
            if self.value_std is not None:
                new_data.iloc[:, 2] = self.value_std * abs(other)
            result = type(self)(
                data=new_data,
                name=f"({self.name}) * ({other})" if name is None else name,
                description_annotations=deepcopy(self.description_annotations),
            )
            return result
        elif isinstance(other, ContinuousSignal1D):
            self._validate_same_descriptions(other, "multiplied")
            merged_axis = self._merged_axis(self, other)
            self_values = np.asarray(self[merged_axis], dtype=float)
            other_values = np.asarray(other[merged_axis], dtype=float)
            merged_value = self_values * other_values
            data = {"Axis": merged_axis, "Values": merged_value}
            if self.value_std is not None and other.value_std is not None:
                data["Value_std"] = self._propagated_std(
                    merged_value,
                    (
                        (self_values, np.asarray(self.std[merged_axis], dtype=float)),
                        (other_values, np.asarray(other.std[merged_axis], dtype=float)),
                    ),
                )
            result = type(self)(
                data=pd.DataFrame(data),
                name=f"({self.name}) * ({other.name})" if name is None else name,
                description_annotations=deepcopy(self.description_annotations),
            )
            return result
        else:
            raise ValueError(
                f"Unsupported type for multiplication: {type(other)}, only int and float are supported"
            )

    def __truediv__(self, other, name=None):
        if isinstance(other, (int, float)):
            if other == 0:
                raise ValueError("Cannot divide by zero")
            new_value = self.value / other
            new_data = self.data.copy()
            new_data.iloc[:, 1] = new_value
            if self.value_std is not None:
                new_data.iloc[:, 2] = self.value_std / abs(other)
            result = type(self)(
                data=new_data,
                name=f"({self.name}) / ({other})" if name is None else name,
                description_annotations=deepcopy(self.description_annotations),
            )
            return result
        elif isinstance(other, ContinuousSignal1D):
            self._validate_same_descriptions(other, "divided")
            merged_axis = self._merged_axis(self, other)
            self_values = np.asarray(self[merged_axis], dtype=float)
            other_values = np.asarray(other[merged_axis], dtype=float)
            if np.any(other_values == 0):
                raise ValueError("Cannot divide by zero")
            merged_value = self_values / other_values
            data = {"Axis": merged_axis, "Values": merged_value}
            if self.value_std is not None and other.value_std is not None:
                data["Value_std"] = self._propagated_std(
                    merged_value,
                    (
                        (self_values, np.asarray(self.std[merged_axis], dtype=float)),
                        (other_values, np.asarray(other.std[merged_axis], dtype=float)),
                    ),
                )
            result = type(self)(
                data=pd.DataFrame(data),
                name=f"({self.name}) / ({other.name})" if name is None else name,
                description_annotations=deepcopy(self.description_annotations),
            )
            return result
        else:
            raise ValueError(
                f"Unsupported type for division: {type(other)}, only int and float are supported"
            )

    def blank_with(self, blank, name=None):
        return self.__sub__(
            blank, name=f"{self.name} blanked" if name is None else name
        )

    def rescale_between(self, target_0, target_1, inplace=False):
        """
        Rescale the values linearly so that ``target_0 -> 0`` and ``target_1 -> 1``.

        Parameters
        ----------
        target_0, target_1 : float
            The two original values mapped to 0 and 1.
        inplace : bool
            If True, write the rescaled values back into ``self.data``.

        Returns
        -------
        np.ndarray
            The rescaled values.
        """
        if target_1 == target_0:
            raise ValueError("target_0 and target_1 should be different")
        values = (np.asarray(self.data.iloc[:, 1], dtype=float) - target_0) / (
            target_1 - target_0
        )
        if inplace:
            # column assignment (instead of ``self.data.iloc[:, 1] = values``)
            # also promotes an integer column to float without a lossy cast
            self.data[self.data.columns[1]] = values
        return values

    def get_peak_between(self, axis_left, axis_right) -> tuple[float, float]:
        """
        Get the peak (axis, value) between the given axis range.
        """
        sliced_axis = self.slice_axis(axis_left, axis_right)
        if len(sliced_axis) == 0:
            raise ValueError("No data in the given range")
        sliced_value: np.ndarray = self[sliced_axis]
        peak_idx = sliced_value.argmax()
        peak_axis = sliced_axis[peak_idx]
        peak_value = sliced_value[peak_idx]
        return (peak_axis, peak_value)

    def plot_at(self, ax: plt.Axes, **kwargs):
        """
        Plot the signal at the given ax and return an artist handle.
        You can provide extra arguments to the plot function by **kwargs. Available arguments are listed below:
        - color: str
        - linewidth: float
        - linestyle: str
        - label: str
        - alpha: float
        - marker: str
        - horizontalalignment: center | right | left
        - verticalalignment: center | top | bottom
        """
        kwargs.pop("text_shift", None)
        label = kwargs.pop("label", None)
        if not label:
            label = self.name
        kwargs_for_annotate = kwargs.copy()
        kwargs_for_Line2D = kwargs.copy()

        kwargs_for_annotate.pop("color", None)
        kwargs_for_Line2D.pop("fontsize", None)
        kwargs_for_Line2D.pop("rotation", None)
        kwargs_for_Line2D.pop("mode", None)
        kwargs_for_annotate.pop("mode", None)

        assert self.axis_annotation.limit is not None, "Axis limit is not set"
        assert self.axis_annotation.margin is not None, "Axis margin is not set"
        assert self.value_annotation.limit is not None, "Value limit is not set"
        assert self.value_annotation.margin is not None, "Value margin is not set"
        (handle,) = ax.plot(
            self.rescale(
                self.axis,
                self.axis_annotation.limit,
                self.axis_annotation.margin,
            ),
            self.rescale(
                np.asarray(self.value),
                self.value_annotation.limit,
                self.value_annotation.margin,
            ),
            label=label,
            **kwargs_for_Line2D,
        )
        if self.value_std is not None:
            l_color = handle.get_color()
            rgba = mcolors.to_rgba(l_color)
            alpha = 1.0 if rgba[3] is None else rgba[3] / 4
            fill_color = rgba[:3] + (alpha,)
            ax.fill_between(
                self.rescale(
                    self.axis,
                    self.axis_annotation.limit,
                    self.axis_annotation.margin,
                ),
                self.rescale(
                    self.value - self.value_std,
                    self.value_annotation.limit,
                    self.value_annotation.margin,
                ),
                self.rescale(
                    self.value + self.value_std,
                    self.value_annotation.limit,
                    self.value_annotation.margin,
                ),
                color=fill_color,
                **kwargs_for_annotate,
            )
        return handle

    def plot_peak_at(
        self,
        ax: plt.Axes,
        axis_left: float,
        axis_right: float,
        type="vline",
        text_shift=(0, 0),
        text_digits=2,
        **kwargs,
    ):
        """
        type can be "vline" or "annotation"
        You can provide extra arguments to the plot function by **kwargs. Available arguments are listed below:
        - color: str
        - linewidth: float
        - linestyle: str
        - label: str
        - alpha: float
        - marker: str
        - horizontalalignment: center | right | left
        - verticalalignment: center | top | bottom
        """
        peak_axis, peak_value = self.get_peak_between(axis_left, axis_right)
        axis_limit = self.axis_annotation.limit
        value_limit = self.value_annotation.limit
        rescaled_peak_axis = transform_utils.rescale_to_0_1(
            peak_axis, axis_limit[0], axis_limit[1]
        )
        rescaled_peak_value = transform_utils.rescale_to_0_1(
            peak_value, value_limit[0], value_limit[1]
        )
        if type == "vline":
            self._plot_peak_at_with_vline(
                ax,
                rescaled_peak_axis=rescaled_peak_axis,
                rescaled_peak_value=rescaled_peak_value,
                peak_axis=peak_axis,
                peak_value=peak_value,
                text_shift=text_shift,
                text_digits=text_digits,
                **kwargs,
            )
        elif type == "annotation":
            self._plot_peak_at_with_annotation(
                ax,
                peak_axis=peak_axis,
                peak_value=peak_value,
                rescaled_peak_axis=rescaled_peak_axis,
                rescaled_peak_value=rescaled_peak_value,
                text_shift=text_shift,
                **kwargs,
            )

    def _plot_peak_at_with_vline(
        self,
        ax: plt.Axes,
        rescaled_peak_axis,
        rescaled_peak_value,
        peak_axis,
        peak_value,
        text_shift,
        text_digits=2,
        **kwargs,
    ):
        linestyle = kwargs.pop("linestyle", "dashed")
        ax.vlines(
            rescaled_peak_axis, 0, rescaled_peak_value, linestyles=linestyle, **kwargs
        )
        ax.annotate(
            f"{peak_axis:.{text_digits}f} {self.axis_annotation.unit}: {peak_value:.{text_digits}f}",
            xy=(rescaled_peak_axis, rescaled_peak_value),
            xytext=(
                rescaled_peak_axis + text_shift[0],
                rescaled_peak_value + text_shift[1],
            ),
            **kwargs,
        )

    def _plot_peak_at_with_annotation(
        self,
        ax: plt.Axes,
        rescaled_peak_axis,
        rescaled_peak_value,
        peak_axis,
        peak_value,
        text_shift,
        **kwargs,
    ):
        ax.annotate(
            f"{peak_axis:.2f} {self.axis_annotation.unit}",
            xy=(rescaled_peak_axis, rescaled_peak_value),
            xytext=(
                rescaled_peak_axis + text_shift[0],
                rescaled_peak_value + text_shift[1],
            ),
            **kwargs,
        )

    def integrate_between(self, start, end, baseline=0.0, ax=None, **fill_kwargs):
        """
        Integrate the signal between two axis values.

        The area is computed with the trapezoidal rule on the sliced signal
        after subtracting *baseline*. If *ax* is given, the integrated region
        is drawn on that axes and vertical lines are drawn at *start* / *end*.

        Parameters
        ----------
        start, end : float
            Limits of the integration interval on the axis.
        baseline : float or iterable of float
            Subtracted from the values before integration. A scalar is applied
            to every point; an iterable must have one value per point of the
            sliced signal.
        ax : matplotlib.axes.Axes, optional
            Axes to draw the integrated region on.
        **fill_kwargs
            Extra arguments for :meth:`matplotlib.axes.Axes.fill_between`
            (e.g. ``color``, ``alpha``, ``label``). ``color``, ``linestyle``,
            ``linewidth`` and ``alpha`` are also applied to the boundary lines.

        Returns
        -------
        float
            The integrated area between *start* and *end*.
        """
        signal_data = self.data[
            (self.data.iloc[:, 0] >= start) & (self.data.iloc[:, 0] <= end)
        ]
        if len(signal_data) == 0:
            raise ValueError(f"No data between {start} and {end}")

        axis_values = np.asarray(signal_data.iloc[:, 0], dtype=float)
        signal_values = np.asarray(signal_data.iloc[:, 1], dtype=float)

        if np.isscalar(baseline):
            baseline_values = np.full(signal_values.shape, float(baseline))
        else:
            baseline_values = np.asarray(baseline, dtype=float)
            if baseline_values.ndim == 0 or baseline_values.size == 1:
                baseline_values = np.full(
                    signal_values.shape, float(baseline_values.ravel()[0])
                )
            elif baseline_values.shape != signal_values.shape:
                raise ValueError(
                    "Baseline length should be equal to the length of signal data"
                )

        peak_area = float(np.trapezoid(signal_values - baseline_values, axis_values))

        if ax is not None:
            axis_limit = self.axis_annotation.limit
            axis_margin = self.axis_annotation.margin
            value_limit = self.value_annotation.limit
            value_margin = self.value_annotation.margin
            assert axis_limit is not None, "Axis limit is not set"
            assert axis_margin is not None, "Axis margin is not set"
            assert value_limit is not None, "Value limit is not set"
            assert value_margin is not None, "Value margin is not set"

            ax.fill_between(
                self.rescale(axis_values, axis_limit, axis_margin),
                self.rescale(baseline_values, value_limit, value_margin),
                self.rescale(signal_values, value_limit, value_margin),
                **fill_kwargs,
            )
            vline_kwargs = {}
            for fill_key, line_key in (
                ("color", "colors"),
                ("linestyle", "linestyles"),
                ("linewidth", "linewidths"),
                ("alpha", "alpha"),
            ):
                if fill_key in fill_kwargs:
                    vline_kwargs[line_key] = fill_kwargs[fill_key]
            ax.vlines(
                self.rescale(np.asarray([start, end], dtype=float), axis_limit, axis_margin),
                0,
                1,
                **vline_kwargs,
            )

        return peak_area


class ContinuousSignal1D_Process(ContinuousSignal1D_Base):

    def clean_by_moving_average(self, z_threshold=3):
        """
        Remove outliers from the signal using z-score method.
        The z_threshold parameter is the threshold for z-score to identify outliers.
        """
        mean = self.value.mean()
        std = self.value.std()
        z_scores = (self.value - mean) / std
        self.data = self.data[abs(z_scores) < z_threshold].reset_index(drop=True)

    def filter_by_moving_average(self, window: int):
        """
        Signal filtering with the moving average method.

        The window parameter is the number of points to be averaged. Both the
        values and the axis are convolved with the same ``window``-point boxcar
        (``mode="valid"``), so the filtered axis is the mean axis of every
        window and the filtered length is ``len(self) - window + 1``. A
        ``value_std`` column, when present, is filtered the same way.
        """

        if window < 1:
            raise ValueError("Window size should be at least 1")
        if window > len(self.data):
            raise ValueError(
                f"Window size ({window}) should not exceed the number of data "
                f"points ({len(self.data)})"
            )
        weights = np.ones(window) / window
        new_axis = np.convolve(np.asarray(self.axis, dtype=float), weights, mode="valid")
        new_value = np.convolve(
            np.asarray(self.data.iloc[:, 1], dtype=float), weights, mode="valid"
        )
        columns = list(self.data.columns)
        new_data = pd.DataFrame({columns[0]: new_axis, columns[1]: new_value})
        if self.value_std is not None:
            new_std = np.convolve(
                np.asarray(self.value_std, dtype=float), weights, mode="valid"
            )
            new_data[columns[2]] = new_std
        self.data = new_data


@dataclass
class ContinuousSignal1D(ContinuousSignal1D_Process):
    pass


@dataclass
class DiscreteSignal1D(Signal1D):
    """
    DiscreteSignal1D represents a Signal1D with continuous axis but discrete value.
    """

    @classmethod
    def from_data(
        cls,
        data: pd.DataFrame,
        name: str,
        axis_name=None,
        axis_unit=None,
        value_name=None,
        value_unit=None,
        detect_axis_name_and_unit=False,
        detect_value_name_and_unit=False,
    ):
        """
        Given a dataframe with two/three columns, create a Signal1D object.
        """
        if detect_axis_name_and_unit:
            axis_name_temp, axis_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[0]
            )
        else:
            axis_name_temp = data.columns[0]
            axis_unit_temp = None
        if not axis_name and axis_name_temp:
            axis_name = axis_name_temp
        if not axis_unit and axis_unit_temp:
            axis_unit = axis_unit_temp

        if detect_value_name_and_unit:
            value_name_temp, value_unit_temp = cls.get_type_and_unit_from_header(
                data.columns[1]
            )
        else:
            value_name_temp = data.columns[1]
            value_unit_temp = None
        if not value_name and value_name_temp:
            value_name = value_name_temp
        if not value_unit and value_unit_temp:
            value_unit = value_unit_temp

        description_annotations = [
            ContDescAnno(
                name=axis_name,
                unit=axis_unit,
                limit=(
                    (min(data.iloc[:, 0]), max(data.iloc[:, 0]))
                    if len(data) > 0
                    else (0, 1)
                ),
                margin=(0, 1),
            ),
            DescAnno(
                name=value_name,
                unit=value_unit,
            ),
        ]
        res = cls(data=data, name=name, description_annotations=description_annotations)
        res.update_data_headers()
        return res

    @classmethod
    def from_csv(
        cls,
        path,
        name=None,
        detect_axis_name_and_unit=True,
        detect_value_name_and_unit=False,
        axis_name=None,
        axis_unit=None,
        value_name="Fraction",
        value_unit=None,
        **kwargs,
    ):
        return super().from_csv(
            path,
            name,
            detect_axis_name_and_unit=detect_axis_name_and_unit,
            detect_value_name_and_unit=detect_value_name_and_unit,
            axis_name=axis_name,
            axis_unit=axis_unit,
            value_name=value_name,
            value_unit=value_unit,
            **kwargs,
        )

    # def __init__(
    #     self,
    #     data,
    #     name,
    #     axis_name=None,
    #     axis_unit=None,
    #     value_name=None,
    #     value_unit=None,
    #     update="to_data",
    #     detect_axis_name_and_unit=False,
    #     detect_value_name_and_unit=False,
    # ):
    #     super().__init__(
    #         data=data,
    #         name=name,
    #         axis_name=axis_name,
    #         axis_unit=axis_unit,
    #         value_name=value_name,
    #         value_unit=value_unit,
    #         update=update,
    #         detect_axis_name_and_unit=detect_axis_name_and_unit,
    #         detect_value_name_and_unit=detect_value_name_and_unit,
    #     )
    #     self.description_annotations = [
    #         ContDescAnno(
    #             self.get_axis_name(),
    #             self.get_axis_unit(),
    #             (self.get_axis().min(), self.get_axis().max()),
    #             10,
    #         ),
    #         DiscDescAnno(self.get_value_name(), self.get_value_unit()),
    #     ]
    #     self.arrowprops = {}

    def plot_at(
        self, ax: plt.Axes, label=None, text_shift=(0, 0), mark_height=0.5, **kwargs
    ):
        """
        Plot the signal at the given ax and return an artist handle.
        You can provide extra arguments to the plot function by **kwargs. Available arguments are listed below:
        - color: str
        - linewidth: float
        - linestyle: str
        - label: str
        - alpha: float
        - marker: str
        - horizontalalignment: center | right | left
        - verticalalignment: center | top | bottom
        """
        if not label:
            label = self.name

        kwargs_for_annotate = kwargs.copy()
        if not "rotation" in kwargs_for_annotate.keys():
            kwargs_for_annotate["rotation"] = 90
        if not "fontsize" in kwargs_for_annotate.keys():
            kwargs_for_annotate["fontsize"] = 10

        kwargs_for_Line2D = kwargs.copy()
        kwargs_for_Line2D.pop("rotation", None)
        kwargs_for_Line2D.pop("fontsize", None)
        kwargs_for_Line2D.pop("mode", None)

        kwargs_for_annotate.pop("mode", None)
        axis_to_plot = transform_utils.rescale_to_0_1(
            self.axis, self.axis_annotation.limit[0], self.axis_annotation.limit[1]
        )
        ax.vlines(
            axis_to_plot, 0, mark_height, linestyles="dashed", **kwargs_for_Line2D
        )
        for axis, value in zip(axis_to_plot, self.value):
            ax.annotate(
                f"{value}",
                xy=(axis, mark_height),
                xytext=(axis + text_shift[0], 0.5 + text_shift[1]),
                ha="center",
                **kwargs_for_annotate,
            )

        handle = plt.Line2D(
            [0], [0], label=label, **kwargs_for_Line2D
        )  # Generate a virtual handle for legend
        return handle

    def set_arrowprops(self, arrowprops):
        """
        Set the arrowprops for annotations. See ax.annotate for supported arrowprops
        """
        self.arrowprops = arrowprops


@dataclass
class SegmentedSignal1D(Signal1D):

    # def __init__(self, **kwargs):
    #     """
    #     A segmented signal 1d should look like\n
    #     Axis,Values,Segment,Others\n
    #     0.2,0.2,1,1\n
    #     0.22,0.3,1,2\n
    #     ...\n
    #     0.4,0.4,1,9\n
    #     0.38,0.38,2,10\n
    #     ...\n
    #     """

    #     self.active_segments = "all"

    def get_segment_num(self):
        return set(self.data["Segment"])

    def get_active_segments(self):
        return self.active_segments

    def get_indices_for_segments(self, segments):
        if segments == "all":
            return self.data.index
        elif isinstance(segments, int):
            return self.data.index[self.data["Segment"] == segments]
        elif isinstance(segments, list):
            return self.data.index[self.data["Segment"].isin(segments)]
        else:
            raise ValueError(
                f"Segments should be 'all', int or list of int, but got {segments}, which is {type(segments)}"
            )

    def get_indices_for_active_segments(self):
        return self.get_indices_for_segments(self.get_active_segments())

    def set_active_segments(self, segments):
        if isinstance(segments, str):
            if segments != "all":
                raise ValueError("segments should be 'all', int or list of int")
        elif isinstance(segments, int):
            if segments < 0 or segments > max(self.data["Segment"]):
                raise ValueError(
                    "segments should be positive int and less than the max segment number"
                )
        elif isinstance(segments, list):
            if any([x < 0 or x > max(self.data["Segment"]) for x in segments]):
                raise ValueError(
                    "segments should be positive int and less than the max segment number"
                )
        else:
            raise ValueError("segments should be 'all', int or list of int")
        self.active_segments = segments

    def get_data_for_segments(self, segments):
        # return self.data.loc[]
        if segments == "all":
            return self.data
        elif isinstance(segments, int):
            return self.data[self.data["Segment"] == segments]
        elif isinstance(segments, list):
            return self.data[self.data["Segment"].isin(segments)]
        else:
            raise ValueError(
                f"Segments should be 'all', int or list of int, but got {segments}, which is {type(segments)}"
            )

    def get_data_for_active_segments(self):
        return self.get_data_for_segments(self.get_active_segments())

    def get_series_for_segements(self, segments, i):
        """
        i = 0 for axis, i = 1 for values
        """
        segement_data = self.get_data_for_segments(segments)
        return segement_data.iloc[:, i]

    def get_axis_for_segments(self, segments):
        return self.get_series_for_segements(segments, 0)

    def get_values_for_segments(self, segments):
        return self.get_series_for_segements(segments, 1)

    def get_series_for_active_segments(self, i):
        """
        i = 0 for axis, i = 1 for values
        """
        return self.get_series_for_segements(self.get_active_segments(), i)

    def get_axis_for_active_segments(self):
        return self.get_series_for_active_segments(0)

    def get_values_for_active_segments(self):
        return self.get_series_for_active_segments(1)

    def plot(self, ax: plt.Axes, color="C0"):

        def pplot(data):
            ax.plot(
                (data["Potential (V)"] - self.get_voltage_limit()[0])
                / (self.get_voltage_limit()[1] - self.get_voltage_limit()[0]),
                (data["Current (A)"] - self.get_current_limit()[0])
                / (self.get_current_limit()[1] - self.get_current_limit()[0]),
                label=self.name,
                color=color,
            )

        if self.active_segments == "all":
            pplot(self.data)
        elif isinstance(self.active_segments, int):
            segment_data = self.data[self.data["Segment"] == self.active_segments]
            pplot(segment_data)
        elif isinstance(self.active_segments, list):
            segment_data = self.data[self.data["Segment"].isin(self.active_segments)]
            pplot(segment_data)
        else:
            raise ValueError(
                f"Segments should be 'all', int or list of int, but got {self.active_segments}, which is {type(self.active_segments)}"
            )


@dataclass
class SegmentedContinuousSignal1D(SegmentedSignal1D, ContinuousSignal1D):

    # def __init__(
    #     self,
    #     data,
    #     name,
    #     axis_name=None,
    #     axis_unit=None,
    #     value_name=None,
    #     value_unit=None,
    #     update="to_data",
    #     detect_axis_name_and_unit=False,
    #     detect_value_name_and_unit=False,
    #     axis_limit=None,
    #     axis_margin=(0.1, 0.1),
    #     axis_digits=11,
    #     value_limit=None,
    #     value_margin=(0.1, 0.1),
    #     value_digits=11,
    # ):
    #     # print(axis_margin)
    #     # print(value_margin)
    #     ContinuousSignal1D.__init__(
    #         self,
    #         data=data,
    #         name=name,
    #         axis_name=axis_name,
    #         axis_unit=axis_unit,
    #         value_name=value_name,
    #         value_unit=value_unit,
    #         update=update,
    #         detect_axis_name_and_unit=detect_axis_name_and_unit,
    #         detect_value_name_and_unit=detect_value_name_and_unit,
    #         axis_limit=axis_limit,
    #         axis_margin=axis_margin,
    #         value_limit=value_limit,
    #         value_margin=value_margin,
    #     )
    #     SegmentedSignal1D.__init__(self)

    def set_active_segments(self, segments, update_value_limit=True):
        res = super().set_active_segments(segments)
        if update_value_limit:
            self.set_default_relative_value_limit()

    def set_default_relative_value_limit(self):
        segment_indices = self.get_indices_for_active_segments()
        axis_indices = self.get_indices_for_current_axis_limit()
        indices = list(set(segment_indices) & set(axis_indices))
        indices.sort()
        my_data = self.data.loc[indices, :]
        value_limit = (my_data.iloc[:, 1].min(), my_data.iloc[:, 1].max())
        self.description_annotations[1].set_limit(value_limit)

    def set_default_limit_and_margin(self):
        # 分析 signal 的 axis 与 value 范围, 设定 axis 和 value 的默认范围

        segment_data = self.get_data_for_active_segments()

        axis_limit = (min(segment_data.iloc[:, 0]), max(segment_data.iloc[:, 0]))
        value_limit = (min(segment_data.iloc[:, 1]), max(segment_data.iloc[:, 1]))
        self.description_annotations[0].set_limit(axis_limit)
        self.description_annotations[1].set_limit(value_limit)

    def plot_at(self, ax: plt.Axes, **kwargs):
        """
        Plot the signal at the given ax and return an artist handle.
        You can provide extra arguments to the plot function by **kwargs. Available arguments are listed below:
        - color: str
        - linewidth: float
        - linestyle: str
        - label: str
        - alpha: float
        - marker: str
        - horizontalalignment: center | right | left
        - verticalalignment: center | top | bottom
        """
        kwargs.pop("text_shift", None)
        label = kwargs.pop("label", None)
        if not label:
            label = self.name

        kwargs_for_annotate = kwargs.copy()
        kwargs_for_Line2D = kwargs.copy()

        kwargs_for_Line2D.pop("fontsize", None)
        kwargs_for_Line2D.pop("rotation", None)
        kwargs_for_Line2D.pop("mode", None)

        (handle,) = ax.plot(
            self.rescale(
                self.get_axis_for_active_segments(),
                self.get_axis_limit(),
                self.get_axis_margin(),
            ),
            self.rescale(
                self.get_values_for_active_segments(),
                self.get_value_limit(),
                self.get_value_margin(),
            ),
            label=label,
            **kwargs_for_Line2D,
        )
        return handle


@dataclass
class FractionSignal(DiscreteSignal1D):
    @classmethod
    def from_csv(
        cls,
        path,
        name=None,
        detect_axis_name_and_unit=True,
        detect_value_name_and_unit=False,
        axis_name=None,
        axis_unit=None,
        value_name="Fraction",
        value_unit=None,
        **kwargs,
    ):
        return super().from_csv(
            path=path,
            name=name,
            detect_axis_name_and_unit=detect_axis_name_and_unit,
            detect_value_name_and_unit=detect_value_name_and_unit,
            axis_name=axis_name,
            axis_unit=axis_unit,
            value_name=value_name,
            value_unit=value_unit,
            **kwargs,
        )

    # def __init__(
    #     self,
    #     data,
    #     name,
    #     axis_name=None,
    #     axis_unit=None,
    #     value_name="Fraction",
    #     value_unit=None,
    #     update="to_data",
    #     detect_axis_name_and_unit=False,
    #     detect_value_name_and_unit=False,
    # ):
    #     super().__init__(
    #         data=data,
    #         name=name,
    #         axis_name=axis_name,
    #         axis_unit=axis_unit,
    #         update=update,
    #         value_name=value_name,
    #         value_unit=value_unit,
    #         detect_axis_name_and_unit=detect_axis_name_and_unit,
    #         detect_value_name_and_unit=detect_value_name_and_unit,
    #     )
    #     if not axis_unit in chromatographic_units_map_types.keys():
    #         raise ValueError(
    #             f"Expected axis_unit to be one of {chromatographic_units_map_types.keys()}, but got {axis_unit}"
    #         )

    #     if axis_name == "undefined":
    #         self.set_axis_name(chromatographic_units_map_types[axis_unit])
