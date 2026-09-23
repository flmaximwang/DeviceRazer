"""
Tests for the Agilent Cary WinUV export parser (``CaryAbsSpecCollection``).

The fixture files are generated on the fly, mirroring the structure of a real
Cary WinUV "Scan" export: a spectrum-name header line, a column-name line,
the data block (one (wavelength, absorbance) pair per spectrum), then one
metadata block per spectrum.
"""

import sys

sys.path.append("..")

import matplotlib

matplotlib.use("Agg")

import pytest

from instrumental_data_analyzer.instruments.Agilent.cary_winuv import (
    CaryAbsSpec,
    CaryAbsSpecCollection,
)

#: Wavelengths of the synthetic exports (Cary scans from Start to Stop nm)
WAVELENGTHS = list(range(600, 589, -1))

_METADATA_TEMPLATE = """Collection Time: {collection_time}
Operator Name  :
Scan Software Version: 4.20(468)
Parameter List :
Instrument                        Cary 100
Instrument Version                12.00
Start (nm)                        600.00
Stop (nm)                         500.00
X Mode                            Nanometers
Y Mode                            Abs
UV-Vis Scan Rate (nm/min)         600.000
UV-Vis Data Interval (nm)         1.000
UV-Vis Ave. Time (sec)            0.100
UV-Vis SBW (nm)                   1.0
Beam Mode                         Double
Signal-to-noise Mode              Off
UV Source                         On
Vis Source                        On
Source Changeover (nm)            350.00
Baseline Correction               Off
Cycle Mode                        On
Cycle Count                       10
Cycle Time (min)                  1.00
Comments
Method Log     :
Method Name    : E:\\s642\\20260923\\260923.MSW
Date/Time stamp: 2026/9/23 14:19:57
Method Modifications:
X Start nm Changed: 2026/9/23 13:51:05, Old: 800.00, New: 600.00
Saved as E:\\s642\\20260923\\5705-ox-1.BSW
End Method Modifications
[Time] , {block_index}.033
<SBW (nm)> , 1.00
<Energy> , 113.00
<Current Wavelength> , 500.00
<Cycle Count> , 4
<Cycle Time> , 0:46"""


def write_export(path, spectra, with_metadata=True, with_column_names=True):
    """
    Write a synthetic Cary WinUV export.

    Parameters
    ----------
    path : Path
        Output file path.
    spectra : list[tuple[str, list[float]]]
        ``[(spectrum_name, values), ...]``; *values* must match *WAVELENGTHS*
        in length (use ``None`` for a blank cell).
    with_metadata : bool
        Append the per-spectrum metadata blocks.
    with_column_names : bool
        Write the column-name line ("Wavelength (nm),Abs,...").
    """
    lines = []
    lines.append("".join(f"{name},," for name, _ in spectra))
    if with_column_names:
        lines.append("".join("Wavelength (nm),Abs," for _ in spectra))
    for i, wavelength in enumerate(WAVELENGTHS):
        cells = []
        for _, values in spectra:
            value = values[i]
            cells.append(f"{wavelength},{'' if value is None else value}")
        lines.append(",".join(cells) + ",")
    if with_metadata:
        for block_index, (name, _) in enumerate(spectra):
            lines.append("")
            lines.append(f"{name},")
            lines.append(name)
            lines.append(
                _METADATA_TEMPLATE.format(
                    collection_time=f"2026/9/23 14:3{block_index}:09",
                    block_index=block_index,
                )
            )
    lines.extend(["", ""])
    path.write_bytes("\r\n".join(lines).encode("utf-8"))
    return path


def values_from(offset):
    """A distinct, easy-to-check absorbance list."""
    return [round(0.1 + offset + i / 1000, 6) for i in range(len(WAVELENGTHS))]


@pytest.fixture
def export_file(tmp_path):
    spectra = [("5705-ox1_1", values_from(0)), ("5705-re1_1", values_from(0.05))]
    return write_export(tmp_path / "5705.csv", spectra)


class TestCaryAbsSpecCollectionFromCsv:

    def test_reads_every_spectrum(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)

        assert len(collection) == 2
        assert collection.signal_names == ["5705-ox1_1", "5705-re1_1"]
        assert collection.visible_signal_names == ["5705-ox1_1", "5705-re1_1"]
        assert collection.name == "5705"

    def test_signal_type_and_data(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)
        signal = collection["5705-ox1_1"]

        assert isinstance(signal, CaryAbsSpec)
        assert list(signal.data.columns) == ["Wavelength (nm)", "10-mm Absorbance"]
        assert len(signal.data) == len(WAVELENGTHS)
        # 波长轴存为升序 (导出文件本身是 600 → 590 递减)
        assert signal.data.iloc[0].tolist() == [590.0, values_from(0)[-1]]
        assert signal.data.iloc[-1].tolist() == [600.0, values_from(0)[0]]
        # 两条光谱的数据互不串列
        assert collection["5705-re1_1"].data.iloc[-1, 1] == values_from(0.05)[0]

    def test_annotations(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)

        assert collection.axis_annotation.name == "Wavelength"
        assert collection.axis_annotation.unit == "nm"
        assert collection.value_annotation.name == "10-mm Absorbance"
        assert collection.value_annotation.unit is None
        assert collection["5705-re1_1"].axis_annotation.limit == (590.0, 600.0)

    def test_optical_path_length_labels_the_absorbance_column(self, export_file):
        """光程参数只改标注, 不改数据 (10 mm 与 1 mm 读出同样的吸光度值)。"""
        collection_10mm = CaryAbsSpecCollection.from_csv(export_file)
        collection_1mm = CaryAbsSpecCollection.from_csv(
            export_file, optical_path_length_mm=1
        )

        assert collection_1mm.value_annotation.label == "1-mm Absorbance"
        assert list(collection_1mm["5705-ox1_1"].data.columns) == [
            "Wavelength (nm)",
            "1-mm Absorbance",
        ]
        assert collection_1mm.optical_path_length_mm == 1
        assert collection_10mm.optical_path_length_mm == 10
        assert (
            collection_1mm["5705-ox1_1"].data.iloc[:, 1].tolist()
            == collection_10mm["5705-ox1_1"].data.iloc[:, 1].tolist()
        )

    def test_non_positive_optical_path_length_raises(self, export_file):
        with pytest.raises(ValueError, match="optical_path_length_mm should be > 0"):
            CaryAbsSpecCollection.from_csv(export_file, optical_path_length_mm=0)

    def test_custom_collection_name(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file, name="Pyridine assay")
        assert collection.name == "Pyridine assay"


class TestCaryAbsSpecMetadata:

    def test_metadata_is_attached_per_spectrum(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)
        signal = collection["5705-ox1_1"]

        assert signal.instrument == "Cary 100"
        assert signal.collection_time is not None
        assert signal.metadata["Start (nm)"] == "600.00"
        assert signal.metadata["Stop (nm)"] == "500.00"
        assert signal.metadata["UV-Vis Data Interval (nm)"] == "1.000"
        assert signal.metadata["UV-Vis SBW (nm)"] == "1.0"
        assert signal.metadata["Beam Mode"] == "Double"
        assert signal.metadata["Cycle Count"] == "10"
        assert signal.metadata["Method Name"] == "E:\\s642\\20260923\\260923.MSW"
        assert signal.metadata["Date/Time stamp"] == "2026/9/23 14:19:57"
        # 元数据块末尾的 "[Time] , 0.033" / "<Cycle Time> , 0:46"
        assert signal.metadata["[Time]"] == "0.033"
        assert signal.metadata["<Cycle Time>"] == "0:46"
        assert signal.metadata["<Current Wavelength>"] == "500.00"
        # 自由文本部分保留成列表
        assert signal.metadata["Method Modifications"] == [
            "X Start nm Changed: 2026/9/23 13:51:05, Old: 800.00, New: 600.00",
            "Saved as E:\\s642\\20260923\\5705-ox-1.BSW",
        ]

    def test_collection_metadata_mapping(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)

        metadata = collection.metadata
        assert list(metadata.keys()) == ["5705-ox1_1", "5705-re1_1"]
        assert metadata["5705-ox1_1"]["Instrument"] == "Cary 100"

    def test_metadata_blocks_are_matched_in_file_order(self, tmp_path):
        """
        元数据块按文件顺序对应光谱, 而不是按名字 —— Cary 里同名光谱的数据可能不同。
        """
        spectra = [("dup", values_from(0)), ("dup", values_from(0.05))]
        export_file = write_export(tmp_path / "dup.csv", spectra)

        collection = CaryAbsSpecCollection.from_csv(export_file)

        assert collection.signal_names == ["dup", "dup(1)"]
        assert collection["dup"].data.iloc[-1, 1] == values_from(0)[0]
        assert collection["dup(1)"].data.iloc[-1, 1] == values_from(0.05)[0]
        # 元数据块按文件顺序对应, 第一个块 (14:30:09) 属于第一条光谱
        assert collection["dup"].collection_time == "2026/9/23 14:30:09"
        assert collection["dup(1)"].collection_time == "2026/9/23 14:31:09"
        assert collection["dup"].metadata["[Time]"] == "0.033"
        assert collection["dup(1)"].metadata["[Time]"] == "1.033"

    def test_missing_metadata_block_falls_back_to_name_matching(self, tmp_path):
        spectra = [("a", values_from(0)), ("b", values_from(0.05))]
        export_file = write_export(tmp_path / "partial.csv", spectra)
        # 删掉 "b" 的元数据块 (其块起始行是 "b," / "b")
        lines = export_file.read_text().splitlines()
        start = lines.index("b,")
        end = len(lines) - 2
        export_file.write_bytes("\r\n".join(lines[:start] + lines[end:]).encode("utf-8"))

        with pytest.warns(UserWarning, match="metadata is matched by spectrum name"):
            collection = CaryAbsSpecCollection.from_csv(export_file)

        assert collection["a"].instrument == "Cary 100"
        assert collection["b"].metadata == {}


class TestAscendingAxis:
    """
    WinUV 导出是 Start (nm) → Stop (nm) **递减**, 但读入后波长轴必须是升序:
    库内按轴取值的运算都走 ``np.interp`` (要求 ``xp`` 升序), 降序轴会让它们
    静默返回错值 (任何波长都返回最后一个数据点), 且不报错。
    """

    def test_axis_is_stored_ascending(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)

        axis = collection["5705-ox1_1"].axis.tolist()

        assert axis == list(range(590, 601))

    def test_getitem_returns_the_value_at_that_wavelength(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)
        signal = collection["5705-ox1_1"]
        by_wavelength = dict(zip(WAVELENGTHS, values_from(0)))

        for wavelength in (590, 595, 600):
            assert signal[wavelength] == pytest.approx(by_wavelength[wavelength])

    def test_get_peak_between_finds_the_true_peak(self, tmp_path):
        values = [0.2] * len(WAVELENGTHS)
        values[WAVELENGTHS.index(595)] = 0.5
        export_file = write_export(tmp_path / "peak.csv", [("peak", values)])
        signal = CaryAbsSpecCollection.from_csv(export_file)["peak"]

        assert signal.get_peak_between(590, 600) == pytest.approx((595.0, 0.5))
        assert signal.get_peak_between(592, 596) == pytest.approx((595.0, 0.5))
        # 峰在窗口外时不应被取到 (取窗口内第一个最大点)
        assert signal.get_peak_between(590, 593) == pytest.approx((590.0, 0.2))

    def test_slice_value_by_axis_follows_the_axis_order(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)
        signal = collection["5705-ox1_1"]
        values = values_from(0)

        sliced = signal.slice_value_by_axis(592, 594)

        # 592 / 593 / 594 nm 三点 (在导出文件里是第 9 / 8 / 7 行)
        assert sliced.tolist() == pytest.approx([values[8], values[7], values[6]])

    def test_difference_spectrum_aligns_on_the_ascending_axis(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)

        difference = collection["5705-re1_1"] - collection["5705-ox1_1"]

        # values_from(0.05) - values_from(0) 处处等于 0.05
        assert difference.value.to_numpy() == pytest.approx([0.05] * len(WAVELENGTHS))


class TestCaryAbsSpecEdgeCases:

    def test_blank_cells_are_dropped_with_warning(self, tmp_path):
        """
        扫描中断时光谱会缺尾部数据点 (导出里是空白单元格, 如 49_8.csv),
        空白点应被丢弃而不是变成 NaN。
        """
        truncated = values_from(0.05)
        truncated[-4:] = [None] * 4
        spectra = [("complete", values_from(0)), ("truncated", truncated)]
        export_file = write_export(tmp_path / "truncated.csv", spectra)

        with pytest.warns(UserWarning, match="4 missing data point"):
            collection = CaryAbsSpecCollection.from_csv(export_file)

        signal = collection["truncated"]
        assert len(signal.data) == len(WAVELENGTHS) - 4
        # 丢掉的是扫描尾部 (593~590 nm), 剩下的最小波长是 594 nm
        assert signal.data.iloc[0, 0] == 594.0
        assert signal.data.iloc[-1, 0] == 600.0
        assert not signal.data.isna().to_numpy().any()

    def test_no_spectrum_in_header_raises(self, tmp_path):
        export_file = tmp_path / "empty.csv"
        export_file.write_bytes("\r\n\r\n".encode("utf-8"))

        with pytest.raises(ValueError):
            CaryAbsSpecCollection.from_csv(export_file)

    def test_not_a_cary_export_raises(self, tmp_path):
        export_file = tmp_path / "other.csv"
        export_file.write_bytes(b"Wavelength,Abs\r\n600,0.1\r\n599,0.2\r\n")

        with pytest.raises(ValueError, match="Not a Cary WinUV export"):
            CaryAbsSpecCollection.from_csv(export_file)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            CaryAbsSpecCollection.from_csv(tmp_path / "nope.csv")

    def test_plot_smoke(self, export_file):
        collection = CaryAbsSpecCollection.from_csv(export_file)
        collection.set_default_annotations()

        fig, ax = collection.plot()

        assert ax.get_xlabel() == "Wavelength (nm)"
        assert ax.get_ylabel() == "10-mm Absorbance"
        assert len(ax.get_lines()) == 2
        assert ax.get_title() == "5705"
