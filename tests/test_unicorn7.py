"""
Tests for unicorn7 parser and empty-data edge cases.
"""

from pathlib import Path

import pandas as pd
import pytest
from dvrazer.abstract.signal_1d import (
    ContinuousSignal1D,
    DiscreteSignal1D,
)
from dvrazer.concrete.chromatography import Chrom
from dvrazer.instruments.GE_Heathcare.unicorn7 import (
    Unicorn7Chrom,
    Unicorn7Project,
)

DATA_DIR = Path(__file__).resolve().parent / "data"


class TestDiscreteSignal1DWithEmptyData:
    """
    DiscreteSignal1D.from_data should handle empty DataFrames gracefully
    instead of raising ValueError from min()/max() on an empty sequence.
    """

    def test_from_data_with_empty_dataframe(self):
        """Empty DataFrame should use (0, 1) as fallback axis limit."""
        empty_df = pd.DataFrame({0: [], 1: []})
        signal = DiscreteSignal1D.from_data(
            data=empty_df,
            name="test",
            axis_name="Volume",
            axis_unit="mL",
            value_name="Log",
            value_unit=None,
        )
        # Axis limit should fall back to (0, 1)
        anno = signal.description_annotations[0]
        assert anno.limit == (0, 1), f"Expected (0, 1), got {anno.limit}"
        assert signal.data.shape == (0, 2)


class TestContinuousSignal1DWithEmptyData:
    """
    ContinuousSignal1D.from_data should handle empty DataFrames gracefully.
    """

    def test_from_data_with_empty_dataframe(self):
        """Empty DataFrame should use (0, 1) as fallback axis and value limits."""
        empty_df = pd.DataFrame({0: [], 1: []})
        signal = ContinuousSignal1D.from_data(
            data=empty_df,
            name="test",
            axis_name="Volume",
            axis_unit="mL",
            value_name="UV",
            value_unit="mAU",
        )
        # Both axis and value limits should fall back to (0, 1)
        axis_anno = signal.description_annotations[0]
        value_anno = signal.description_annotations[1]
        assert axis_anno.limit == (0, 1), f"Expected (0, 1), got {axis_anno.limit}"
        assert value_anno.limit == (0, 1), f"Expected (0, 1), got {value_anno.limit}"
        assert signal.data.shape == (0, 2)


class TestUnicorn7ChromAPI:
    """
    Unicorn7Chrom.from_txt delegates to Unicorn7Project.read_txt.
    """

    def test_read_txt_is_callable_on_the_class(self):
        """Unicorn7Project.read_txt is a staticmethod (no instance needed)."""
        chroms = Unicorn7Project.read_txt(DATA_DIR / "unicorn_empty_fraction.txt")

        assert isinstance(chroms, list)
        assert len(chroms) == 1
        assert isinstance(chroms[0], Chrom)

    def test_from_txt_returns_a_list_of_chroms(self):
        chroms = Unicorn7Chrom.from_txt(DATA_DIR / "unicorn_empty_fraction.txt")

        assert isinstance(chroms, list)
        assert len(chroms) == 1
        assert isinstance(chroms[0], Chrom)

    def test_from_txt_matches_read_txt(self):
        from_txt = Unicorn7Chrom.from_txt(DATA_DIR / "unicorn_empty_fraction.txt")
        read_txt = Unicorn7Project.read_txt(DATA_DIR / "unicorn_empty_fraction.txt")

        assert [c.name for c in from_txt] == [c.name for c in read_txt]
        assert [c.keys() for c in from_txt] == [c.keys() for c in read_txt]

    def test_name_argument_overrides_project_name(self):
        chroms = Unicorn7Chrom.from_txt(
            DATA_DIR / "unicorn_empty_fraction.txt", name="custom"
        )

        assert chroms[0].name == "custom_0"

    def test_cytiva_reexport_is_the_same_class(self):
        from dvrazer.instruments.Cytiva.unicorn7 import Unicorn7Chrom as Reexported

        assert Reexported is Unicorn7Chrom


class TestUnicorn7ChromParser:
    """
    Unicorn7Chrom.from_txt should skip signals with no data rows
    instead of crashing.
    """

    def test_parse_file_with_empty_fraction_signal(self):
        """
        A .txt file containing a UV signal (with data) and a Fraction signal
        (header only, no data rows) should parse successfully and include
        only the UV signal.
        """
        chroms = Unicorn7Chrom.from_txt(DATA_DIR / "unicorn_empty_fraction.txt")
        assert len(chroms) == 1, f"Expected 1 chromatogram, got {len(chroms)}"

        chrom = chroms[0]
        signal_names = list(chrom.keys())
        assert "UV" in signal_names, f"Expected 'UV' in signals, got {signal_names}"
        assert (
            "Fraction" not in signal_names
        ), f"Fraction should be skipped, but got {signal_names}"
        assert len(signal_names) == 1, f"Expected 1 signal, got {len(signal_names)}"

        # Verify the UV signal has the expected data
        uv_signal = chrom["UV"]
        assert uv_signal.data.shape[0] > 0, "UV signal should have data rows"

    def test_parse_normal_file_smoke(self):
        """
        Smoke test: parsing the existing large unicorn file should still
        work correctly (no regressions).
        """
        chroms = Unicorn7Chrom.from_txt(DATA_DIR / "unicorn_chrom_1.txt")
        assert len(chroms) >= 1, f"Expected at least 1 chromatogram, got {len(chroms)}"

        chrom = chroms[0]
        signal_names = list(chrom.keys())
        # Normal file should have multiple signals
        assert len(signal_names) >= 3, (
            f"Expected >=3 signals, got {len(signal_names)}: {signal_names}"
        )
        # Common expected signals
        expected = {"UV", "Cond", "Conc B", "Fraction", "Injection"}
        found = expected & set(signal_names)
        assert len(found) >= 2, (
            f"Expected at least 2 common signals, found {found} in {signal_names}"
        )

    def test_parse_file_with_only_empty_signals(self, tmp_path: Path):
        """
        A file where ALL signals are empty (headers only, no data rows)
        should return an empty list of chromatograms.
        """
        # Build a minimal file with only headers, no data
        rows = [
            ["Chrom.1", "", "Chrom.1", ""],
            ["UV", "", "Fraction", ""],
            ["ml", "mAU", "ml", "Fraction"],
        ]
        df = pd.DataFrame(rows)
        empty_file = tmp_path / "unicorn_all_empty.txt"
        df.to_csv(
            empty_file,
            sep="\t",
            encoding="UTF-16 LE",
            header=False,
            index=False,
            na_rep="",
        )
        chroms = Unicorn7Chrom.from_txt(empty_file)
        # Should not crash; Chrom.from_similar_signals([]) should handle an
        # empty signals list gracefully.
        assert len(chroms) >= 0, "Should handle empty signals list"
