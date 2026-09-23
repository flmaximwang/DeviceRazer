import sys

sys.path.append("..")

import pandas as pd

from instrumental_data_analyzer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_Group,
    SoftMaxPro_Plate_Endpoint,
    SoftMaxPro_Project,
)


def test_read_endpoint_plate_from_bca_export():
    """A BCA export contains a Plate block (Endpoint/Absorbance 96-well) plus
    Group blocks. The Endpoint plate must parse into a MultiWellPlate."""
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    assert len(project.blocks) == 3
    assert len(project.plates) == 1
    assert len(project.groups) == 2

    plate = project["Plate1"]
    assert isinstance(plate, SoftMaxPro_Plate_Endpoint)
    assert plate.data.shape == (8, 12)
    assert plate["A", 1] == 0.1021
    assert plate["A", 3] == 0.0998


def test_read_groups_from_bca_export():
    """Group blocks (standards + sample groups) are exposed via group()."""
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    assert [g.name for g in project.groups] == ["Standards", "SampleA"]

    standards = project.group("Standards")
    assert isinstance(standards, SoftMaxPro_Group)
    # 4 standards x 3 replicate wells
    assert len(standards.data) == 12
    # forward-filled sample number
    assert list(standards.data["Sample"]) == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
    # numeric columns converted, well IDs kept as strings
    assert standards.data["Conc"].dtype == "float64"
    assert standards.data["Value"].dtype == "float64"
    assert pd.api.types.is_string_dtype(standards.data["Wells"])
    assert float(standards.data["Conc"].iloc[0]) == 0.000
    assert float(standards.data["Value"].iloc[0]) == 0.102
    assert float(standards.data["MeanValue"].iloc[0]) == 0.101

    sample = project.group("SampleA")
    assert len(sample.data) == 3
    assert list(sample.data["Well"]) == ["A4", "B4", "C4"]
    assert list(sample.data["Values"]) == [0.100, 0.092, 0.091]
    assert list(sample.data["Result"]) == [-0.039, -0.048, -0.049]


def test_group_column_formula_table():
    """The Group Column section is parsed into a formula table."""
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    standards = project.group("Standards")
    assert list(standards.columns["Column"]) == [1, 2, 5, 6]
    assert list(standards.columns["Formula"]) == [
        "!SampleNames",
        "!Concentration",
        "!WellValues",
        "Average(Value)",
    ]


def test_group_summaries():
    """The Group Summaries section (e.g. MinStd/MaxStd) is parsed."""
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    standards = project.group("Standards")
    assert len(standards.summaries) == 2
    assert str(standards.summaries.iloc[0, 0]) == "MinStd"
    assert str(standards.summaries.iloc[1, 0]) == "MaxStd"
    # sample group has no summaries
    assert len(project.group("SampleA").summaries) == 0


def test_getitem_finds_group_by_name():
    """__getitem__ falls back to group names."""
    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    assert project["Standards"].name == "Standards"


def test_missing_group_raises_keyerror():
    import pytest

    project = SoftMaxPro_Project.read_txt("tests/data/softmax_endpoint_bca.txt")
    with pytest.raises(KeyError):
        project.group("NoSuchGroup")
