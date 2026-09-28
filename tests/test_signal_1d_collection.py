"""
Tests for Signal1DCollection.from_similar_signals and related constructors.
"""

import sys

sys.path.append("..")

import pandas as pd
import pytest
from dvrazer.abstract.signal_1d import ContinuousSignal1D
from dvrazer.abstract.signal_1d_collection import (
    Signal1DCollection,
    ContinuousSignal1DCollection,
)


def make_signal(name: str, values: list[float]) -> ContinuousSignal1D:
    """Build a small ContinuousSignal1D for testing."""
    df = pd.DataFrame({"axis": [0.0, 1.0, 2.0], "value": values})
    return ContinuousSignal1D.from_data(
        data=df,
        name=name,
        axis_name="Time",
        axis_unit="s",
        value_name="Absorbance",
        value_unit="AU",
    )


class TestFromSimilarSignals:
    def test_signals_are_copied(self):
        """Signals in the new collection must be copies of the originals."""
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])

        collection = Signal1DCollection.from_similar_signals([sig1, sig2])

        # The collection must not contain the original objects
        assert collection.signals[0] is not sig1
        assert collection.signals[1] is not sig2

    def test_modifying_collection_signal_does_not_affect_original(self):
        """Renaming / editing a signal inside the collection must not touch the original."""
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])

        collection = Signal1DCollection.from_similar_signals([sig1, sig2])

        # Rename the copy inside the collection
        collection.signals[0].name = "renamed"
        assert sig1.name == "sig1", "Original signal name must be unchanged"

        # Edit the value annotation of the copy
        collection.signals[0].value_annotation.unit = "mAU"
        assert (
            sig1.value_annotation.unit == "AU"
        ), "Original signal annotation must be unchanged"

        # Edit the underlying data of the copy
        collection.signals[0].data.iloc[0, 1] = 99.0
        assert sig1.data.iloc[0, 1] == 1.0, "Original signal data must be unchanged"

    def test_visible_signal_names_matches_signals(self):
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])

        collection = Signal1DCollection.from_similar_signals([sig1, sig2])
        assert collection.visible_signal_names == ["sig1", "sig2"]
        assert collection.signal_names == ["sig1", "sig2"]

    def test_signal_names_renames_copies(self):
        """signal_names renames the copies inside the collection, not the originals."""
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])

        collection = Signal1DCollection.from_similar_signals(
            [sig1, sig2], signal_names=["a", "b"]
        )
        assert collection.signal_names == ["a", "b"]
        assert collection.visible_signal_names == ["a", "b"]
        # Originals must be untouched
        assert sig1.name == "sig1"
        assert sig2.name == "sig2"

    def test_signal_names_wrong_length_raises(self):
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])

        with pytest.raises(ValueError):
            Signal1DCollection.from_similar_signals(
                [sig1, sig2], signal_names=["only_one"]
            )

    def test_merge_does_not_rename_original_signals(self):
        """merge with signal_renaming=True must rename only the copies."""
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])
        col1 = Signal1DCollection.from_similar_signals([sig1], name="col1")
        col2 = Signal1DCollection.from_similar_signals([sig2], name="col2")

        merged = Signal1DCollection.merge([col1, col2])

        assert merged.signal_names == ["col1_sig1", "col2_sig2"]
        assert sig1.name == "sig1", "merge must not rename original signals"
        assert sig2.name == "sig2", "merge must not rename original signals"
        assert col1.signals[0] is not merged.signals[0]

    def test_merge_signal_renaming_false(self):
        sig1 = make_signal("sig1", [1.0, 2.0, 3.0])
        sig2 = make_signal("sig2", [3.0, 2.0, 1.0])
        col1 = Signal1DCollection.from_similar_signals([sig1], name="col1")
        col2 = Signal1DCollection.from_similar_signals([sig2], name="col2")

        merged = Signal1DCollection.merge([col1, col2], signal_renaming=False)
        assert merged.signal_names == ["sig1", "sig2"]


class TestContinuousSignal1DCollection:
    def test_average_similar_signals_does_not_rename_originals(self):
        sig1 = make_signal("sample A1", [1.0, 2.0, 3.0])
        sig2 = make_signal("control B1", [3.0, 2.0, 1.0])
        collection = ContinuousSignal1DCollection.from_similar_signals([sig1, sig2])

        averaged = collection.average_similar_signals()

        # Single-signal groups are renamed inside the copy, not the original
        assert sig1.name == "sample A1", "Original signal name must be unchanged"
        assert averaged.signal_names == ["sample", "control"]
        assert averaged.signals[0] is not sig1
        assert averaged.signals[1] is not sig2
