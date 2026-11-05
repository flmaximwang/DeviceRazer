"""
Export SoftMax Pro cuvette data to CSV
======================================

Read a cuvette .txt file exported by SoftMax Pro, parse it and export it as CSV.

Usage::

    # Default: export the Raw-Ref (OD) section
    python examples/softmax_pro/cuvette/clipboard2csv.py /path/to/data.txt

    # Set the mode to Transmission (%)
    python examples/softmax_pro/cuvette/clipboard2csv.py /path/to/data.txt --mode Transmission

    # Export the Ref section
    python examples/softmax_pro/cuvette/clipboard2csv.py /path/to/data.txt --section Ref

    # Set the output path
    python examples/softmax_pro/cuvette/clipboard2csv.py /path/to/data.txt -o result.csv
"""

import argparse
import sys
from pathlib import Path

from dvrazer.instruments.MolecularDevices.softmax_pro import (
    SoftMaxPro_CuvetteData,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export SoftMax Pro cuvette data to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "txt",
        type=str,
        help="Path to the cuvette .txt file exported by SoftMax Pro",
    )
    parser.add_argument(
        "-s",
        "--section",
        default="Raw-Ref",
        choices=["Wavelength", "Ref", "Raw-Ref"],
        help="Data section to export (default: Raw-Ref)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="OD",
        choices=["OD", "Transmission"],
        help="Data type: OD (absorbance, cm⁻¹) or Transmission (transmittance, %%), (default: OD)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output CSV file path (default: <input filename>_<section>_<mode>.csv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    txt_path = Path(args.txt)
    if not txt_path.exists():
        print(f"Error: file not found: {txt_path}")
        sys.exit(1)

    # Parse the data
    print(f"Reading: {txt_path}")
    curve = SoftMaxPro_CuvetteData.from_clipboard(
        txt=str(txt_path),
        section=args.section,
        mode=args.mode,
    )

    print(f"Sample: {curve._extra_metadata['sample_name']}")
    print(f"Section: {args.section}  |  Mode: {args.mode}")
    print(f"Temperature: {curve._extra_metadata['temperature']} °C")
    print(f"Data points: {len(curve.data)}")

    # Determine the output path
    if args.output:
        csv_path = Path(args.output)
    else:
        stem = txt_path.stem
        csv_path = txt_path.with_name(f"{stem}_{args.section}_{args.mode}.csv")

    # Write CSV (keeping units in the column headers)
    curve.data.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
