import sys

sys.path.append("..")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from scipy import stats

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Project,
    SoftMaxPro_Protocol,
)


def _standards():
    return {
        "name": "standards",
        "type": "standards",
        "fit": "linear",
        "series": [
            {"value": 0.0, "unit": "mg/ml", "wells": ["A1", "A2", "A3"]},
            {"value": 0.125, "unit": "mg/ml", "wells": ["B1", "B2", "B3"]},
            {"value": 0.250, "unit": "mg/ml", "wells": ["C1", "C2", "C3"]},
            {"value": 2.000, "unit": "mg/ml", "wells": ["D1", "D2", "D3"]},
        ],
    }


def _plate():
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    return project["Plate1"]


def _protocol():
    sample = {"name": "SampleA", "type": "unknown", "wells": ["A4", "B4", "C4"]}
    protocol = SoftMaxPro_Protocol([_standards(), sample])
    return protocol, _plate()


def _dilution_standards():
    """标准品最高点用 G1-G3 (均值 OD ≈ 1.338), 使量程覆盖 1× 梯度孔 E4/E5。"""
    return {
        "name": "standards",
        "type": "standards",
        "fit": "linear",
        "series": [
            {"value": 0.0, "unit": "mg/ml", "wells": ["A1", "A2", "A3"]},
            {"value": 0.125, "unit": "mg/ml", "wells": ["B1", "B2", "B3"]},
            {"value": 0.250, "unit": "mg/ml", "wells": ["C1", "C2", "C3"]},
            {"value": 2.000, "unit": "mg/ml", "wells": ["G1", "G2", "G3"]},
        ],
    }


def _elution_group():
    return {
        "name": "Elution",
        "type": "unknown_dilution",
        "series": [
            {"dilution_factor": 1.0, "wells": ["E4", "E5"]},
            {"dilution_factor": 2.0, "wells": ["B4", "C4", "D4"]},
        ],
    }


def _dilution_protocol():
    """Elution 组: 1× = E4/E5 (量程内), 2× = B4/C4/D4 (低于 MinStd, 超量程)。"""
    protocol = SoftMaxPro_Protocol([_dilution_standards(), _elution_group()])
    return protocol, _plate()


def test_apply_returns_self_and_computes_results():
    protocol, plate = _protocol()
    assert protocol.apply(plate) is protocol

    results = protocol.results
    assert list(results["Well"]) == ["A4", "B4", "C4"]
    assert list(results["Group"]) == ["SampleA"] * 3
    assert list(results["Unit"]) == ["mg/ml"] * 3
    # A4 raw OD from the synthetic plate is 0.0999
    assert np.isclose(float(results.loc[0, "Value"]), 0.0999)


def test_results_carry_group_statistics():
    """每组第一行带 MeanResult/Std.Dev./CV%, 与 SoftMax Pro Group 区块一致。"""
    protocol, plate = _protocol()
    protocol.apply(plate)

    results = protocol.results
    assert "MeanResult" in results.columns
    assert "Std.Dev." in results.columns
    assert "CV%" in results.columns
    # 该组只有第一行有统计, 其余行为 NaN
    assert np.isfinite(results.loc[0, "MeanResult"])
    assert np.isnan(results.loc[1, "MeanResult"])
    assert np.isnan(results.loc[2, "MeanResult"])
    # MeanResult == 组内浓度均值
    expected_mean = float(results["Concentration"].mean())
    assert np.isclose(float(results.loc[0, "MeanResult"]), expected_mean)


def test_summary_table():
    """summary 是每组一行的汇总统计表。"""
    protocol, plate = _protocol()
    protocol.apply(plate)

    summary = protocol.summary
    assert list(summary["Group"]) == ["SampleA"]
    assert summary.loc[0, "n"] == 3
    # MeanConcentration 等于组内浓度均值
    results = protocol.results
    assert np.isclose(
        float(summary.loc[0, "MeanConcentration"]),
        float(results["Concentration"].mean()),
    )
    assert np.isclose(
        float(summary.loc[0, "MeanValue"]),
        float(results["Value"].mean()),
    )


def test_standard_curve_linear_fit():
    protocol, plate = _protocol()
    protocol.apply(plate)

    std = protocol.standards_data
    assert list(std["Conc"]) == [0.0, 0.125, 0.250, 2.000]
    # mean of replicate wells
    assert np.isclose(float(std.loc[0, "Value"]), 0.1014)

    fit = protocol.fit_result
    # A4 OD 0.100 back-calculated concentration
    conc_a4 = (float(protocol.results.loc[0, "Value"]) - fit.intercept) / fit.slope
    assert np.isclose(float(protocol.results.loc[0, "Concentration"]), conc_a4)


def test_standard_curve_figure():
    protocol, plate = _protocol()
    protocol.apply(plate)
    fig = protocol.standard_curve
    assert fig is not None
    assert len(fig.axes) == 1
    assert "Standard curve" in fig.axes[0].get_title()
    # 图例包含每个未知组
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "SampleA" in labels


def test_plot_standard_curve_groups_filter():
    """plot_standard_curve(groups=...) 只绘制指定的未知组。"""
    protocol, plate = _protocol()
    protocol.apply(plate)

    # 默认 all: 图例包含全部未知组
    all_labels = [
        t.get_text() for t in protocol.plot_standard_curve().axes[0].get_legend().get_texts()
    ]
    assert "SampleA" in all_labels

    # 指定单个组名 (字符串)
    single_labels = [
        t.get_text()
        for t in protocol.plot_standard_curve(groups="SampleA").axes[0].get_legend().get_texts()
    ]
    assert "SampleA" in single_labels
    # 未知组名在图例中恰好出现一次 (标准线 "linear fit"/"standards" 始终存在)
    assert single_labels.count("SampleA") == 1

    # 无效组名抛 KeyError
    import pytest

    with pytest.raises(KeyError):
        protocol.plot_standard_curve(groups="NoSuchGroup")


def test_getitem_returns_group_subset():
    protocol, plate = _protocol()
    protocol.apply(plate)
    subset = protocol["SampleA"]
    assert list(subset["Well"]) == ["A4", "B4", "C4"]
    # 子表首行同样带统计列
    assert np.isfinite(subset.loc[0, "MeanResult"])


def test_requires_standards_group():
    protocol = SoftMaxPro_Protocol([])
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    try:
        protocol.apply(project["Plate1"])
        assert False, "should raise"
    except ValueError as e:
        assert "standards group" in str(e)


def test_access_before_apply_raises():
    protocol, _ = _protocol()
    with pytest.raises(RuntimeError):
        _ = protocol.results
    with pytest.raises(RuntimeError):
        _ = protocol.summary
    with pytest.raises(RuntimeError):
        _ = protocol.standard_curve
    with pytest.raises(RuntimeError):
        _ = protocol.standards_data
    with pytest.raises(RuntimeError):
        _ = protocol.fit_result


# --- unknown_dilution: 稀释梯度组 ------------------------------------------


def test_unknown_dilution_raw_concentration_and_adjusted_result():
    """镜像 SoftMax Unk_Dilution: 逐孔 Concentration 未校正, 梯度首行给 Dilution/AdjResult。"""
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    results = protocol.results
    assert list(results["Well"]) == ["E4", "E5", "B4", "C4", "D4"]
    assert list(results["Group"]) == ["Elution"] * 5

    fit = protocol.fit_result
    # 逐孔 Concentration = 原始反算浓度 (未乘稀释倍数)
    od_e4 = float(results.loc[0, "Value"])
    assert np.isclose(od_e4, plate["E", 4])
    assert np.isclose(
        float(results.loc[0, "Concentration"]), (od_e4 - fit.intercept) / fit.slope
    )
    assert all(results["Unit"] == "mg/ml")

    # 1× 梯度首行 (E4): Dilution 1.0, AdjResult == MeanResult
    assert np.isclose(float(results.loc[0, "Dilution"]), 1.0)
    mean_1x = float(results.loc[0, "MeanResult"])
    assert np.isclose(mean_1x, float(results.loc[:1, "Concentration"].mean()))
    assert np.isclose(float(results.loc[0, "AdjResult"]), mean_1x)

    # 2× 梯度首行 (B4, 第 3 行): Dilution 2.0, AdjResult == MeanResult × 2
    assert np.isclose(float(results.loc[2, "Dilution"]), 2.0)
    mean_2x = float(results.loc[2, "MeanResult"])
    assert np.isclose(mean_2x, float(results.loc[2:4, "Concentration"].mean()))
    assert np.isclose(float(results.loc[2, "AdjResult"]), mean_2x * 2.0)

    # 同梯度其余行: 统计列与 Dilution/AdjResult 均为 NaN
    for col in ("MeanResult", "Std.Dev.", "CV%", "Dilution", "AdjResult"):
        assert np.isnan(results.loc[1, col])
        assert np.isnan(results.loc[3, col])


def test_unknown_dilution_summary_one_row_per_level():
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    summary = protocol.summary
    assert list(summary["Group"]) == ["Elution", "Elution"]
    assert list(summary["Dilution"]) == [1.0, 2.0]
    assert list(summary["n"]) == [2, 3]
    # AdjResult = MeanConcentration × Dilution
    for _, row in summary.iterrows():
        assert np.isclose(row["AdjResult"], row["MeanConcentration"] * row["Dilution"])
    # MeanConcentration 始终是未校正值 (与 results 的逐孔浓度一致)
    assert np.isclose(
        float(summary.loc[0, "MeanConcentration"]),
        float(protocol.results.loc[:1, "Concentration"].mean()),
    )


def test_unknown_dilution_in_range_flag():
    """InRange 对应 SoftMax 的 R 列: 吸光度落在标准品 MinStd..MaxStd 之外则 False。"""
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    results = protocol.results
    assert results["InRange"].dtype == bool
    # 1× (E4=1.035, E5=0.8942) 落在量程 [0.1014, 1.827] 内
    assert list(results.loc[:1, "InRange"]) == [True, True]
    # 2× (B4=0.0921, C4=0.0913, D4=0.0926) 低于 MinStd
    assert list(results.loc[2:4, "InRange"]) == [False, False, False]

    summary = protocol.summary
    assert list(summary["nInRange"]) == [2, 0]


def test_plain_unknown_group_has_no_dilution():
    """普通 unknown 组: summary 每行一个组, Dilution/AdjResult 为 NaN, nInRange 生效。"""
    protocol, plate = _protocol()
    protocol.apply(plate)

    summary = protocol.summary
    assert list(summary["Group"]) == ["SampleA"]
    assert np.isnan(summary.loc[0, "Dilution"])
    assert np.isnan(summary.loc[0, "AdjResult"])
    # A4=0.0999 < MinStd=0.1014 → 超量程
    assert summary.loc[0, "nInRange"] == 0


def test_unknown_dilution_plot_labels_carry_dilution():
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    labels = [
        t.get_text()
        for t in protocol.standard_curve.axes[0].get_legend().get_texts()
    ]
    assert "Elution 1×" in labels
    assert "Elution 2×" in labels
    # 按组名筛选仍然可用 (一个组含多个梯度)
    filtered = [
        t.get_text()
        for t in protocol.plot_standard_curve(groups=["Elution"])
        .axes[0]
        .get_legend()
        .get_texts()
    ]
    assert filtered.count("Elution 1×") == 1
    assert filtered.count("Elution 2×") == 1


def test_getitem_returns_all_dilution_levels():
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)
    subset = protocol["Elution"]
    assert list(subset["Well"]) == ["E4", "E5", "B4", "C4", "D4"]


def test_unknown_dilution_validation_errors():
    plate = _plate()
    # 缺少 series
    protocol = SoftMaxPro_Protocol(
        [_standards(), {"name": "Elution", "type": "unknown_dilution"}]
    )
    with pytest.raises(ValueError, match="needs a 'series'"):
        protocol.apply(plate)
    # series 项缺 dilution_factor
    protocol = SoftMaxPro_Protocol(
        [
            _standards(),
            {
                "name": "Elution",
                "type": "unknown_dilution",
                "series": [{"wells": ["E4"]}],
            },
        ]
    )
    with pytest.raises(ValueError, match="dilution_factor"):
        protocol.apply(plate)
    # series 项缺 wells
    protocol = SoftMaxPro_Protocol(
        [
            _standards(),
            {
                "name": "Elution",
                "type": "unknown_dilution",
                "series": [{"dilution_factor": 2.0}],
            },
        ]
    )
    with pytest.raises(ValueError, match="'wells'"):
        protocol.apply(plate)
    # 未知组类型
    protocol = SoftMaxPro_Protocol(
        [_standards(), {"name": "Elution", "type": "dilution", "wells": ["E4"]}]
    )
    with pytest.raises(ValueError, match="Unsupported group type"):
        protocol.apply(plate)


# --- 稀释线性回归: plot_unknown_dilution_curve ------------------------------


def test_dilution_fit_matches_manual_linregress():
    """dilution_fit = 反算浓度 vs 1/dilution 的线性回归 (斜率 = 原始样品浓度)。"""
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    fits = protocol.dilution_fit
    assert list(fits) == ["Elution"]

    summary = protocol.summary
    expected = stats.linregress(
        1.0 / summary["Dilution"].to_numpy(dtype=float),
        summary["MeanConcentration"].to_numpy(dtype=float),
    )
    fit = fits["Elution"]
    assert np.isclose(fit.slope, expected.slope)
    assert np.isclose(fit.intercept, expected.intercept)
    # 只有 2 个稀释梯度时自由度为 0，linregress 的 pvalue (及 stderr) 为 nan，
    # 因此这里允许 nan == nan；斜率/截距断言仍然验证回归数学正确。
    assert np.isclose(fit.pvalue, expected.pvalue, equal_nan=True)


def test_summary_carries_fitted_concentration():
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    summary = protocol.summary
    assert "FittedConcentration" in summary.columns
    expected = protocol.dilution_fit["Elution"].slope
    # 同一稀释组的每个梯度行都填同一个回归斜率
    assert np.allclose(summary["FittedConcentration"], expected)


def test_plain_unknown_group_has_nan_fitted_concentration():
    protocol, plate = _protocol()
    protocol.apply(plate)
    summary = protocol.summary
    assert np.isnan(summary.loc[0, "FittedConcentration"])
    # 非稀释组不出现在 dilution_fit 里
    assert protocol.dilution_fit == {}


def test_plot_unknown_dilution_curve_contents():
    protocol, plate = _dilution_protocol()
    protocol.apply(plate)

    fig = protocol.plot_unknown_dilution_curve()
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Relative concentration (1/dilution)"
    assert "Back-calculated concentration (mg/ml)" == ax.get_ylabel()

    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert "Elution (mean ± SD)" in labels
    assert "Elution linear fit" in labels

    # 图注给出回归方程、R² 与 "slope = 原始浓度"
    notes = " ".join(t.get_text() for t in ax.texts)
    fit = protocol.dilution_fit["Elution"]
    assert f"y = {fit.slope:.4f}x" in notes
    assert f"R² = {fit.rvalue**2:.4f}" in notes
    assert "slope = " in notes and "(original concentration)" in notes

    # x 轴刻度 = 1/dilution, 标签写成稀释倍数
    assert sorted(t.get_text() for t in ax.get_xticklabels()) == ["1/1", "1/2"]
    plt.close(fig)


def test_plot_unknown_dilution_curve_multiple_groups():
    second = {
        "name": "FlowThrough",
        "type": "unknown_dilution",
        "series": [
            {"dilution_factor": 1.0, "wells": ["F4"]},
            {"dilution_factor": 2.0, "wells": ["F5"]},
        ],
    }
    protocol = SoftMaxPro_Protocol(
        [_dilution_standards(), _elution_group(), second]
    )
    protocol.apply(_plate())

    fig = protocol.plot_unknown_dilution_curve()
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "Elution linear fit" in labels and "FlowThrough linear fit" in labels
    assert list(protocol.dilution_fit) == ["Elution", "FlowThrough"]
    plt.close(fig)
    # groups 只画指定组
    only_fig = protocol.plot_unknown_dilution_curve(groups=["FlowThrough"])
    only_labels = [t.get_text() for t in only_fig.axes[0].get_legend().get_texts()]
    assert "FlowThrough linear fit" in only_labels
    assert "Elution linear fit" not in only_labels
    plt.close(only_fig)


def test_plot_unknown_dilution_curve_errors():
    # 没有 unknown_dilution 组 → ValueError
    protocol, plate = _protocol()
    protocol.apply(plate)
    with pytest.raises(ValueError, match="unknown_dilution"):
        protocol.plot_unknown_dilution_curve()

    # 未 apply → RuntimeError
    fresh = SoftMaxPro_Protocol([_dilution_standards(), _elution_group()])
    with pytest.raises(RuntimeError):
        fresh.plot_unknown_dilution_curve()
    with pytest.raises(RuntimeError):
        _ = fresh.dilution_fit

    # 指定非稀释组名 → KeyError
    dilution_protocol, dilution_plate = _dilution_protocol()
    dilution_protocol.apply(dilution_plate)
    with pytest.raises(KeyError, match="SampleA"):
        dilution_protocol.plot_unknown_dilution_curve(groups="SampleA")


def test_single_level_dilution_group_has_no_fit():
    """只有一个梯度时无法回归: dilution_fit 为 None, 绘图抛 ValueError。"""
    single = {
        "name": "Elution",
        "type": "unknown_dilution",
        "series": [{"dilution_factor": 2.0, "wells": ["E4", "E5"]}],
    }
    protocol = SoftMaxPro_Protocol([_dilution_standards(), single])
    protocol.apply(_plate())

    assert protocol.dilution_fit["Elution"] is None
    assert np.isnan(protocol.summary.loc[0, "FittedConcentration"])
    with pytest.raises(ValueError, match="fewer than 2 dilution levels"):
        protocol.plot_unknown_dilution_curve()
