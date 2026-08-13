#!/usr/bin/env python3
"""Create the portable Simulation_Data archive attached to a Pythia release."""

import argparse
from pathlib import Path

from pythia.example_release import build_example_archive


def main():
    parser = argparse.ArgumentParser(
        description="Validate and package the Pythia Sri Lanka example data."
    )
    parser.add_argument("source", help="Path to the Simulation_Data directory")
    parser.add_argument("output", help="Destination .zip path")
    parser.add_argument(
        "--readme",
        default=str(
            Path(__file__).parents[1] / "release" / "Simulation_Data_README.md"
        ),
        help="README inserted at the root of Simulation_Data",
    )
    args = parser.parse_args()

    archive, checksum, size = build_example_archive(
        args.source, args.output, args.readme
    )
    print(f"Created:  {archive}")
    print(f"Size:     {size / 1024**2:.1f} MiB")
    print(f"Checksum: {checksum}")


if __name__ == "__main__":
    main()
