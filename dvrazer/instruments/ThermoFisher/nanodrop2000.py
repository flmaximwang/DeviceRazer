"""
``instruments.ThermoFisher.nanodrop2000`` --- Thermo Fisher NanoDrop 2000 数据解析
====================================================================================

解析 NanoDrop 2000 分光光度计导出的 .tsv 文件。

:class:`Nanodrop2000Workbook` 继承自 :class:`AbsorbSpecCollection`:
- 自动将 .tsv 文件按双换行分割为多个光谱
- 每个光谱包含样品名和时间戳
- 支持去除时间戳重复名称
- 支持自动设置 UV-Vis 或 Protein A280 模式的坐标轴范围

使用示例::

    from dvrazer.instruments import Nanodrop2000Workbook

    wb = Nanodrop2000Workbook.from_tsv("spectra.tsv")
    wb.set_default_annotations(mode="UV-Vis")
    fig, ax = wb.plot()
"""

import io
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from copy import deepcopy

from ...utils import name_utils
from ...abstract.display import Signal1DPlotArgs
from ...concrete.spectroscopy import AbsorbSpec, AbsorbSpecCollection


@dataclass(slots=True)
class Nanodrop2000PlotArgs(Signal1DPlotArgs):
    ax_size: tuple[float, float] = (8, 6)
    colormap: str = "default"
    mode: int = 0


@dataclass
class Nanodrop2000Workbook(AbsorbSpecCollection):
    plot_args: Signal1DPlotArgs = field(default_factory=Nanodrop2000PlotArgs)

    @staticmethod
    def from_tsv(tsv, name=None):
        """
        Import a spectrum from a .tsv file
        """
        spectrums: list[AbsorbSpec] = []
        # 确保文件的末尾是 3 个换行符, 以便最后一个 spectrum 能被正确读取
        with open(tsv, "r") as file_input:
            lines = file_input.readlines()
        while lines.pop() == "\n":
            continue
        for i in range(3):
            lines.extend(["\n"])
        with open(tsv, "w") as file_output:
            file_output.writelines(lines)

        with open(tsv) as file_input:
            lines = file_input.readlines()
        # 将 lines 分割, 遇到 2 个连续换行符时进行分割
        new_line_indices = [i for i, line in enumerate(lines) if line == "\n"]
        separator_indices = [
            new_line_indices[i]
            for i in range(0, len(new_line_indices) - 1)
            if new_line_indices[i + 1] - new_line_indices[i] == 1
            and new_line_indices[i] - new_line_indices[i - 1] != 1
        ]
        separator_indices.insert(0, -2)
        for i in range(len(separator_indices) - 1):
            entryName = lines[separator_indices[i] + 2][:-1]
            time = lines[separator_indices[i] + 3][:-1]
            csv_text = "".join(
                lines[separator_indices[i] + 4 : separator_indices[i + 1]]
            )
            data = pd.read_csv(io.StringIO(csv_text), sep="\t", dtype=float)
            res = AbsorbSpec.from_data(
                data=data,
                axis_name="Wavelength",
                axis_unit="nm",
                value_name=data.columns[1],
            )
            res.name = f"{entryName} {time}"
            spectrums.append(res)
        name_counter = {}
        for i, spectrum in enumerate(spectrums):
            spectrum_name = spectrum.name
            if spectrum_name not in name_counter:
                name_counter[spectrum_name] = 0
            else:
                name_counter[spectrum_name] += 1
                spectrum.name = spectrum_name + f"({name_counter[spectrum_name]})"

        return Nanodrop2000Workbook(
            signals=spectrums,
            name=Path(tsv).stem if name is None else name,
            description_annotations=deepcopy(spectrums[0].description_annotations),
            plot_args=Nanodrop2000PlotArgs(),
            visible_signal_names=[spectrum.name for spectrum in spectrums],
        )

    def remove_timestamp(self):
        original_sig_names = list(self.keys())
        new_sig_names = [
            "_".join(sig_name.split("_")[:-1]) for sig_name in original_sig_names
        ]
        name_utils.rename_duplicated_names(new_sig_names)
        for new_name, old_name in zip(new_sig_names, original_sig_names):
            self.rename_signal(old_name, new_name)

    def set_default_annotations(self, mode: str):
        """
        Parameters
        ----------
        mode : str
            The mode of the measurement.
            UV-Vis: 220 nm to 800 nm
            Protein A280: 220 nm to 320 nm
        """

        super().set_default_annotations()
        if mode == "UV-Vis":
            self.align_axes(220, 720)
            self.axis_annotation.ticklabel_floor = 200
            self.axis_annotation.ticklabel_space_major = 100
            self.axis_annotation.ticklabel_space_minor = 20
            self.plot_args.legend_loc = "upper right"
        elif mode == "Protein A280":
            self.align_axes(220, 320)
            self.axis_annotation.ticklabel_floor = 220
            self.axis_annotation.ticklabel_space_major = 20
            self.axis_annotation.ticklabel_space_minor = 5
            self.plot_args.legend_loc = "upper right"
        else:
            raise ValueError(f"Unknown mode: {mode}")

        value_max = 0
        for signal_name in self.visible_signal_names:
            signal = self[signal_name]
            current_max = signal.data.iloc[:, 1].max()
            if current_max > value_max:
                value_max = current_max
        if (value_max > 10) & (value_max <= 15):
            self.align_values(self.visible_signal_names, 0, 15)
            self.value_annotation.ticklabel_space_major = 5
        elif (value_max > 15) & (value_max <= 60):
            self.align_values(self.visible_signal_names, 0, 60)
            self.value_annotation.ticklabel_space_major = 10
