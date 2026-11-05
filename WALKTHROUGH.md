# DVRazer 核心架构走读 —— 从数据模型到仪器解析

*2026-10-04T01:54:00Z by Showboat 0.6.1*
<!-- showboat-id: a6456b6e-1f0d-43ec-b8b8-38c105536350 -->

## 0. 这个库在做什么

DVRazer（包名 `dvrazer`）是一个**仪器数据处理库**。它把不同厂商仪器导出的原始文件统一成同一套数据模型，再在这套模型上做绘图、插值、峰检测、区域积分等分析。它要化解的核心矛盾是：**每家仪器的格式与物理含义都不同，但分析逻辑是共通的**——所以它把"数据"和"数据的物理含义"绑成一个对象，让上层分析不必再关心数据来自哪台仪器。

```bash
sed -n '1,8p' README.md
```

```output
# DVRazer

一个用于处理、分析和可视化各种仪器数据的 Python 库，为科学实验数据提供统一的数据模型和处理框架。

## 功能特性

- **统一数据模型**：通过 `Signal` → `Signal1D` / `Signal2D` → 具体仪器信号的层次化抽象，统一管理所有仪器数据
- **内置描述注释系统**：自动管理数据的物理含义（名称、单位、范围、刻度标签），简化绘图和展示
```

## 1. 三层结构

包内按职责分成四层。`abstract/` 是核心框架（抽象数据模型），`concrete/` 是具体领域的语义化子类（光谱、色谱、动力学……），`instruments/` 是各厂商的解析器，`utils/` 是杂项工具。**依赖方向是单向的**：instruments → concrete → abstract。

```bash
find dvrazer -maxdepth 1 -mindepth 1 -type d -not -name '__pycache__' | sort
```

```output
dvrazer/abstract
dvrazer/concrete
dvrazer/instruments
dvrazer/utils
```

## 2. 描述注释系统：给每个数据维度贴上物理含义

整个框架的第一块基石是 `DescAnno`。它只做一件事：给一个数据列绑定"名称 + 单位"，并用 `label` 属性把它们拼成绘图/导出用的标签（如 `Absorbance (a.u.)`）。注意 `unit` 允许为 `None`——那时 `label` 退化成纯名称，所以"没单位的列"也能自然工作。

```bash
sed -n '42,58p' dvrazer/abstract/signal.py
```

```output
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
```

## 3. 连续维度的刻度和自动小数位

`ContDescAnno` 在 `DescAnno` 之上加了连续维度特有的东西：范围 `limit`、边距 `margin`、刻度间距。最巧妙的是 `ticklabel_space_major` 的 setter——**它按刻度间距自动决定小数点位数**：间距大于 1 用 0 位、大于 0.1 用 1 位，依此类推。这样轴标签的小数位永远刚好够用，而不用人手调。`ticklabels` 则从 `ticklabel_floor` 开始按间距递推到上限，再按位数格式化成字符串。

```bash
sed -n '121,141p' dvrazer/abstract/signal.py
```

```output
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
```

## 4. Signal 基类：一切数据的根

`Signal` 是所有数据类型的根。它的全部状态就三样：一个 `pandas.DataFrame`（`data`）、一个名字（`name`）、以及一个与 DataFrame 列一一对应的注释列表（`description_annotations`）。**数据是表，含义是列上的注释**——这个设计让"加一个维度"和"给这一维命名/配单位"变成两个正交的动作。基类本身只提供最通用的能力：从 CSV 读写、线性缩放。

```bash
sed -n '199,219p' dvrazer/abstract/signal.py
```

```output
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
```

## 5. Signal1D：把"第一列是轴、第二列是值"固化成约定

`Signal1D` 是使用最多的类型：约定第 0 列是连续轴（波长、时间、体积……），第 1 列是测量值。类体顶端的两行类属性 `axis_annotation_type` / `value_annotation_type` 是关键——**子类通过覆盖它们来收紧类型约束**（例如连续信号的轴必须是 `ContDescAnno`）。这样类型检查是声明式的，不需要在每个方法里写判断。

```bash
sed -n '172,195p' dvrazer/abstract/signal_1d.py
```

```output
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
```

## 6. axis / value 属性：把列访问包装成领域语言

`axis` 和 `value` 两个 property 把 `data.iloc[:, 0]` / `data.iloc[:, 1]` 藏起来，让调用方写的是 `sig.value` 而不是列号。它们各自还有 setter，写回时按列**名**赋值而不是按位置，所以注释更新后列名变化也不会写错列。`axis_annotation` / `value_annotation` 同理，只是作用在注释列表上。

```bash
sed -n '197,229p' dvrazer/abstract/signal_1d.py
```

```output
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
```

## 7. _Interpolate：一个既能插值、又能当数组用的视图

这是整个库里最精巧的一处。`_Interpolate` 让 `sig.value` 同时具备两种身份：按轴取值时走 `np.interp` 做线性插值（`sig.value[283.5]` 直接给出该波长处的值），按数组用时走 `__array__` / `__len__` / `__iter__` 以及一整套算术运算符。所以**新增插值能力没有破坏任何既有代码**——老代码依然把 `value` 当 numpy 数组用。`_as_axis_values` 还额外把 `slice` 重新解释成"轴范围"（`interp[280:283]` 表示轴上的 280、281、282），这是为谱图按波长切片专门做的。

```bash
sed -n '59,84p' dvrazer/abstract/signal_1d.py
```

```output
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
```

## 8. SignalCollection：用字典语义管理一组信号

单条信号之外，最常见的就是"一组要对比的信号"（多次进样、多个样品）。`SignalCollection` 让集合表现得像一个**按名字索引的字典**：`coll[signal_name]` 取信号，`keys()` 列出名字。底层仍是 `list[Signal]`，但用 `__index_cache__` 把名字到下标的映射缓存起来，避免每次查找都做线性扫描。

```bash
sed -n '24,53p' dvrazer/abstract/signal_collection.py
```

```output
@dataclass
class SignalCollection:
    """
    A SignalCollection contains multiple signals and is designed to
    easily compare and visualize them.

    - Dimensions of signals in a signal collection must be the same.
    - Signals in a collection is stored by a dictionary, you can find every signal with its name like SignalCollection[signal_name]

    Properties
    ----------
    signals: list[Signal]
        A dictionary of signals in the collection, with signal names as keys.
    name: str
        The name of the signal collection.
    plot_args: PlotArgs
        The arguments for plotting the signal collection.
    """

    signals: list[Signal] = None
    signal_type: type = Signal
    visible_signal_names: list[str] = None
    name: str = None
    description_annotations: list[DescAnno] = None
    plot_args: SignalPlotArgs = None
    __index_cache__: dict = None

    @property
    def signal_names(self):
        return [signal.name for signal in self.signals]
```

## 9. concrete 层：一层薄薄的语义别名

`concrete/` 里的类几乎都是空壳——`Spectrum`、`AbsorbSpec` 都只是 `ContinuousSignal1D` 的子类，类体是 `pass`。这不是冗余，而是**把"继承层次"翻译成"领域词汇"**：调用方写 `AbsorbSpec` 而不是 `ContinuousSignal1D[ContDescAnno]`，代码立刻可读，同时未来给某个具体类型加特有行为时，有现成的挂载点。

```bash
sed -n '16,45p' dvrazer/concrete/spectroscopy.py
```

```output
from dataclasses import dataclass, field
from ..abstract import (
    ContinuousSignal1D,
    ContinuousSignal1DCollection,
    ContDescAnno,
)


@dataclass
class Spectrum(ContinuousSignal1D):

    pass


@dataclass
class SpectrumCollection(ContinuousSignal1DCollection):

    pass


@dataclass
class AbsorbSpec(ContinuousSignal1D):

    pass


@dataclass
class AbsorbSpecCollection(ContinuousSignal1DCollection):

    pass
```

## 10. instruments 层：把一个厂商格式对接到这套模型

最后看解析器层的一个最小例子。Multiskan FC 酶标仪导出的 .txt 里，数据前面混着一堆表头，只有带 12 列标题的那一行之后才是真正的数据。`MultiWellPlateFC.from_exported_file` 就干两件事：**逐行扫描找到那行标题当开关（flag），然后把它之后的文本丢给 pandas**，最后用解析出的 DataFrame 构造一个 concrete 类型。整个解析器约 14 行——这正是这套架构的兑现方式：**换成另一台仪器，你只需要改"怎么把文件读成 DataFrame"这一小段，上层的数据模型、绘图、插值能力一行都不用动。**

```bash
sed -n '25,39p' dvrazer/instruments/ThermoFisher/multiscan_fc.py
```

```output
class MultiWellPlateFC(MultiWellPlate):

    @staticmethod
    def from_exported_file(txt_path, name="Default Multi-Scan Fluorescence Collection"):
        with open(txt_path, "r") as f:
            flag = False
            data_txt = ""
            for line in f:
                if not flag and "	1	2	3	4	5	6	7	8	9	10	11	12" in line:
                    flag = True
                if flag:
                    data_txt += line
        my_df = pd.read_csv(io.StringIO(data_txt), sep="\t", index_col=0)

        return MultiWellPlateFC(data=my_df, name=name)
```

## 收尾

一条主线：**抽象层定义"数据 + 含义"的骨架（Signal → Signal1D → SignalCollection），concrete 层给它领域名字，instruments 层负责把各家仪器的原始文件喂进这套骨架。** 想扩展一种新仪器时，你只需要写一个解析器把文件读成 `DataFrame` 并调用某个 concrete 类型的 `from_data`，剩下所有分析和绘图能力都是白送的。

