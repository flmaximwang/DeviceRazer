"""
Tests for :class:`Nanodrop2000Workbook.from_tsv`.

Regression tests for the bug where ``from_tsv`` rewrote the input .tsv file,
popping one data row from its tail on every call.
"""

from pathlib import Path

import pytest

from dvrazer.instruments.ThermoFisher.nanodrop2000 import Nanodrop2000Workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_TSV = REPO_ROOT / "examples" / "nanodrop2000" / "protein-a280" / "example.tsv"


def _write_two_spectrum_tsv(path: Path) -> Path:
    """Write a synthetic NanoDrop-style TSV containing two spectra.

    The real NanoDrop export separates spectra with two blank lines and the
    last spectrum ends with a trailing newline (no padding blank lines are
    guaranteed), which is exactly the situation the buggy implementation
    mangled.
    """
    spectra = [
        (
            "Sample A",
            "2026/1/2 10:00:00",
            [(220, 1.0), (221, 1.1), (222, 1.2)],
        ),
        (
            "Sample B",
            "2026/1/2 10:05:00",
            [(220, 2.0), (221, 2.1), (222, 2.2)],
        ),
    ]
    parts: list[str] = []
    for i, (name, timestamp, rows) in enumerate(spectra):
        parts.append(f"{name}\n{timestamp}\nWavelength (nm)\t10mm Absorbance\n")
        parts.extend(f"{wavelength}\t{value}\n" for wavelength, value in rows)
        if i < len(spectra) - 1:
            parts.append("\n\n")
    path.write_text("".join(parts), encoding="utf-8")
    return path


@pytest.fixture
def two_spectrum_tsv(tmp_path: Path) -> Path:
    return _write_two_spectrum_tsv(tmp_path / "two_spectra.tsv")


def test_from_tsv_does_not_modify_input_file(two_spectrum_tsv: Path):
    """The input file must be byte-for-byte identical after parsing."""
    original_bytes = two_spectrum_tsv.read_bytes()

    Nanodrop2000Workbook.from_tsv(two_spectrum_tsv)

    assert two_spectrum_tsv.read_bytes() == original_bytes


def test_from_tsv_parses_both_spectra_and_keeps_last_data_row(
    two_spectrum_tsv: Path,
):
    """Both spectra are parsed and no data row is lost from the tail."""
    workbook = Nanodrop2000Workbook.from_tsv(two_spectrum_tsv)

    assert len(workbook) == 2
    assert list(workbook.keys()) == [
        "Sample A 2026/1/2 10:00:00",
        "Sample B 2026/1/2 10:05:00",
    ]

    sample_a = workbook["Sample A 2026/1/2 10:00:00"]
    assert sample_a.data.iloc[:, 0].tolist() == [220.0, 221.0, 222.0]
    assert sample_a.data.iloc[:, 1].tolist() == pytest.approx([1.0, 1.1, 1.2])
    # The last data row of the first spectrum is present as well
    assert sample_a.data.iloc[-1, 0] == 222.0

    sample_b = workbook["Sample B 2026/1/2 10:05:00"]
    assert sample_b.data.iloc[:, 0].tolist() == [220.0, 221.0, 222.0]
    assert sample_b.data.iloc[:, 1].tolist() == pytest.approx([2.0, 2.1, 2.2])
    # ... and so is the very last data row of the file
    assert sample_b.data.iloc[-1, 0] == 222.0
    assert sample_b.data.iloc[-1, 1] == pytest.approx(2.2)


def test_from_tsv_is_idempotent(two_spectrum_tsv: Path):
    """Parsing repeatedly yields the same result and never trims the file."""
    original_bytes = two_spectrum_tsv.read_bytes()

    first = Nanodrop2000Workbook.from_tsv(two_spectrum_tsv)
    second = Nanodrop2000Workbook.from_tsv(two_spectrum_tsv)

    assert two_spectrum_tsv.read_bytes() == original_bytes
    assert list(first.keys()) == list(second.keys())
    for signal_name in first.keys():
        assert first[signal_name].data.equals(second[signal_name].data)


@pytest.mark.skipif(not EXAMPLE_TSV.exists(), reason="example TSV is missing")
def test_from_tsv_on_example_keeps_trailing_wavelength(tmp_path: Path):
    """A copy of the example export keeps its final data row (349 nm)."""
    tsv_copy = tmp_path / EXAMPLE_TSV.name
    tsv_copy.write_bytes(EXAMPLE_TSV.read_bytes())
    original_bytes = tsv_copy.read_bytes()

    workbook = Nanodrop2000Workbook.from_tsv(tsv_copy)

    assert tsv_copy.read_bytes() == original_bytes
    assert len(workbook) == 1
    spectrum = workbook.signals[0]
    assert spectrum.data.iloc[0, 0] == 220.0
    assert spectrum.data.iloc[-1, 0] == 349.0
    assert workbook.name == tsv_copy.stem
