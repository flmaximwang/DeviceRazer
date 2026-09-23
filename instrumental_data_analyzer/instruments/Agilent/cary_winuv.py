"""
``instruments.Agilent.cary_winuv`` --- Agilent Cary WinUV 紫外-可见光谱数据解析
================================================================================

解析 Agilent Cary WinUV (Cary 100 / 300 等) "Scan" 导出的 ``.csv`` 文件,
把文件内的多条光谱读成一个 :class:`CaryAbsSpecCollection`:

- :class:`CaryAbsSpec` : 单条吸收光谱 (``AbsorbSpec``) + 该次扫描的元数据
- :class:`CaryAbsSpecCollection` : :meth:`CaryAbsSpecCollection.from_csv` 读取导出文件

导出文件结构 (以 Pyridine Hemochrome Assay 的实测导出为参考)::

    <样品 1>,,<样品 2>,,...                        ← 第 1 行: 光谱名 (每条光谱占 2 列)
    Wavelength (nm),Abs,Wavelength (nm),Abs,...    ← 第 2 行: 列名
    600,0.148074612,600,0.02556228451,...          ← 数据段: (波长, 吸光度) 交替排列,
    ...                                             波长由 Start (nm) 递减到 Stop (nm)
    500,0.1624793112,500,0.1937115341,...
                                                   ← 空行
    <样品 1>,                                      ← 之后每条光谱一个元数据块
    <样品 1>
    Collection Time: 2026/9/23 14:31:09
    Scan Software Version: 4.20(468)
    Parameter List :
    Instrument                        Cary 100
    Start (nm)                        600.00
    ...
    Method Log     :
    Method Name    : E:\\s642\\20260923\\260923.MSW
    ...
    End Method Modifications
    [Time] , 3.033
    <SBW (nm)> , 1.00
    ...

使用示例::

    from instrumental_data_analyzer.instruments.Agilent.cary_winuv import (
        CaryAbsSpecCollection,
    )

    collection = CaryAbsSpecCollection.from_csv("5705.csv")
    collection.signal_names                                # 8 条光谱
    collection["5705-ox1_1"].collection_time               # '2026/9/23 14:31:09'
    collection["5705-ox1_1"].metadata["UV-Vis SBW (nm)"]   # '1.0'
    collection.value_annotation.label                      # '10-mm Absorbance'
    collection.set_default_annotations()
    fig, ax = collection.plot()

吸光度列按比色皿光程标注: ``from_csv(..., optical_path_length_mm=1)`` 得到
``1-mm Absorbance`` (默认 10 mm), 该参数只影响标注, 不对数据做换算。

每条光谱读入后波长轴统一存为**升序** (导出文件本身是 Start → Stop 递减): 库内
``__getitem__`` / ``get_peak_between`` / ``slice_value_by_axis`` / 差谱等按轴取值的
运算都建立在轴升序的前提上 (``np.interp`` 要求 ``xp`` 升序), 降序轴会让它们静默返回错值。
"""

import csv
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ...abstract.display import Signal1DPlotArgs
from ...concrete.spectroscopy import AbsorbSpec, AbsorbSpecCollection


# ============================== 文件解析工具 ==============================


def _read_text_lines(csv_path: Path) -> list[str]:
    """
    读取导出文件的所有行 (兼容 UTF-8 与 UTF-16 导出, 兼容 CRLF/LF 换行)。
    """
    raw = csv_path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-16-le")
    return text.splitlines()


def _split_fields(line: str) -> list[str]:
    """
    按 CSV 规则切分一行, 返回字段列表。
    """
    return next(csv.reader([line]))


def _split_key_value(line: str) -> tuple[str | None, str | None]:
    """
    切分元数据块中的一行 key-value, 支持三种书写方式::

        Collection Time: 2026/9/23 14:31:09      → ("Collection Time", "2026/9/23 14:31:09")
        Instrument                        Cary 100   → ("Instrument", "Cary 100")
        <Cycle Time> , 0:46                       → ("<Cycle Time>", "0:46")

    无法识别为 key-value 时返回 ``(None, None)``。
    """
    comma_index = line.find(" ,")
    colon_index = line.find(":")
    if comma_index != -1 and (colon_index == -1 or comma_index < colon_index):
        # " , " 分隔 (元数据块末尾的 [Time] / <SBW (nm)> 等), 值本身可能含 ":"
        key, _, value = line.partition(" ,")
        return key.strip(), value.strip()
    if colon_index != -1:
        key, _, value = line.partition(":")
        return key.strip(), value.strip()
    parts = re.split(r"\s{2,}", line, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def _parse_metadata(block_lines: list[str]) -> dict[str, Any]:
    """
    解析一条光谱的元数据块, 返回 ``{key: value}``。

    - ``Parameter List`` / ``Method Log`` 里的 key-value 按原 key 存入;
    - ``Comments`` 与 ``Method Modifications`` 为自由文本, 分别存成
      ``metadata["Comments"]`` / ``metadata["Method Modifications"]`` 字符串列表。
    """
    metadata: dict[str, Any] = {}
    comments: list[str] = []
    modifications: list[str] = []
    section = None
    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "Comments":
            section = "comments"
            continue
        if stripped.startswith("Parameter List"):
            section = "parameters"
            continue
        if stripped.startswith("Method Log"):
            section = "method_log"
            continue
        if stripped.startswith("Method Modifications"):
            section = "method_modifications"
            continue
        if stripped.startswith("End Method Modifications"):
            section = "trailer"
            continue
        if section == "comments":
            comments.append(stripped)
            continue
        if section == "method_modifications":
            modifications.append(stripped)
            continue
        key, value = _split_key_value(stripped)
        if key is not None:
            metadata[key] = value
    if comments:
        metadata["Comments"] = comments
    if modifications:
        metadata["Method Modifications"] = modifications
    return metadata


def _is_block_start(lines: list[str], index: int, spectrum_names: set[str]) -> bool:
    """
    判断 ``lines[index]`` 是否为一条光谱元数据块的起始行。

    起始行形如 ``<光谱名>,`` 且紧随其后的一行是 ``<光谱名>``。
    数据段之后的 ``Saved as E:\\\\...`` 等自由文本行不会与之混淆。
    """
    if index + 1 >= len(lines):
        return False
    fields = _split_fields(lines[index])
    first_field = fields[0].strip() if fields else ""
    return (
        first_field in spectrum_names
        and all(not field.strip() for field in fields[1:])
        and lines[index + 1].strip() == first_field
    )


def _parse_metadata_blocks(
    lines: list[str], start_index: int, spectrum_names: list[str]
) -> list[tuple[str, dict[str, Any]]]:
    """
    解析数据段之后的全部元数据块, 按文件出现顺序返回
    ``[(光谱名, metadata), ...]``。
    """
    names_set = set(spectrum_names)
    blocks: list[tuple[str, dict[str, Any]]] = []
    index = start_index
    while index < len(lines):
        if not _is_block_start(lines, index, names_set):
            index += 1
            continue
        block_name = _split_fields(lines[index])[0].strip()
        # 块内容: 从块内的 <光谱名> 行之后, 到下一个块起始行之前
        content: list[str] = []
        next_index = index + 2
        while next_index < len(lines) and not _is_block_start(
            lines, next_index, names_set
        ):
            content.append(lines[next_index])
            next_index += 1
        blocks.append((block_name, _parse_metadata(content)))
        index = next_index
    return blocks


# ============================== 信号与集合 ==============================


@dataclass(slots=True)
class CaryAbsSpecPlotArgs(Signal1DPlotArgs):
    ax_size: tuple[float, float] = (8, 6)
    mode: int = 0


@dataclass
class CaryAbsSpec(AbsorbSpec):
    """
    一条 Cary WinUV 吸收光谱, 附带该次扫描的元数据。

    Attributes
    ----------
    metadata : dict[str, Any]
        元数据块解析结果, 例如 ``metadata["Instrument"]`` == ``"Cary 100"``,
        ``metadata["UV-Vis SBW (nm)"]`` == ``"1.0"``,
        ``metadata["Start (nm)"]`` == ``"600.00"``;
        ``Comments`` 与 ``Method Modifications`` 为字符串列表。
    """

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def collection_time(self) -> str | None:
        """该次扫描的采集时间 (Collection Time)。"""
        return self.metadata.get("Collection Time")

    @property
    def instrument(self) -> str | None:
        """仪器型号 (Instrument), 如 ``"Cary 100"``。"""
        return self.metadata.get("Instrument")


@dataclass
class CaryAbsSpecCollection(AbsorbSpecCollection):
    """
    Agilent Cary WinUV 导出文件中的一组吸收光谱。

    通过 :meth:`from_csv` 读取一个 "Scan" 导出 ``.csv``;
    每条光谱的元数据挂在 :class:`CaryAbsSpec` 上, 也可用 :attr:`metadata` 一次性取出。
    """

    signal_type: type = CaryAbsSpec
    plot_args: Signal1DPlotArgs = field(default_factory=CaryAbsSpecPlotArgs)
    #: 比色皿光程 (mm), 由 :meth:`from_csv` 传入, 用于标注吸光度列
    optical_path_length_mm: float = 10

    @property
    def metadata(self) -> dict[str, dict[str, Any]]:
        """``{光谱名: 该光谱的元数据字典}``。"""
        return {signal.name: signal.metadata for signal in self.signals}

    @classmethod
    def from_csv(
        cls,
        csv_path: str | Path,
        name: str | None = None,
        optical_path_length_mm: float = 10,
    ) -> "CaryAbsSpecCollection":
        """
        读取一个 Cary WinUV "Scan" 导出 ``.csv`` 文件。

        Parameters
        ----------
        csv_path : str | Path
            导出文件路径。
        name : str, optional
            集合名称, 默认取文件名 (不含扩展名)。
        optical_path_length_mm : float, default 10
            比色皿光程 (mm), 只用于标注吸光度列 (``10`` → ``10-mm Absorbance``,
            ``1`` → ``1-mm Absorbance``), **不**对数据做换算。

        Returns
        -------
        CaryAbsSpecCollection
            文件内的全部光谱; 波长轴标注为 ``Wavelength (nm)``,
            吸光度标注为 ``<光程>-mm Absorbance``
            (导出文件中的 ``Abs`` 列, 无单位)。
        """
        if optical_path_length_mm <= 0:
            raise ValueError(
                f"optical_path_length_mm should be > 0, got {optical_path_length_mm}"
            )
        value_name = f"{optical_path_length_mm:g}-mm Absorbance"
        csv_path = Path(csv_path)
        if not csv_path.is_file():
            raise ValueError(f"File {csv_path} does not exist or is not a file")
        lines = _read_text_lines(csv_path)
        if len(lines) < 3:
            raise ValueError(f"File {csv_path} is too short to be a Cary WinUV export")

        spectrum_names, column_headers = _parse_header(lines)
        data_rows, data_end = _parse_data_section(lines, 2, len(spectrum_names))
        if not data_rows:
            raise ValueError(f"No data rows found in {csv_path}")

        axis_label, value_label = column_headers[0], column_headers[1]
        spectra: list[CaryAbsSpec] = []
        for i, spectrum_name in enumerate(spectrum_names):
            data, missing = _parse_spectrum(data_rows, i, axis_label, value_label)
            if data.empty:
                warnings.warn(
                    f"{csv_path.name}: spectrum '{spectrum_name}' has no data, skipped"
                )
                continue
            if missing:
                warnings.warn(
                    f"{csv_path.name}: spectrum '{spectrum_name}' has {missing} "
                    "missing data point(s) (blank cells in the export), dropped"
                )
            spectra.append(
                CaryAbsSpec.from_data(
                    data=data,
                    detect_axis_name_and_unit=True,
                    value_name=value_name,
                    value_unit=None,
                    name=spectrum_name,
                )
            )
        if not spectra:
            raise ValueError(f"No spectrum data found in {csv_path}")

        _attach_metadata(spectra, lines, data_end, csv_path)
        _deduplicate_names(spectra)

        collection = cls.from_similar_signals(
            spectra, name=csv_path.stem if name is None else name
        )
        collection.optical_path_length_mm = optical_path_length_mm
        return collection


# ============================== 解析步骤 ==============================


def _parse_header(lines: list[str]) -> tuple[list[str], list[str]]:
    """
    解析文件头两行, 返回 ``(光谱名列表, 列名列表)``。
    """
    name_fields = _split_fields(lines[0])
    spectrum_names = [
        name_fields[2 * i].strip() for i in range(len(name_fields) // 2)
    ]
    while spectrum_names and not spectrum_names[-1]:
        # 表头常以 ",," 结尾, 去掉末尾空名
        spectrum_names.pop()
    if not spectrum_names:
        raise ValueError("No spectrum name found in the header of the export file")
    if any(not spectrum_name for spectrum_name in spectrum_names):
        raise ValueError(
            "Malformed header: spectrum names should occupy every other column, "
            f"got {name_fields}"
        )
    column_headers = _split_fields(lines[1])
    if len(column_headers) < 2:
        raise ValueError(
            f"Malformed column header line, expected at least 2 columns: {lines[1]!r}"
        )
    try:
        float(column_headers[0])
    except ValueError:
        pass
    else:
        raise ValueError(
            "Not a Cary WinUV export: line 2 should hold the column names "
            f"(like 'Wavelength (nm),Abs'), got {lines[1]!r}"
        )
    return spectrum_names, column_headers


def _parse_data_section(
    lines: list[str], start_index: int, spectrum_count: int
) -> tuple[list[list[str]], int]:
    """
    解析数据段, 返回 ``(数据行列表, 数据段结束行号)``。

    数据段从 ``lines[start_index]`` 开始, 到第一个空行或第一个非数值行为止
    (其后即为各光谱的元数据块)。
    """
    data_rows: list[list[str]] = []
    data_end = start_index
    for index in range(start_index, len(lines)):
        fields = _split_fields(lines[index])
        if not fields or not fields[0].strip():
            data_end = index
            break
        try:
            float(fields[0])
        except ValueError:
            data_end = index
            break
        if len(fields) < 2 * spectrum_count:
            raise ValueError(
                f"Data row {index + 1} has {len(fields)} fields, expected at least "
                f"{2 * spectrum_count} for {spectrum_count} spectra"
            )
        data_rows.append(fields)
    else:
        data_end = len(lines)
    return data_rows, data_end


def _parse_spectrum(
    data_rows: list[list[str]],
    index: int,
    axis_label: str,
    value_label: str,
) -> tuple[pd.DataFrame, int]:
    """
    取第 *index* 条光谱的数据, 返回 ``(DataFrame, 被丢弃的空数据点个数)``。

    Cary 在扫描中断 / 覆盖保存时会在导出文件里留下空白单元格
    (如 49_8.csv 中的第一条 49.8-ox-1_1 只测到 510 nm), 这些空白点被丢弃并计数,
    以免 NaN 进入后续的插值 / 加减运算。

    返回的 DataFrame 按波长**升序**排列: WinUV 的扫描是 Start (nm) 递减到
    Stop (nm), 而库内按轴取值的运算 (``np.interp`` / :meth:`get_peak_between` /
    差谱) 都假定轴升序, 降序轴会让它们静默返回错值。
    """
    axis_values: list[float] = []
    values: list[float] = []
    missing = 0
    for row in data_rows:
        axis_cell = row[2 * index].strip() if len(row) > 2 * index else ""
        value_cell = row[2 * index + 1].strip() if len(row) > 2 * index + 1 else ""
        if not axis_cell or not value_cell:
            missing += 1
            continue
        axis_values.append(float(axis_cell))
        values.append(float(value_cell))
    frame = pd.DataFrame({axis_label: axis_values, value_label: values})
    frame = frame.sort_values(axis_label, kind="stable").reset_index(drop=True)
    return frame, missing


def _deduplicate_names(spectra: list[CaryAbsSpec]) -> None:
    """
    同名光谱 (Cary 允许覆盖保存同名文件, 导出里会出现两条同名光谱) 依次加
    ``(1)``, ``(2)`` ... 后缀, 与 ``Nanodrop2000Workbook.from_tsv`` 的处理一致。
    """
    used: set[str] = set()
    for spectrum in spectra:
        if spectrum.name in used:
            counter = 1
            while f"{spectrum.name}({counter})" in used:
                counter += 1
            spectrum.name = f"{spectrum.name}({counter})"
        used.add(spectrum.name)


def _attach_metadata(
    spectra: list[CaryAbsSpec],
    lines: list[str],
    data_end: int,
    csv_path: Path,
) -> None:
    """
    把元数据块挂到对应的光谱上。

    正常情况下元数据块与光谱一一对应, 按文件顺序匹配;
    数量不一致时退化为按光谱名匹配并给出警告。
    """
    blocks = _parse_metadata_blocks(lines, data_end, [s.name for s in spectra])
    if len(blocks) == len(spectra):
        for spectrum, (_, metadata) in zip(spectra, blocks):
            spectrum.metadata = metadata
        return
    if not blocks:
        return
    warnings.warn(
        f"{csv_path.name}: found {len(blocks)} metadata blocks for "
        f"{len(spectra)} spectra; metadata is matched by spectrum name"
    )
    remaining: dict[str, list[dict[str, Any]]] = {}
    for block_name, metadata in blocks:
        remaining.setdefault(block_name, []).append(metadata)
    for spectrum in spectra:
        if remaining.get(spectrum.name):
            spectrum.metadata = remaining[spectrum.name].pop(0)
