"""
``instruments.MolecularDevices.softmax_pro`` --- Molecular Devices SoftMax Pro 数据解析
========================================================================================

解析 SoftMax Pro 软件导出的 .txt / .xls 文件 (UTF-16 LE 编码)。

文件格式:
  - 以 ``##BLOCKS=N`` 开头, 包含 N 个 Block
  - 每个 Block 以 ``~End`` 结束
  - 每个 Block 对应一个孔板 (Plate)

支持的读板模式:
  - **Endpoint** : 终点法 → :class:`SoftMaxPro_Plate_Endpoint` (返回 :class:`MultiWellPlate`)
  - **Kinetic** : 动力学法 → :class:`SoftMaxPro_Plate_Kinetic` (返回 :class:`ContinuousSignal1DCollection`)
  - **Spectrum** : 光谱扫描 → :class:`SoftMaxPro_Plate_Spectrum` (返回 :class:`ContinuousSignal1DCollection`)

支持的区块类型:
  - **Plate** 区块 (以 ``Plate:`` 开头): 每次读板的原始数据
  - **Group** 区块 (以 ``Group:`` 开头): 模板中定义的 reduction 组,
    例如 BCA 定量中的标准曲线组 (``Standards``) 和各样品组 → :class:`SoftMaxPro_Group`

数据后处理:
  - :class:`SoftMaxPro_Protocol`: 根据孔位定义拟合标准曲线并反算未知孔浓度
    (标准品组带 ``fit`` key, value 为 ``"linear"`` 时使用线性回归)

使用示例::

    from instrumental_data_analyzer.instruments import SoftMaxPro_Project

    project = SoftMaxPro_Project.read_txt("data.txt")
    # 通过板名称访问
    plate = project["Plate 1"]
    # 通过组名称访问 (例如 BCA 标准曲线组)
    standards = project.group("Standards")
    standards.data  # 标准曲线数据表 (Conc, Value, MeanValue, ...)
    # 后处理: 标准曲线 + 未知孔浓度
    protocol = SoftMaxPro_Protocol([standards_definition, sample_definition])
    protocol.apply(plate)
    protocol.results          # DataFrame: Well, Group, Value, Concentration
    protocol.standard_curve   # matplotlib Figure

支持读板方式:
  - Absorbance (吸光度)
  - Fluorescence (荧光)
  - Luminescence (发光)

使用示例::

    from instrumental_data_analyzer.instruments import SoftMaxPro_Project

    project = SoftMaxPro_Project.read_txt("data.txt")
    # 通过板名称访问
    plate = project["Plate 1"]
    # 动力学数据: 访问每个孔的曲线
    curve = plate["A1"]
    curve.plot_at(ax)
"""

import re, tempfile, warnings
from io import StringIO
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt
from ...abstract.signal import ContDescAnno
from ...abstract.signal_1d import ContinuousSignal1D
from ...abstract.signal_1d_collection import (
    Signal1DCollection,
    ContinuousSignal1DCollection,
)
from ...concrete.multi_well_plates import (
    MultiWellPlateSeries,
    MultiWellPlate,
    PLATE_COL_NAMES,
    PLATE_ROW_NAMES,
)
from ...concrete.kinetics import KineticCurve, KineticCurveCollection


def well_num_to_row_num(well_num: int) -> int:
    if well_num == 6:
        return 2
    elif well_num == 12:
        return 3
    elif well_num == 24:
        return 4
    elif well_num == 48:
        return 6
    elif well_num == 96:
        return 8
    elif well_num == 384:
        return 16
    else:
        raise ValueError("Unsupported plate well number")


def well_num_to_col_num(well_num: int) -> int:
    if well_num == 6:
        return 3
    elif well_num == 12:
        return 4
    elif well_num == 24:
        return 6
    elif well_num == 48:
        return 8
    elif well_num == 96:
        return 12
    elif well_num == 384:
        return 24
    else:
        raise ValueError("Unsupported plate well number")


def time_to_seconds(time: str):
    if "." in time:
        day = int(time.split(".")[0])
        time = time.split(".")[1]
    else:
        day = 0
    h, m, s = map(int, time.split(":"))
    return day * 3600 * 24 + h * 3600 + m * 60 + s


class SoftMaxPro_Plate:
    """
    An object to represent a plate in Molecular Devices SoftMax Pro software. The data is usually organized
    in a specific format, which can be parsed to extract the kinetic or endpoint data for each plate. The extracted
    data is stored as a MultiWellPlate object, which contains the data matrix and the corresponding metadata.
    """

    @staticmethod
    def parse_metadata(text: str) -> dict[str, str]:
        """
        For every plate (block), there is a line of text containing the metadata of the plate, which is organized
        in a specific format. This function parses the metadata line and extracts the relevant information,
        such as plate name, read method, read mode, data type, data point number, duration, interval,
        wavelength number, excitation wavelengths, column start and number, plate well number, emission wavelengths,
        cutoff type and wavelength, flashes per read, PMT gain, row start and number. The extracted information
        is returned as a dictionary.
        """
        components = text.split("\t")
        _ = components.pop(0)  # "Plate:"
        plate_name = components.pop(0)
        _ = components.pop(0)  # A strange number 1.3
        _ = components.pop(0)  # "PlateFormat"
        method = components.pop(0)  # Kinetic, Endpoint, or Spectrum
        mode = components.pop(0)  # Absorbance, Fluorescence, or Luminescence)
        if method == "Kinetic":
            if mode == "Fluorescence":
                read_from_bottom = components.pop(0)
                data_type = components.pop(0)
                assert data_type in [
                    "Raw",
                    "Reduced",
                ], f"Unsupported data type {data_type} for kinetic fluorescence method"
                calibrate = components.pop(0)
                data_point_num = int(components.pop(0))
                duration_seconds = int(components.pop(0))
                interval_seconds = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                wavelength_num = int(components.pop(0))  # Wavelength number
                excitation_wavelengths = list(
                    map(int, components.pop(0).split())
                )  # Excitation wavelengths
                col_start = int(components.pop(0))
                col_num = int(components.pop(0))
                plate_well_num = int(components.pop(0))
                emission_wavelengths = list(
                    map(int, components.pop(0).split())
                )  # Emission wavelengths
                cutoff_type = components.pop(0)  # Cutoff type
                cutoff_wavelength = int(components.pop(0))  # Cutoff wavelength
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                flashes_per_read = int(components.pop(0))  # Flashes per read
                PMT_gain = components.pop(0)  # PMT gain
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                row_start = int(components.pop(0))
                row_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                return {
                    "plate_name": plate_name,
                    "method": method,
                    "mode": mode,
                    "read_from_bottom": read_from_bottom,
                    "calibrate": calibrate,
                    "data_type": data_type,
                    "data_point_num": data_point_num,
                    "duration_seconds": duration_seconds,
                    "interval_seconds": interval_seconds,
                    "wavelength_num": wavelength_num,
                    "excitation_wavelengths": excitation_wavelengths,
                    "col_start": col_start,
                    "col_num": col_num,
                    "plate_well_num": plate_well_num,
                    "emission_wavelengths": emission_wavelengths,
                    "cutoff_type": cutoff_type,
                    "cutoff_wavelength": cutoff_wavelength,
                    "flashes_per_read": flashes_per_read,
                    "PMT_gain": PMT_gain,
                    "row_start": row_start,
                    "row_num": row_num,
                }
            elif mode == "Absorbance":
                data_type = components.pop(0)
                assert data_type in [
                    "Raw",
                    "Reduced",
                ], f"Unsupported data type {data_type} for kinetic absorbance method"
                calibrate = components.pop(0)
                data_point_num = int(components.pop(0))
                duration_seconds = int(components.pop(0))
                interval_seconds = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                wavelength_num = int(components.pop(0))  # Wavelength number
                wavelengths = list(map(int, components.pop(0).split()))  # Wavelengths
                col_start = int(components.pop(0))
                col_num = int(components.pop(0))
                plate_well_num = int(components.pop(0))
                row_start = int(components.pop(0))
                row_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                return {
                    "plate_name": plate_name,
                    "method": method,
                    "mode": mode,
                    "data_type": data_type,
                    "calibrate": calibrate,
                    "data_point_num": data_point_num,
                    "duration_seconds": duration_seconds,
                    "interval_seconds": interval_seconds,
                    "wavelength_num": wavelength_num,
                    "wavelengths": wavelengths,
                    "col_start": col_start,
                    "col_num": col_num,
                    "plate_well_num": plate_well_num,
                    "row_start": row_start,
                    "row_num": row_num,
                }
            else:
                raise ValueError(f"Unsupported read mode {mode} for kinetic method")
        elif method == "Endpoint":
            if mode == "Absorbance":
                data_type = components.pop(0)
                calibrate = components.pop(0)
                data_point_num = int(components.pop(0))
                _ = components.pop(0)
                _ = components.pop(0)
                _ = components.pop(0)
                _ = components.pop(0)
                _ = components.pop(0)
                wavelength_num = components.pop(0)
                wavelengths = list(map(int, components.pop(0).split()))
                col_start = int(components.pop(0))
                col_num = int(components.pop(0))
                plate_well_num = int(components.pop(0))
                row_start = int(components.pop(0))
                row_num = int(components.pop(0))
                _ = components.pop(0)
                return {
                    "plate_name": plate_name,
                    "method": method,
                    "calibrate": calibrate,
                    "data_point_num": data_point_num,
                    "wavelength_num": wavelength_num,
                    "wavelengths": wavelengths,
                    "col_start": col_start,
                    "col_num": col_num,
                    "plate_well_num": plate_well_num,
                    "row_start": row_start,
                    "row_num": row_num,
                }
        elif method == "Spectrum":
            if mode == "Absorbance":
                data_type = components.pop(0)
                assert data_type in [
                    "Raw",
                    "Reduced",
                ], f"Unsupported data type {data_type} for spectrum absorbance method"
                calibrate = components.pop(0)
                data_point_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                wavelength_min = int(components.pop(0))
                wavelength_max = int(components.pop(0))
                wavelength_interval = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                col_start = int(components.pop(0))
                col_num = int(components.pop(0))
                plate_well_num = int(components.pop(0))
                row_start = int(components.pop(0))
                row_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                return {
                    "plate_name": plate_name,
                    "method": method,
                    "mode": mode,
                    "data_type": data_type,
                    "calibrate": calibrate,
                    "data_point_num": data_point_num,
                    "wavelength_min": wavelength_min,
                    "wavelength_max": wavelength_max,
                    "wavelength_interval": wavelength_interval,
                    "col_start": col_start,
                    "col_num": col_num,
                    "plate_well_num": plate_well_num,
                    "row_start": row_start,
                    "row_num": row_num,
                }
            elif mode == "Fluorescence":
                read_from_bottom = components.pop(0)
                data_type = components.pop(0)
                assert data_type in ["Raw", "Reduced"]
                calibrate = components.pop(0)
                data_point_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                wavelength_min = int(components.pop(0))
                wavelength_max = int(components.pop(0))
                wavelength_interval = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                col_start = int(components.pop(0))
                col_num = int(components.pop(0))
                plate_well_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                cutoff_type = components.pop(0)  # Cutoff type
                cutoff_wavelength = int(components.pop(0))  # Cutoff wavelength
                spectrum_type = components.pop(0)  # Scanning type
                excitation_wavelength = int(components.pop(0))  # Excitation wavelength
                flashes_per_read = int(components.pop(0))  # Flashes per read
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                _ = components.pop(0)  # Unknown
                row_start = int(components.pop(0))
                row_num = int(components.pop(0))
                _ = components.pop(0)  # Unknown
                return {
                    "plate_name": plate_name,
                    "method": method,
                    "mode": mode,
                    "data_type": data_type,
                    "read_from_bottom": read_from_bottom,
                    "calibrate": calibrate,
                    "data_point_num": data_point_num,
                    "wavelength_min": wavelength_min,
                    "wavelength_max": wavelength_max,
                    "wavelength_interval": wavelength_interval,
                    "col_start": col_start,
                    "col_num": col_num,
                    "plate_well_num": plate_well_num,
                    "cutoff_type": cutoff_type,
                    "cutoff_wavelength": cutoff_wavelength,
                    "spectrum_type": spectrum_type,
                    "excitation_wavelength": excitation_wavelength,
                    "flashes_per_read": flashes_per_read,
                    "row_start": row_start,
                    "row_num": row_num,
                }
            else:
                raise ValueError(f"Unsupported read mode {mode} for spectrum method")
        else:
            raise ValueError(f"Unsupported read method {method}")

    @staticmethod
    def parse_read_area(
        plate_well_num: int,
        col_start: int,
        col_num: int,
        row_start: int,
        row_num: int,
        wavelengths: list[int] = None,
    ) -> list[tuple[str, int]]:
        """
        Calculate the well markers (a list of well markers) for the read area based on the plate well number, column start and number, row start and number.
        The well markers are returned as a list of tuples, where each tuple contains the row name and column name corresponding to a well in the read area.
        The row names and column names are determined by the plate well number and the column and row start and number.
        """
        well_markers = []
        plate_row_names_for_well_num = PLATE_ROW_NAMES[plate_well_num]
        plate_col_names_for_well_num = PLATE_COL_NAMES[plate_well_num]
        if wavelengths is None:
            for i in range(row_start - 1, row_start + row_num - 1):
                for j in range(col_start - 1, col_start + col_num - 1):
                    well_markers.append(
                        (
                            plate_row_names_for_well_num[i],
                            plate_col_names_for_well_num[j],
                        )
                    )
        else:
            for i in range(row_start - 1, row_start + row_num - 1):
                for j in range(col_start - 1, col_start + col_num - 1):
                    for wavelength in wavelengths:
                        well_markers.append(
                            (
                                plate_row_names_for_well_num[i],
                                f"{plate_col_names_for_well_num[j]}_{wavelength}",
                            )
                        )
        return well_markers

    @staticmethod
    def read_text_to_data(text: str) -> pd.DataFrame:
        """
        Read the text corresponding to a read and convert it to a pandas DataFrame. The text is organized in a specific format, which can be parsed to extract the data matrix for this read. The data matrix is returned as a pandas DataFrame directly correspinding to the plate layout, with the row and column names corresponding to the well positions.
        """
        data = pd.read_csv(
            StringIO(text),
            header=None,
            sep="\t",
        )
        marker = data.iloc[0, 0]
        temperature = data.iloc[0, 1]
        plate_data = data.iloc[0:, 2:-2]
        plate_shape = plate_data.shape

        return marker, temperature, plate_data, plate_shape

    @staticmethod
    def parse_read(
        text: str,
        metadata: dict,
    ):
        """
        Each read is organized as text separated by tabs.
        This function parses the text and extracts the data matrix for this read.
        The data matrix is returned as a pandas DataFrame directly correspinding to the plate layout,
        with the row and column names corresponding to the well positions.

        Parameters
        ----------
        text: str
            The text corresponding to this read, which is organized in a specific format.
        wavelengths: list[int], optional
            The list of wavelengths for this read, which is used to determine the column names for the data matrix.
            If the read method is kinetic and the read mode is absorbance,
            the wavelengths are used to determine the column names for the data matrix.

        Return
        ------
        marker: str
            The marker of this read, which is usually the time for kinetic reads
            and the wavelength for spectrum reads.
        temperature: float
            The temperature for this read.
        plate_data: pd.DataFrame
            The data matrix for this read, with the row and column names
            corresponding to the well positions.
        """

        read_method = metadata["method"]
        if read_method == "Kinetic":
            return SoftMaxPro_Plate_Kinetic._parse_read(text, metadata=metadata)
        elif read_method == "Spectrum":
            return SoftMaxPro_Plate_Spectrum._parse_read(text, metadata=metadata)
        elif read_method == "Endpoint":
            return SoftMaxPro_Plate_Endpoint._parse_read(text, metadata=metadata)
        else:
            raise ValueError(f"Unsupported read method {read_method}")

    @staticmethod
    def parse_block(
        textIO: StringIO,
    ) -> "MultiWellPlate | Signal1DCollection | SoftMaxPro_Group":
        """
        Automatically parse the block of text corresponding to a plate and extract the data.
        The parsing method is determined by the read method specified in the metadata.
        For kinetic read method, the data is organized as a series of reads,
        and each read contains a data matrix corresponding to the plate layout.
        The extracted data is returned as a SoftMaxProPlateKinetic object,
        which contains the metadata and the data for this plate.
        For endpoint and spectrum read methods, the parsing method is not implemented yet.
        Blocks starting with ``Group:`` (template reduction groups, e.g. BCA standard
        curve) are parsed by :meth:`SoftMaxPro_Group.parse_block`.
        """
        textIO.seek(0)
        first_line = textIO.readline()
        if first_line.startswith("Group:"):
            return SoftMaxPro_Group.parse_block(textIO)
        textIO.seek(0)
        metadata_text = textIO.readline()
        metadata = SoftMaxPro_Plate.parse_metadata(metadata_text)
        if metadata["method"] == "Endpoint":
            return SoftMaxPro_Plate_Endpoint._parse_block(
                textIO=textIO, metadata=metadata
            )
        elif metadata["method"] == "Kinetic":
            return SoftMaxPro_Plate_Kinetic._parse_block(
                textIO=textIO,
                metadata=metadata,
            )
        elif metadata["method"] == "Spectrum":
            return SoftMaxPro_Plate_Spectrum._parse_block(
                textIO=textIO,
                metadata=metadata,
            )
        else:
            raise ValueError(f"Unsupported read method {metadata['method']}")


@dataclass
class SoftMaxPro_Plate_Kinetic(ContinuousSignal1DCollection):

    metadata: dict = None

    @classmethod
    def _parse_block(
        cls,
        textIO: StringIO,
        metadata: dict,
    ) -> "SoftMaxPro_Plate_Kinetic":
        """
        This function should be called by the parse_block function of the SoftMaxProPlate class when the read method is kinetic.
        Each block corresponds to a plate and contains multiple reads. This function parses the block and extracts
        the metadata and the data for this plate. The metadata is extracted using the parse_metadata function, and the data is extracted using the parse_read function. The extracted data is organized as a MultiWellPlateSeries object, which contains a list of MultiWellPlate objects corresponding to each read, and a pandas DataFrame containing the time and temperature information for each read. The metadata and the data are returned as a SoftMaxProPlateKinetic object.
        """
        header = textIO.readline()
        plate_well_num = metadata["plate_well_num"]
        row_num = len(PLATE_ROW_NAMES[plate_well_num])
        data_point_num = metadata["data_point_num"]
        data_raw = {"Time": [], "Temperature": []}
        read_area = SoftMaxPro_Plate.parse_read_area(
            plate_well_num=metadata["plate_well_num"],
            col_start=metadata["col_start"],
            col_num=metadata["col_num"],
            row_start=metadata["row_start"],
            row_num=metadata["row_num"],
            wavelengths=metadata["wavelengths"],
        )
        for wavelength in metadata["wavelengths"]:
            for well_marker in read_area:
                data_raw[well_marker] = []
        early_terminated = False
        for i in range(data_point_num):
            read_text = ""
            for j in range(row_num):
                # Read text row by row
                line = textIO.readline()
                if not line:
                    early_terminated = True
                    break
                read_text += line
            if early_terminated:
                warnings.warn(
                    f"Plate {metadata['plate_name']} contains less data points than expected, which indicates an interrupted experiment."
                )
                break
            time, temperature, plate_data = SoftMaxPro_Plate.parse_read(
                read_text, metadata=metadata
            )
            seconds = time_to_seconds(time)
            data_raw["Time"].append(seconds)
            data_raw["Temperature"].append(temperature)
            for well_marker in read_area:
                data_raw[well_marker].append(
                    plate_data.loc[well_marker[0], well_marker[1]]
                )
            textIO.readline()  # Read the empty line between reads
        signals: list[ContinuousSignal1D] = []
        for value_name in data_raw:
            if value_name == "Time":
                continue
            elif value_name == "Temperature":
                value_unit = "°C"
            else:
                if metadata["mode"] == "Absorbance":
                    value_unit = "AU"
                elif metadata["mode"] == "Fluorescence":
                    value_unit = "RFU"
                else:
                    raise ValueError(f"Unsupported read mode {metadata['mode']}")
            signal = ContinuousSignal1D.from_data(
                data=pd.DataFrame(
                    {
                        "Time": data_raw["Time"],
                        value_name: data_raw[value_name],
                    }
                ),
                axis_name="Time",
                axis_unit="s",
                value_name=metadata["mode"],
                value_unit=value_unit,
                name=(
                    f"{value_name[0]}{value_name[1]}"
                    if isinstance(value_name, tuple)
                    else value_name
                ),
            )
            signals.append(signal)
        res = cls(
            signals=signals,
            description_annotations=[
                ContDescAnno(
                    name="Time",
                    unit="s",
                ),
                ContDescAnno(
                    name=metadata["mode"],
                    unit=value_unit,
                ),
            ],
            visible_signal_names=[signal.name for signal in signals],
        )
        res.metadata = metadata
        return res

    @classmethod
    def _parse_read(cls, text: str, metadata: dict):
        time, temperature, plate_data, _ = SoftMaxPro_Plate.read_text_to_data(text)
        wavelengths = metadata["wavelengths"]
        plate_well_num = metadata["plate_well_num"]
        cols_per_wavelength = len(PLATE_COL_NAMES[plate_well_num])

        # Drop separator columns between adjacent wavelength blocks.
        if len(wavelengths) > 1:
            separator_indices = [
                k * cols_per_wavelength + (k - 1) for k in range(1, len(wavelengths))
            ]
            separator_col_names = [plate_data.columns[i] for i in separator_indices]
            plate_data = plate_data.drop(columns=separator_col_names)

        plate_shape = plate_data.shape

        expected_col_num = {
            6: (2, 3 * len(wavelengths)),
            12: (3, 4 * len(wavelengths)),
            24: (4, 6 * len(wavelengths)),
            48: (6, 8 * len(wavelengths)),
            96: (8, 12 * len(wavelengths)),
            384: (16, 24 * len(wavelengths)),
        }
        flag = False
        for i in expected_col_num:
            if plate_shape == expected_col_num[i]:
                col_names = PLATE_COL_NAMES[i]
                row_names = PLATE_ROW_NAMES[i]
                flag = True
                break
        if not flag:
            raise ValueError(
                f"Unsupported plate shape {plate_shape} for {len(wavelengths)} wavelengths."
            )
        col_names_with_wavelengths = []
        for wavelength in wavelengths:
            for col_name in col_names:
                col_names_with_wavelengths.append(f"{col_name}_{wavelength}")
        plate_data.columns = col_names_with_wavelengths
        plate_data.index = row_names
        return time, temperature, plate_data

    def set_default_annotations(self):
        super().set_default_annotations()
        limit = None
        for signal in self.signals:
            if signal.name == "Temperature":
                continue
            else:
                if limit is None:
                    limit = [
                        signal.value_annotation.limit[0],
                        signal.value_annotation.limit[1],
                    ]
                else:
                    if signal.value_annotation.limit[0] < limit[0]:
                        limit[0] = signal.value_annotation.limit[0]
                    if signal.value_annotation.limit[1] > limit[1]:
                        limit[1] = signal.value_annotation.limit[1]
        self.value_annotation.limit = limit
        self.align_values(self.signal_names, limit[0], limit[1])
        self.value_annotation.ticklabel_space_major = (limit[1] - limit[0]) / 9


@dataclass
class SoftMaxPro_Plate_Spectrum(ContinuousSignal1DCollection):

    metadata: dict = None

    @classmethod
    def _parse_block(cls, textIO: StringIO, metadata: dict):
        """
        This function should be called by the parse_block function of the SoftMaxProPlate class when the read method is "Spectrum".
        Each block corresponds to a plate and contains multiple reads. This function parses the block and extracts
        the metadata and the data for this plate. The metadata is extracted using the parse_metadata function, and the data is extracted using the parse_read function. The extracted data is organized as a MultiWellPlateSeries object, which contains a list of MultiWellPlate objects corresponding to each read, and a pandas DataFrame containing the time and temperature information for each read. The metadata and the data are returned as a SoftMaxProPlateKinetic object.
        """
        header = textIO.readline()
        plate_well_num = metadata["plate_well_num"]
        row_num = len(PLATE_ROW_NAMES[plate_well_num])
        data_point_num = metadata["data_point_num"]
        data_raw = {"Wavelength": [], "Temperature": []}
        read_area = SoftMaxPro_Plate.parse_read_area(
            plate_well_num=metadata["plate_well_num"],
            col_start=metadata["col_start"],
            col_num=metadata["col_num"],
            row_start=metadata["row_start"],
            row_num=metadata["row_num"],
        )
        for well_marker in read_area:
            data_raw[well_marker] = []
        early_terminated = False
        for i in range(data_point_num):
            read_text = ""
            for j in range(row_num):
                read_text += textIO.readline()
                if len(read_text) == 0:
                    early_terminated = True
                    break
            if early_terminated:
                warnings.warn(
                    f"Plate {metadata['plate_name']} contains less data points than expected, which indicates an interrupted experiment."
                )
                break
            wavelength, temperature, plate_data = SoftMaxPro_Plate.parse_read(
                read_text, metadata=metadata
            )
            data_raw["Wavelength"].append(wavelength)
            data_raw["Temperature"].append(temperature)
            for well_marker in read_area:
                data_raw[well_marker].append(
                    plate_data.loc[well_marker[0], well_marker[1]]
                )
            textIO.readline()  # Read the empty line between reads
        signals: list[ContinuousSignal1D] = []
        for value_name in data_raw:
            if value_name == "Wavelength":
                continue
            elif value_name == "Temperature":
                value_unit = "°C"
            else:
                if metadata["mode"] == "Absorbance":
                    value_unit = "AU"
                elif metadata["mode"] == "Fluorescence":
                    value_unit = "RFU"
                else:
                    raise ValueError(f"Unsupported read mode {metadata['mode']}")
            signal = ContinuousSignal1D.from_data(
                data=pd.DataFrame(
                    {
                        "Wavelength": data_raw["Wavelength"],
                        value_name: data_raw[value_name],
                    },
                ),
                axis_name="Wavelength",
                axis_unit="nm",
                value_name=metadata["mode"],
                value_unit=value_unit,
                name=(
                    f"{value_name[0]}{value_name[1]}"
                    if isinstance(value_name, tuple)
                    else value_name
                ),
            )
            signals.append(signal)
        res = cls(
            signals=signals,
            description_annotations=[
                ContDescAnno(
                    name="Wavelength",
                    unit="nm",
                ),
                ContDescAnno(
                    name=metadata["mode"],
                    unit=value_unit,
                ),
            ],
            visible_signal_names=[signal.name for signal in signals],
        )
        res.metadata = metadata
        return res

    @staticmethod
    def _parse_read(text: str, metadata: dict):
        wavelength, temperature, plate_data, plate_shape = (
            SoftMaxPro_Plate.read_text_to_data(text)
        )
        expected_col_num = {
            6: (2, 3),
            12: (3, 4),
            24: (4, 6),
            48: (6, 8),
            96: (8, 12),
            384: (16, 24),
        }
        flag = False
        for i in expected_col_num:
            if plate_shape == expected_col_num[i]:
                col_names = PLATE_COL_NAMES[i]
                row_names = PLATE_ROW_NAMES[i]
                flag = True
                break
        if not flag:
            raise ValueError(
                f"Unsupported plate shape {plate_shape} for spectrum read."
            )
        plate_data.columns = col_names
        plate_data.index = row_names
        return wavelength, temperature, plate_data


@dataclass
class SoftMaxPro_Plate_Endpoint(MultiWellPlate):

    metadata: dict = None

    @classmethod
    def _parse_block(cls, textIO: StringIO, metadata: dict):
        """
        This function should be called by the parse_block function of the SoftMaxProPlate class when the read method is "Endpoint".
        Each block corresponds to a plate and contains a single read. This function parses the block and extracts
        the metadata and the data for this plate. The metadata is extracted using the parse_metadata function, and the data is extracted using the parse_read function. The extracted data is organized as a MultiWellPlate object, which contains the data matrix corresponding to the plate layout, and a pandas DataFrame containing the time and temperature information for this read. The metadata and the data are returned as a SoftMaxPlateEndpoint object.
        """
        header = textIO.readline()
        marker, temperature, plate_data = SoftMaxPro_Plate.parse_read(
            textIO.read(), metadata=metadata
        )
        res = cls(
            data=plate_data,
        )
        res.metadata = metadata
        return res

    @staticmethod
    def _parse_read(text: str, metadata: dict):
        """
        Parse a single endpoint read: a single data matrix corresponding to the
        plate layout (identical to a spectrum read, except the first column holds
        an empty marker instead of a time/wavelength).
        """
        marker, temperature, plate_data, plate_shape = (
            SoftMaxPro_Plate.read_text_to_data(text)
        )
        expected_col_num = {
            6: (2, 3),
            12: (3, 4),
            24: (4, 6),
            48: (6, 8),
            96: (8, 12),
            384: (16, 24),
        }
        col_names = None
        row_names = None
        flag = False
        for i in expected_col_num:
            if plate_shape == expected_col_num[i]:
                col_names = PLATE_COL_NAMES[i]
                row_names = PLATE_ROW_NAMES[i]
                flag = True
                break
        if not flag:
            raise ValueError(
                f"Unsupported plate shape {plate_shape} for endpoint read."
            )
        plate_data.columns = col_names
        plate_data.index = row_names
        return marker, temperature, plate_data


@dataclass
class SoftMaxPro_Group:
    """
    A reduction group in a SoftMax Pro export (a ``Group:`` block).

    SoftMax Pro templates define reduction groups that summarize groups of
    wells.  In a BCA protein-assay export, for example, the file contains a
    ``Standards`` group (the standard curve, with columns such as ``Conc``,
    ``Value`` and ``MeanValue``) and one group per sample (columns such as
    ``Values`` and ``Result`` — the interpolated concentration).

    Attributes
    ----------
    name : str
        The group name, e.g. ``"Standards"`` or a sample name.
    data : pandas.DataFrame
        The parsed per-well data table.  The sample number in the first column
        is forward-filled across replicate wells; purely numeric columns are
        converted to ``float`` while text columns (e.g. well IDs) are kept as
        strings.
    columns : pandas.DataFrame
        The ``Group Column`` formula table (column name, formula name,
        formula, precision, notation) as reported by SoftMax Pro.
    summaries : pandas.DataFrame
        The ``Group Summaries`` rows (empty DataFrame when none are present).
    """

    name: str
    data: pd.DataFrame
    columns: pd.DataFrame = None
    summaries: pd.DataFrame = None

    @classmethod
    def parse_block(cls, textIO: StringIO) -> "SoftMaxPro_Group":
        """
        Parse a ``Group:`` block.

        Block layout::

            Group: <name>
            <column header line>
            <data rows>          # empty first cell = continuation of previous sample
            Group Column ...     # column formula definitions
            Group Summaries      # optional summary rows
            ~End

        Returns
        -------
        SoftMaxPro_Group
        """
        textIO.seek(0)
        first_line = textIO.readline()
        name = first_line.split(":", 1)[1].strip()

        header_line = textIO.readline()
        header = [c.strip() for c in header_line.rstrip("\n").split("\t")]
        while header and header[-1] == "":
            header.pop()

        remaining = textIO.readlines()
        # --- split into data / column-formula / summaries sections ---
        data_lines: list[str] = []
        column_lines: list[str] = []
        summary_lines: list[str] = []
        section = "data"
        for line in remaining:
            stripped = line.rstrip("\n")
            if stripped.startswith("Group Column"):
                section = "columns"
                continue
            if stripped.startswith("Group Summaries"):
                section = "summaries"
                continue
            if stripped.strip() == "":
                continue
            if section == "data":
                data_lines.append(stripped)
            elif section == "columns":
                column_lines.append(stripped)
            else:
                summary_lines.append(stripped)

        rows = []
        for line in data_lines:
            cells = [c.strip() for c in line.split("\t")]
            cells = (cells + [""] * len(header))[: len(header)]
            rows.append(cells)
        data = pd.DataFrame(rows, columns=header)
        data = data.replace("", pd.NA)
        if header:
            data[header[0]] = data[header[0]].ffill()
        for col in data.columns:
            data[col] = cls._coerce_numeric(data[col])

        # --- Group Column section ---
        columns = pd.DataFrame()
        if column_lines:
            col_header = ["Column", "Formula Name", "Formula", "Precision", "Notation"]
            col_rows = []
            for line in column_lines:
                cells = line.split("\t")
                cells = (cells + [""] * len(col_header))[: len(col_header)]
                col_rows.append(cells)
            columns = pd.DataFrame(col_rows, columns=col_header)
            columns = columns.replace("", pd.NA)
            for col in columns.columns:
                columns[col] = cls._coerce_numeric(columns[col])

        # --- Group Summaries section ---
        summaries = pd.DataFrame()
        if summary_lines:
            max_cells = max(len(l.split("\t")) for l in summary_lines)
            sum_rows = []
            for line in summary_lines:
                cells = line.split("\t")
                cells = (cells + [""] * max_cells)[:max_cells]
                sum_rows.append(cells)
            summaries = pd.DataFrame(sum_rows)

        return cls(name=name, data=data, columns=columns, summaries=summaries)

    @staticmethod
    def _coerce_numeric(series: pd.Series) -> pd.Series:
        """Convert a column to numeric only if every value is numeric, so text
        columns (e.g. well IDs like ``A4``) are preserved."""
        nonempty = series.dropna()
        if nonempty.empty:
            return series
        try:
            converted = pd.to_numeric(nonempty)
        except (ValueError, TypeError):
            return series
        if converted.notna().all():
            return converted.reindex(series.index)
        return series


@dataclass
class SoftMaxPro_Project:
    """
    An object to read data from Molecular Devices SoftMax Pro software. The data is usually exported
    as .txt files with UTF-16 LE encoding. The file contains multiple blocks of data, each block
    corresponds to a plate (``Plate:``) or a reduction group (``Group:``). Each block starts with a line
    containing "##BLOCKS= " and ends with a line containing "~End". The data in each block is organized
    in a specific format, which can be parsed to extract the kinetic or endpoint data for each plate,
    or the reduction table for each group. Plates are returned as :class:`SoftMaxPro_Plate_Kinetic`,
    :class:`SoftMaxPro_Plate_Spectrum` or :class:`SoftMaxPro_Plate_Endpoint` objects; groups are returned
    as :class:`SoftMaxPro_Group` objects.
    """

    blocks: list[
        SoftMaxPro_Plate_Kinetic
        | SoftMaxPro_Plate_Spectrum
        | SoftMaxPro_Plate_Endpoint
        | SoftMaxPro_Group
    ] = field(default_factory=list)

    @classmethod
    def read_txt(
        cls,
        txt_file: str | Path,
    ) -> "SoftMaxPro_Project":
        """ """
        with open(txt_file, "r", encoding="utf-16le") as f:
            block_num_line = f.readline()
            block_num = int(re.search(r"##BLOCKS= (\d+).*", block_num_line).group(1))
            blocks = []
            for i in range(block_num):
                block = StringIO()
                while True:
                    line = f.readline()
                    if not line or line.startswith("~End"):
                        break
                    block.write(line)
                blocks.append(block)
            project_metadata = f.readline().strip()

        block_results = []
        for block in blocks:
            block_result = SoftMaxPro_Plate.parse_block(block)
            block_results.append(block_result)

        return cls(blocks=block_results)

    @classmethod
    def read_xls(cls, xls_file: str | Path):
        return cls.read_txt(txt_file=xls_file)

    @property
    def plates(
        self,
    ) -> list[
        SoftMaxPro_Plate_Endpoint | SoftMaxPro_Plate_Kinetic | SoftMaxPro_Plate_Spectrum
    ]:
        """Plate blocks only (``Plate:`` sections)."""
        return [
            block
            for block in self.blocks
            if isinstance(
                block,
                (
                    SoftMaxPro_Plate_Endpoint,
                    SoftMaxPro_Plate_Kinetic,
                    SoftMaxPro_Plate_Spectrum,
                ),
            )
        ]

    @property
    def groups(self) -> list[SoftMaxPro_Group]:
        """Reduction-group blocks only (``Group:`` sections)."""
        return [block for block in self.blocks if isinstance(block, SoftMaxPro_Group)]

    @property
    def metadata(self):
        return [block.metadata for block in self.plates]

    @property
    def plate_name(self):
        return [metadata["plate_name"] for metadata in self.metadata]

    def group(self, name: str) -> SoftMaxPro_Group:
        """Look up a reduction group by its name."""
        for group in self.groups:
            if group.name == name:
                return group
        raise KeyError(f"Group {name} not found in this project.")

    def __getitem__(self, key: str):
        for block in self.plates:
            if block.metadata["plate_name"] == key:
                return block
        for group in self.groups:
            if group.name == key:
                return group
        raise KeyError(f"Plate or group {key} not found in this project.")


@dataclass
class SoftMaxPro_Protocol:
    """
    对 SoftMax Pro 读板结果进行后处理的协议对象。

    根据用户定义的组 (groups) 从 :class:`MultiWellPlate` 提取各孔吸光度,
    拟合标准曲线, 并反算未知孔浓度。

    组定义 (dict):

    - standards 组 (必须且唯一)::

        {
            "name": "standards",
            "type": "standards",
            "fit": "linear",   # 拟合方式, 当前仅支持 "linear" (线性回归)
            "series": [
                {"value": 0, "unit": "mg/ml", "wells": ["A1", "A2", "A3"]},
                {"value": 0.125, "unit": "mg/ml", "wells": ["B1", "B2", "B3"]},
                ...
            ],
        }

      ``fit`` key 控制标准曲线的拟合方式, value 为 ``"linear"`` 时使用线性回归
      (``scipy.stats.linregress``), 这也是默认值。

    - unknown 组 (可多个)::

        {"name": "sampleA", "type": "unknown", "wells": ["A4", "B4", "C4"]}

    - unknown_dilution 组 (可多个) —— 带稀释梯度的未知样品::

        {
            "name": "Elution",
            "type": "unknown_dilution",
            "series": [                                     # 每个 series = 一个稀释梯度
                {"dilution_factor": 1.0, "wells": ["B4", "B5", "B6"]},
                {"dilution_factor": 2.0, "wells": ["C4", "C5", "C6"]},
                {"dilution_factor": 4.0, "wells": ["D4", "D5", "D6"]},
                ...
            ],
        }

      每个 ``series`` 项是一个稀释梯度, ``dilution_factor`` 为该梯度的稀释倍数
      (原始样品被稀释的倍数, 如 2 倍稀释写 ``2.0``)。语义镜像 SoftMax Pro 导出的
      ``Unk_Dilution`` 组: 逐孔 ``Concentration`` 是**未校正的原始反算浓度**
      (由标准曲线反算), 每个梯度的**首行**额外给出 ``Dilution`` (稀释倍数) 与
      ``AdjResult`` = ``MeanResult × Dilution`` (校正到原始样品浓度); 同梯度其余行的
      这几列为 NaN。

    使用示例::

        protocol = SoftMaxPro_Protocol([standards, sampleA, elution])
        result = protocol.apply(plate)      # 返回 self
        result.plot_standard_curve()        # 绘制标准曲线图 (返回 Figure)
        result["sampleA"]                   # 按组名取该组浓度结果 (DataFrame)
        result.results                      # 全部结果: Well, Group, Value, InRange, Concentration, ...
        result.summary                      # 每组 (稀释组为每梯度) 汇总: Mean/SD/CV%/AdjResult

    Attributes
    ----------
    groups : list[dict]
        组定义列表。
    results : pandas.DataFrame
        未知孔的逐孔浓度结果表 (调用 :meth:`apply` 后可用), 列包括 Well,
        Group, Value (吸光度), InRange (吸光度是否落在标准品量程内),
        Concentration (未校正的反算浓度), Unit, 以及每个梯度首行的统计列
        MeanResult / Std.Dev. / CV%, 稀释组还带 Dilution / AdjResult
        (与 SoftMax Pro Group 区块一致)。
    summary : pandas.DataFrame
        未知组的汇总统计表: ``unknown`` 组每组一行, ``unknown_dilution`` 组
        每个稀释梯度一行, 含 Group, n (孔数), MeanValue / SD_Value (吸光度),
        MeanConcentration / SD_Concentration (浓度), CV%, nInRange (量程内
        孔数), 稀释组另有 Dilution 与 AdjResult = MeanConcentration × Dilution,
        以及 FittedConcentration (稀释线性回归给出的原始样品浓度, 组内各行相同)。
    standards_data : pandas.DataFrame
        标准曲线数据表 (Conc, Value 均值, SD)。
    fit_result : scipy.stats.linregress 结果
        标准曲线拟合结果 (调用 :meth:`apply` 后可用)。
    standard_curve : matplotlib Figure
        标准曲线图 (调用 :meth:`apply` 后可用)。
    dilution_fit : dict[str, scipy.stats.linregress 结果 | None]
        每个 ``unknown_dilution`` 组一个稀释线性回归结果 (组名 → ``linregress``
        结果): 以 ``1/dilution_factor`` 为 x、未校正反算浓度为 y 做线性回归,
        ``slope`` 即原始样品浓度, ``intercept`` 理想接近 0。梯度数不足 2 的组为
        ``None``; 非稀释组不出现在该 dict 中。

    Methods
    -------
    plot_standard_curve(groups="all")
        绘制标准曲线图并返回 Figure (每组未知样品以平均浓度 ± 误差棒绘制;
        可用 ``groups`` 指定只绘制某些组)。
    plot_unknown_dilution_curve(groups="all")
        绘制 ``unknown_dilution`` 组的稀释线性图并返回 Figure: 以
        ``1/dilution`` 为 x、未校正反算浓度 (均值 ± SD) 为 y 散点, 叠加线性
        回归直线, 并标注方程/R² 与 "slope = 原始样品浓度"。
    __getitem__(group_name)
        按组名返回该组的浓度结果子表 (DataFrame)。
    """

    groups: list[dict] = field(default_factory=list)

    _plate = None
    _results = None
    _summary = None
    _standards_data = None
    _standard_curve_fig = None
    _fit_result = None
    _dilution_fits = None
    _standard_group = None
    _unit = None

    _SUPPORTED_FITS = ("linear",)
    _SUPPORTED_TYPES = ("unknown", "unknown_dilution")

    @staticmethod
    def _well_to_marker(well: str) -> tuple[str, int]:
        """将 "A1" 形式的孔位转为 (行字母, 列号) 元组, 供 MultiWellPlate 索引。"""
        row = well[0]
        col = int(well[1:])
        return row, col

    @classmethod
    def _group_levels(cls, group: dict) -> list[dict]:
        """把一个未知组定义展开为若干"梯度" (level)。

        ``unknown`` 组展开为单个梯度 (``dilution`` 为 ``None``);
        ``unknown_dilution`` 组的每个 ``series`` 项展开为一个稀释梯度,
        该项的 ``dilution_factor`` 作为 ``dilution``。

        Returns
        -------
        list[dict]
            ``[{"dilution": float | None, "wells": [...]}, ...]``
        """
        name = group.get("name", "unknown")
        gtype = group.get("type", "unknown")
        if gtype == "unknown":
            if "wells" not in group:
                raise ValueError(
                    f"Group {name!r} of type 'unknown' needs a 'wells' list."
                )
            return [{"dilution": None, "wells": list(group["wells"])}]
        if gtype == "unknown_dilution":
            if "series" not in group:
                raise ValueError(
                    f"Group {name!r} of type 'unknown_dilution' needs a 'series' "
                    f"list of {{'dilution_factor': ..., 'wells': [...]}} items."
                )
            levels = []
            for i, series in enumerate(group["series"]):
                if "dilution_factor" not in series:
                    raise ValueError(
                        f"Group {name!r} series #{i + 1} needs a 'dilution_factor'."
                    )
                if "wells" not in series:
                    raise ValueError(
                        f"Group {name!r} series #{i + 1} needs a 'wells' list."
                    )
                levels.append(
                    {
                        "dilution": float(series["dilution_factor"]),
                        "wells": list(series["wells"]),
                    }
                )
            if not levels:
                raise ValueError(
                    f"Group {name!r} of type 'unknown_dilution' has an empty 'series'."
                )
            return levels
        raise ValueError(
            f"Unsupported group type {gtype!r} for group {name!r}. "
            f"Supported: {list(cls._SUPPORTED_TYPES)} (plus 'standards')."
        )

    def apply(self, plate: MultiWellPlate) -> "SoftMaxPro_Protocol":
        """
        对给定孔板执行协议: 提取标准品吸光度 -> 拟合标准曲线 ->
        反算未知孔浓度, 并生成标准曲线图。

        Parameters
        ----------
        plate : MultiWellPlate
            该协议的孔板数据 (例如 ``SoftMaxPro_Project["Plate1"]`` 返回的板)。

        Returns
        -------
        SoftMaxPro_Protocol
            自身, 便于链式调用。
        """
        self._plate = plate
        standards = [g for g in self.groups if g.get("type") == "standards"]
        unknowns = [g for g in self.groups if g.get("type") != "standards"]
        if len(standards) != 1:
            raise ValueError(
                f"Exactly one standards group (type='standards') is required, "
                f"got {len(standards)}."
            )
        standard_group = standards[0]

        fit = standard_group.get("fit", "linear")
        if fit not in self._SUPPORTED_FITS:
            raise ValueError(
                f"Unsupported fit method {fit!r}. Supported: {list(self._SUPPORTED_FITS)}"
            )

        # --- 提取标准品吸光度 ---
        std_rows = []
        unit = ""
        for series in standard_group["series"]:
            value = series["value"]
            unit = series.get("unit", "")
            wells = series["wells"]
            od_values = [float(plate[self._well_to_marker(w)]) for w in wells]
            std_rows.append(
                {
                    "Conc": value,
                    "Value": float(np.mean(od_values)),
                    "SD": (
                        float(np.std(od_values, ddof=1)) if len(od_values) > 1 else 0.0
                    ),
                    "Wells": ", ".join(wells),
                }
            )
        standards_data = pd.DataFrame(std_rows)
        self._standards_data = standards_data

        # --- 拟合标准曲线 ---
        if fit == "linear":
            fit_result = st.linregress(standards_data["Conc"], standards_data["Value"])
        else:  # pragma: no cover - guarded above
            raise ValueError(f"Unsupported fit method {fit!r}")
        self._fit_result = fit_result

        slope = fit_result.slope
        intercept = fit_result.intercept

        # --- 反算未知孔浓度 ---
        # 量程 = 各标准品浓度点吸光度均值的范围, 对齐 SoftMax 的 MinStd / MaxStd
        # (即 Group Summaries 里的 Min(MeanValue) / Max(MeanValue))。
        std_mean_values = [row["Value"] for row in std_rows]
        min_std = min(std_mean_values)
        max_std = max(std_mean_values)

        result_rows = []
        summary_rows = []
        dilution_levels: dict[str, list[tuple[float, float]]] = {}
        for group in unknowns:
            name = group.get("name", "unknown")
            for level in self._group_levels(group):
                wells = level["wells"]
                dilution = level["dilution"]
                ods = [float(plate[self._well_to_marker(w)]) for w in wells]
                concs = [(od - intercept) / slope for od in ods]
                # SoftMax 的 R 列: 吸光度落在标准品量程外则标记
                in_range = [bool(min_std <= od <= max_std) for od in ods]
                n = len(wells)
                mean_conc = float(np.mean(concs))
                sd_conc = float(np.std(concs, ddof=1)) if n > 1 else 0.0
                # SoftMax Pro 的 Cv 以 |mean| 为分母, 故取绝对值
                cv = float(sd_conc / abs(mean_conc) * 100) if mean_conc != 0 else np.nan
                mean_od = float(np.mean(ods))
                sd_od = float(np.std(ods, ddof=1)) if n > 1 else 0.0
                # AdjResult = MeanResult × Dilution, 即校正回原始样品浓度
                adj_result = mean_conc * dilution if dilution is not None else np.nan
                for i, (well, od, conc, flag) in enumerate(
                    zip(wells, ods, concs, in_range)
                ):
                    result_rows.append(
                        {
                            "Well": well,
                            "Group": name,
                            "Value": od,
                            "InRange": flag,
                            "Concentration": conc,
                            "Unit": unit,
                            "MeanResult": mean_conc if i == 0 else np.nan,
                            "Std.Dev.": sd_conc if i == 0 else np.nan,
                            "CV%": cv if i == 0 else np.nan,
                            "Dilution": (
                                dilution if (i == 0 and dilution is not None) else np.nan
                            ),
                            "AdjResult": adj_result if i == 0 else np.nan,
                        }
                    )
                if dilution is not None:
                    dilution_levels.setdefault(name, []).append((dilution, mean_conc))
                summary_rows.append(
                    {
                        "Group": name,
                        "n": n,
                        "MeanValue": mean_od,
                        "SD_Value": sd_od,
                        "MeanConcentration": mean_conc,
                        "SD_Concentration": sd_conc,
                        "CV%": cv,
                        "Dilution": dilution if dilution is not None else np.nan,
                        "AdjResult": adj_result,
                        "nInRange": int(sum(in_range)),
                    }
                )
        results = pd.DataFrame(result_rows)
        self._results = results

        # --- 稀释线性回归: 未校正反算浓度 vs 1/dilution_factor ---
        # 理想情况下 c_反算 = c_原始 / dilution, 即反算浓度对 1/dilution 为过原点
        # 直线: 斜率 = 原始样品浓度, 截距应接近 0 (偏离提示基质效应/本底)。
        dilution_fits = {}
        for name, pairs in dilution_levels.items():
            if len(pairs) >= 2:
                xs = [1.0 / dilution for dilution, _ in pairs]
                ys = [conc for _, conc in pairs]
                dilution_fits[name] = st.linregress(xs, ys)
            else:  # 只有一个梯度, 无法做回归
                dilution_fits[name] = None
        self._dilution_fits = dilution_fits

        summary = pd.DataFrame(summary_rows)
        if not summary.empty:
            # 稀释线性回归给出的原始样品浓度 (同一稀释组内每个梯度行相同)
            fitted_concentrations = {
                name: (fit.slope if fit is not None else np.nan)
                for name, fit in dilution_fits.items()
            }
            summary["FittedConcentration"] = [
                fitted_concentrations.get(group_name, np.nan)
                for group_name in summary["Group"]
            ]
        self._summary = summary

        # --- 标准曲线图 ---
        self._standard_group = standard_group
        self._unit = unit
        self._standard_curve_fig = self._build_standard_curve_figure(
            standard_group=standard_group,
            unit=unit,
            standards_data=standards_data,
            fit_result=fit_result,
            summary=summary,
        )
        return self

    def _build_standard_curve_figure(
        self,
        standard_group: dict,
        unit: str,
        standards_data: pd.DataFrame,
        fit_result,
        summary: pd.DataFrame,
    ):
        """构建标准曲线图: 标准点散点 + 拟合直线 + 每组未知样品的均值/误差棒。"""
        fig, ax = plt.subplots()
        std = standards_data

        # 标准品散点 + 误差棒
        ax.errorbar(
            std["Conc"],
            std["Value"],
            yerr=std["SD"],
            fmt="o",
            color="black",
            markersize=1,
            capsize=3,
            label=standard_group.get("name", "standards"),
        )
        # 拟合直线
        xs = np.linspace(std["Conc"].min() * 0.9, std["Conc"].max() * 1.1, 100)
        ax.plot(
            xs,
            fit_result.slope * xs + fit_result.intercept,
            color="red",
            linewidth=1.5,
            label="linear fit",
        )
        # 未知组: 每组用平均浓度(x) ± 平均吸光度(y), 画 error bar, 分组分开
        # (unknown_dilution 组的每个稀释梯度各为一个点, 图例标注稀释倍数)
        if summary is not None and not summary.empty:
            for i, row in summary.iterrows():
                label = str(row["Group"])
                dilution = row.get("Dilution")
                if dilution is not None and pd.notna(dilution):
                    label = f"{label} {float(dilution):g}×"
                ax.errorbar(
                    row["MeanConcentration"],
                    row["MeanValue"],
                    xerr=row["SD_Concentration"],
                    yerr=row["SD_Value"],
                    fmt="x",
                    color=f"C{i + 1}",
                    markersize=1,
                    capsize=3,
                    label=label,
                    zorder=3,
                )
        r2 = fit_result.rvalue**2
        ax.set_xlabel(f"Concentration ({unit})" if unit else "Concentration")
        ax.set_ylabel("Absorbance")
        ax.set_title(
            f"Standard curve: y = {fit_result.slope:.4f}x "
            f"{fit_result.intercept:+.4f}  (R² = {r2:.4f})"
        )
        ax.legend()
        return fig

    @property
    def results(self) -> pd.DataFrame:
        """未知孔浓度结果表 (调用 :meth:`apply` 后可用)。

        列为 ``Well``, ``Group``, ``Value`` (吸光度), ``InRange`` (吸光度是否
        落在标准品量程 MinStd..MaxStd 内, 对应 SoftMax 的 R 列标记),
        ``Concentration`` (由标准曲线反算、**未做稀释校正**的浓度), ``Unit``,
        以及每个梯度首行 (该梯度第一个孔) 的统计: ``MeanResult`` (梯度平均浓度),
        ``Std.Dev.`` (浓度标准差), ``CV%`` (变异系数 = Std.Dev./|MeanResult|*100)、
        ``Dilution`` (稀释倍数) 和 ``AdjResult`` (= MeanResult × Dilution,
        即校正回原始样品浓度; 非稀释组为 NaN)。与 SoftMax Pro Group 区块的导出
        格式一致, 同梯度其余行的这几列为 NaN。
        """
        if self._results is None:
            raise RuntimeError("Call apply(plate) before accessing results.")
        return self._results

    @property
    def summary(self) -> pd.DataFrame:
        """未知组汇总统计表 (调用 :meth:`apply` 后可用)。

        ``unknown`` 组每组一行, ``unknown_dilution`` 组每个稀释梯度一行:
        ``Group``, ``n`` (孔数), ``MeanValue`` / ``SD_Value`` (吸光度均值/标准差),
        ``MeanConcentration`` / ``SD_Concentration`` (**未校正**浓度均值/标准差),
        ``CV%``, ``nInRange`` (落在标准品量程内的孔数); 稀释组另有 ``Dilution``
        (稀释倍数)、``AdjResult`` (= MeanConcentration × Dilution, 校正回原始
        样品浓度) 与 ``FittedConcentration`` (稀释线性回归给出的原始样品浓度,
        组内每个梯度行相同); 非稀释组的这几列为 NaN。
        """
        if self._summary is None:
            raise RuntimeError("Call apply(plate) before accessing summary.")
        return self._summary

    @property
    def standards_data(self) -> pd.DataFrame:
        """标准曲线数据表 (调用 :meth:`apply` 后可用)。"""
        if self._standards_data is None:
            raise RuntimeError("Call apply(plate) before accessing standards_data.")
        return self._standards_data

    @property
    def fit_result(self):
        """标准曲线拟合结果 (调用 :meth:`apply` 后可用)。"""
        if self._fit_result is None:
            raise RuntimeError("Call apply(plate) before accessing fit_result.")
        return self._fit_result

    @property
    def standard_curve(self):
        """标准曲线图 (matplotlib Figure, 调用 :meth:`apply` 后可用)。"""
        if self._standard_curve_fig is None:
            raise RuntimeError("Call apply(plate) before accessing standard_curve.")
        return self._standard_curve_fig

    def plot_standard_curve(self, groups="all"):
        """绘制并返回标准曲线图。

        Parameters
        ----------
        groups : str | list[str] | tuple[str], default="all"
            要绘制的未知组。默认 ``"all"`` 绘制全部未知组;
            也可传入一个或多个组名 (如 ``groups=["SampleA", "SampleB"]``),
            此时只绘制指定的未知组 (标准点与拟合直线始终绘制)。

        Returns
        -------
        matplotlib Figure
            标准曲线图。
        """
        if groups == "all":
            summary = self.summary
        else:
            if isinstance(groups, str):
                groups = [groups]
            summary = self.summary[self.summary["Group"].isin(list(groups))]
            missing = [g for g in groups if g not in set(self.summary["Group"])]
            if missing:
                raise KeyError(
                    f"Unknown group(s) {missing} not found in results. "
                    f"Available groups: {sorted(self.summary['Group'].unique())}"
                )
        if self._standard_group is None or self._unit is None:
            raise RuntimeError("Call apply(plate) before plotting.")
        return self._build_standard_curve_figure(
            standard_group=self._standard_group,
            unit=self._unit,
            standards_data=self.standards_data,
            fit_result=self.fit_result,
            summary=summary,
        )

    @property
    def dilution_fit(self) -> dict:
        """每个 ``unknown_dilution`` 组的稀释线性回归结果 (调用 :meth:`apply` 后可用)。

        以 ``1/dilution_factor`` 为 x、未校正反算浓度为 y 做
        ``scipy.stats.linregress`` 回归: ``slope`` 即原始样品浓度,
        ``intercept`` 应接近 0。梯度数不足 2 的组映射为 ``None``;
        非 ``unknown_dilution`` 组不出现在该 dict 中。
        """
        if self._dilution_fits is None:
            raise RuntimeError("Call apply(plate) before accessing dilution_fit.")
        return self._dilution_fits

    def plot_unknown_dilution_curve(self, groups="all"):
        """绘制并返回稀释线性图 (每个 ``unknown_dilution`` 组一条回归直线)。

        以 ``1/dilution_factor`` 为 x、未校正反算浓度 (均值 ± SD) 为 y 画点,
        叠加线性回归直线; 回归斜率即原始样品浓度 (图上标注方程、R² 与斜率)。

        Parameters
        ----------
        groups : str | list[str], default="all"
            要绘制的稀释组名 (``"all"`` 绘制全部 ``unknown_dilution`` 组);
            传入普通 ``unknown`` 组名会抛 ``KeyError``。

        Returns
        -------
        matplotlib Figure
            稀释线性图。
        """
        fits = self._dilution_fits
        if fits is None:
            raise RuntimeError("Call apply(plate) before plotting.")
        available = list(fits)
        if not available:
            raise ValueError(
                "plot_unknown_dilution_curve requires at least one group of type "
                "'unknown_dilution' (use plot_standard_curve for 'unknown' groups)."
            )
        if groups == "all":
            selected = available
        else:
            if isinstance(groups, str):
                groups = [groups]
            missing = [g for g in groups if g not in available]
            if missing:
                raise KeyError(
                    f"Unknown dilution group(s) {missing}. "
                    f"Available groups: {sorted(available)}"
                )
            selected = list(groups)
        no_fit = [g for g in selected if fits[g] is None]
        if no_fit:
            raise ValueError(
                f"Group(s) {no_fit} have fewer than 2 dilution levels — "
                f"a dilution regression needs at least 2."
            )
        return self._build_dilution_curve_figure(selected, fits)

    def _build_dilution_curve_figure(self, groups: list[str], fits: dict):
        """构建稀释线性图: 每组 (1/dilution, 平均反算浓度±SD) 散点 + 回归直线。"""
        fig, ax = plt.subplots()
        annotations = []
        x_points: list[float] = []
        summary = self.summary
        for i, name in enumerate(groups):
            rows = summary[(summary["Group"] == name) & summary["Dilution"].notna()]
            dilutions = np.asarray(rows["Dilution"], dtype=float)
            xs = 1.0 / dilutions
            ys = np.asarray(rows["MeanConcentration"], dtype=float)
            yerr = np.asarray(rows["SD_Concentration"], dtype=float)
            color = f"C{i}"
            ax.errorbar(
                xs,
                ys,
                yerr=yerr,
                fmt="o",
                color=color,
                capsize=3,
                label=f"{name} (mean ± SD)",
            )
            fit = fits[name]
            if fit is None:  # pragma: no cover - 调用方已拦截
                raise ValueError(f"Group {name!r} has no dilution regression result.")
            x_line = np.linspace(0.0, float(np.max(xs)) * 1.05, 100)
            ax.plot(
                x_line,
                fit.slope * x_line + fit.intercept,
                color=color,
                linewidth=1.5,
                linestyle="--",
                label=f"{name} linear fit",
            )
            annotations.append(
                f"{name}: y = {fit.slope:.4f}x {fit.intercept:+.4f}  "
                f"(R² = {fit.rvalue**2:.4f})\n"
                f"    slope = {fit.slope:.4f} {self._unit} (original concentration)"
            )
            x_points.extend(xs.tolist())
        # x 轴刻度直接标出对应稀释倍数, 便于与实验梯度对应
        tick_values = sorted({round(x, 6) for x in x_points})
        ax.set_xticks(tick_values, labels=[f"1/{1 / x:g}" for x in tick_values])
        ax.set_xlabel("Relative concentration (1/dilution)")
        ax.set_ylabel(
            f"Back-calculated concentration ({self._unit})"
            if self._unit
            else "Back-calculated concentration"
        )
        ax.set_title("Dilution linearity")
        ax.set_xlim(-0.02, max(tick_values) * 1.08)
        ax.text(
            0.02,
            0.98,
            "\n".join(annotations),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
        )
        ax.legend()
        return fig

    def __getitem__(self, key: str) -> pd.DataFrame:
        """按组名返回该组的浓度结果子表 (调用 :meth:`apply` 后可用)。

        Parameters
        ----------
        key : str
            未知组名 (即组定义中的 ``"name"``), 例如 ``protocol["20d42243"]``。

        Returns
        -------
        pandas.DataFrame
            该组全部孔的 ``results`` 子表 (Well, Value, Concentration, ...)。
        """
        if self._results is None:
            raise RuntimeError("Call apply(plate) before accessing results.")
        subset = self._results[self._results["Group"] == key]
        if subset.empty:
            raise KeyError(
                f"Group {key!r} not found in results. "
                f"Available groups: {sorted(self._results['Group'].unique())}"
            )
        return subset.reset_index(drop=True)


class SoftMaxPro_CuvetteData(ContinuousSignal1D):
    """
    解析 SoftMax Pro 比色皿 (Cuvette) 数据。

    支持 SoftMax Pro 导出的多 section 格式（由空行分隔）：
      - Raw 数据（section name = "Wavelength"）
      - Ref 数据（section name = "Ref"）
      - Raw-Ref 数据（section name = "Raw-Ref"）

    示例::

        from instrumental_data_analyzer.instruments.MolecularDevices.softmax_pro import (
            SoftMaxPro_CuvetteData,
        )

        # 默认返回 Raw-Ref (OD)
        curve = SoftMaxPro_CuvetteData.from_clipboard(txt="data.txt")

        # 指定 mode = Transmission
        curve = SoftMaxPro_CuvetteData.from_clipboard(txt="data.txt", mode="Transmission")

        # 读取 Ref 段
        ref = SoftMaxPro_CuvetteData.from_clipboard(txt="data.txt", section="Ref")
    """

    _MODE_MAP = {
        "OD": ("Absorbance (OD)", "cm⁻¹"),
        "Transmission": ("Transmission", "%"),
    }

    _extra_metadata: dict = field(default_factory=dict)

    @classmethod
    def from_clipboard(
        cls,
        txt: str | Path = None,
        text: str | None = None,
        section: str = "Raw-Ref",
        mode: str = "OD",
    ) -> "SoftMaxPro_CuvetteData":
        """
        从 SoftMax Pro 导出的比色皿数据中解析指定的 section。

        Parameters
        ----------
        txt: str | Path, optional
            文件路径（尝试 UTF-8 读取）。
        text: str, optional
            直接传入的文本内容（例如从剪贴板粘贴的内容）。
        section: str, default="Raw-Ref"
            要返回的 section 名称：
              - ``"Wavelength"``  — 原始测量数据
              - ``"Ref"``         — 参比数据
              - ``"Raw-Ref"``     — 扣背景后的结果数据
        mode: str, default="OD"
            数据类型：
              - ``"OD"``           — 吸光度 (cm⁻¹)
              - ``"Transmission"`` — 透光率 (%)

        Returns
        -------
        SoftMaxPro_CuvetteData
            一个 ContinuousSignal1D 对象，axis=Wavelength (nm),
            value 根据 mode 确定。
        """
        if txt is not None:
            txt_path = Path(txt)
            try:
                text = txt_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = txt_path.read_text(encoding="utf-16-le")
        elif text is None:
            raise ValueError("Either 'txt' or 'text' must be provided.")

        if mode not in cls._MODE_MAP:
            raise ValueError(
                f"Unsupported mode '{mode}'. Supported modes: {list(cls._MODE_MAP.keys())}"
            )

        # --- 按空行分割 section ---
        lines = text.splitlines()
        sections: dict[str, list[str]] = {}
        current_name: str | None = None
        current_lines: list[str] = []

        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "":
                if current_name is not None and current_lines:
                    sections[current_name] = current_lines
                    current_name = None
                    current_lines = []
                continue
            if current_name is None:
                # 首行为 header → 第一列是 section 名称
                header_parts = stripped.split("\t")
                # 兼容 blank-separated header: 有些导出格式可能有额外空格
                current_name = header_parts[0].strip()
                current_lines = [stripped]
            else:
                current_lines.append(stripped)

        # 收尾最后一个 section
        if current_name is not None and current_lines:
            sections[current_name] = current_lines

        if section not in sections:
            available = list(sections.keys())
            raise KeyError(
                f"Section '{section}' not found. " f"Available sections: {available}"
            )

        # --- 解析目标 section ---
        section_text = "\n".join(sections[section])
        data = pd.read_csv(StringIO(section_text), sep="\t")

        axis_col = data.columns[0]  # Wavelength (nm) or section name as placeholder
        sample_col = data.columns[2]  # 第三列是样本名对应的测量值

        axis_values = data[axis_col].astype(float).values
        value_values = data[sample_col].astype(float).values

        # Temperature 作为 metadata
        temperature_str = str(data.iloc[0, 1])
        try:
            temperature = float(
                temperature_str.replace("¡C", "").replace("°C", "").strip()
            )
        except (ValueError, AttributeError):
            temperature = None

        value_name, value_unit = cls._MODE_MAP[mode]

        # 构建两列 DataFrame
        result_df = pd.DataFrame(
            {
                "Wavelength": axis_values,
                sample_col: value_values,
            }
        )

        result = cls.from_data(
            data=result_df,
            axis_name="Wavelength",
            axis_unit="nm",
            value_name=value_name,
            value_unit=value_unit,
            name=f"{section} ({sample_col})",
        )

        # 额外 metadata
        result._extra_metadata = {
            "section": section,
            "sample_name": sample_col,
            "temperature": temperature,
            "mode": mode,
        }
        return result
