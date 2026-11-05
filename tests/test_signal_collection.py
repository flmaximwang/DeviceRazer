"""
Tests for :class:`dvrazer.abstract.signal_collection.SignalCollection`.

Run with::

    /Applications/DVRazer/bin/python -m pytest tests/test_signal_collection.py -q

Covers the index-cache / ``visible_signal_names`` bookkeeping of
``__delitem__`` (bug 2) and ``append`` / ``__setitem__`` (bug 11).
"""

import sys

sys.path.append("..")

import pandas as pd
import pytest

from dvrazer.abstract.signal import Signal
from dvrazer.abstract.signal_collection import SignalCollection


def make_signal(name: str, values=(1.0, 2.0)) -> Signal:
    """Build a minimal signal usable in a SignalCollection."""
    return Signal(
        data=pd.DataFrame({"axis": [0.0, 1.0], "value": list(values)}),
        name=name,
        description_annotations=[],
    )


def make_collection(*names: str, visible: bool = True, name="collection") -> SignalCollection:
    signals = [make_signal(signal_name) for signal_name in names]
    return SignalCollection(
        signals=signals,
        name=name,
        visible_signal_names=[signal.name for signal in signals] if visible else None,
    )


class TestDelItem:
    """Bug 2: deleting a signal must refresh the index cache and visible names."""

    def test_remaining_signals_are_found_by_name(self):
        collection = make_collection("a", "b", "c")
        del collection["a"]

        assert collection.signal_names == ["b", "c"]
        assert len(collection) == 2
        assert "a" not in collection
        assert "b" in collection
        assert "c" in collection
        assert collection["b"].name == "b"
        assert collection["c"].name == "c"
        assert collection.index("b") == 0
        assert collection.index("c") == 1

    def test_delete_in_non_deletion_order(self):
        collection = make_collection("a", "b", "c")
        del collection["b"]

        assert collection.signal_names == ["a", "c"]
        assert collection["a"].name == "a"
        assert collection["c"].name == "c"

        del collection["a"]
        assert collection.signal_names == ["c"]
        assert collection["c"].name == "c"

    def test_delete_then_delete_another_signal_uses_fresh_indices(self):
        """A stale index cache used to delete the wrong signal on the next delete."""
        collection = make_collection("a", "b", "c")
        del collection["a"]
        del collection["b"]

        assert collection.signal_names == ["c"]
        assert collection["c"].name == "c"

    def test_deleted_name_is_removed_from_visible_signal_names(self):
        collection = make_collection("a", "b", "c")
        del collection["a"]

        assert collection.visible_signal_names == ["b", "c"]

    def test_visible_order_of_the_remaining_signals_is_preserved(self):
        collection = make_collection("a", "b", "c")
        del collection["b"]

        assert collection.visible_signal_names == ["a", "c"]

    def test_delete_then_lookup_of_deleted_name_raises(self):
        collection = make_collection("a", "b", "c")
        del collection["a"]

        with pytest.raises(KeyError):
            collection["a"]
        with pytest.raises(KeyError):
            collection.index("a")

    def test_delete_missing_name_raises(self):
        collection = make_collection("a", "b")
        with pytest.raises(KeyError):
            del collection["missing"]


class TestVisibleSignalNamesOnAdd:
    """Bug 11: added signals must become visible."""

    def test_append_adds_the_signal_name_to_visible_signal_names(self):
        collection = make_collection("a")
        collection.append(make_signal("b"))

        assert collection.signal_names == ["a", "b"]
        assert collection.visible_signal_names == ["a", "b"]
        assert collection["b"].name == "b"

    def test_append_initializes_visible_signal_names_when_they_are_none(self):
        collection = make_collection("a", visible=False)
        assert collection.visible_signal_names is None

        collection.append(make_signal("b"))

        assert collection.visible_signal_names == ["a", "b"]

    def test_append_duplicate_name_raises_and_keeps_the_collection_unchanged(self):
        collection = make_collection("a")
        with pytest.raises(KeyError):
            collection.append(make_signal("a"))

        assert collection.signal_names == ["a"]
        assert collection.visible_signal_names == ["a"]

    def test_setitem_with_a_new_name_adds_it_to_visible_signal_names(self):
        collection = make_collection("a")
        collection["b"] = make_signal("ignored")

        assert collection.signal_names == ["a", "b"]
        assert collection.visible_signal_names == ["a", "b"]
        assert collection["b"].name == "b"  # renamed after the assignment key

    def test_setitem_with_a_new_name_initializes_visible_signal_names(self):
        collection = make_collection("a", visible=False)
        collection["b"] = make_signal("ignored")

        assert collection.visible_signal_names == ["a", "b"]

    def test_setitem_with_an_existing_name_does_not_duplicate_the_visible_name(self):
        collection = make_collection("a", "b")
        collection["a"] = make_signal("replacement")

        assert collection.signal_names == ["a", "b"]
        assert collection.visible_signal_names == ["a", "b"]
        assert collection["a"].name == "a"

    def test_setitem_does_not_make_a_hidden_signal_visible_again(self):
        collection = make_collection("a", "b")
        collection.visible_signal_names.remove("a")

        collection["a"] = make_signal("replacement")

        assert collection.visible_signal_names == ["b"]

    def test_append_after_delete_keeps_the_name_addressable(self):
        collection = make_collection("a", "b")
        del collection["a"]
        collection.append(make_signal("c"))

        assert collection.signal_names == ["b", "c"]
        assert collection.visible_signal_names == ["b", "c"]
        assert collection["c"].name == "c"


class TestIndexCache:
    """The index cache must stay consistent across mutations."""

    def test_lookups_after_rename(self):
        collection = make_collection("a", "b", "c")
        collection.rename_signal("b", "renamed")

        assert collection["renamed"].name == "renamed"
        assert collection["c"].name == "c"
        assert collection.visible_signal_names == ["a", "renamed", "c"]

    def test_lookups_after_remove_signal(self):
        collection = make_collection("a", "b", "c")
        collection.remove_signal("b")

        assert collection["c"].name == "c"
        assert collection.visible_signal_names == ["a", "c"]

    def test_merge_result_supports_append_and_delete(self):
        first = make_collection("a", name="first")
        second = make_collection("b", name="second")
        merged = SignalCollection.merge([first, second])
        assert merged.signal_names == ["a", "b"]

        merged.append(make_signal("c"))
        assert merged.visible_signal_names == ["a", "b", "c"]

        del merged["a"]
        assert merged["b"].name == "b"
        assert merged["c"].name == "c"
        assert merged.visible_signal_names == ["b", "c"]
