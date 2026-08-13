import json
from pathlib import Path

import pytest

from pythia.example_data import (
    DATA_ROOT_TOKEN,
    DSSAT_EXECUTABLE_TOKEN,
    EXAMPLE_CONFIGS,
    ExampleDataError,
    configure_example_data,
    validate_example_data,
)
from pythia.example_release import build_example_archive, inspect_archive


def _make_example_package(tmp_path: Path) -> Path:
    root = tmp_path / "Simulation Data"
    required = (
        "weather_data/Sri_Lanka/0001.WTH",
        "eGHR/GHR.db",
        "eGHR/LK.SOL",
        "raster/ggcmi_soils_2.tif",
        "raster/spam2010V2r0_global_H_MAIZ_H.tif",
        "raster/spam2010V2r0_global_H_RICE_I.tif",
        "Sri_Lanka/templates/example.X",
        "Sri_Lanka/shapes/Sri_Lanka.shp",
        "Sri_Lanka/CUL_files/example.CUL",
    )
    for relative in required:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test")

    for name in EXAMPLE_CONFIGS:
        config = {
            "workDir": f"{DATA_ROOT_TOKEN}/OUTPUT/example",
            "templateDir": f"{DATA_ROOT_TOKEN}/Sri_Lanka/templates",
            "weatherDir": f"{DATA_ROOT_TOKEN}/weather_data/Sri_Lanka",
            "ghr_root": f"{DATA_ROOT_TOKEN}/eGHR",
            "default_setup": {
                "include": [f"{DATA_ROOT_TOKEN}/Sri_Lanka/CUL_files/example.CUL"],
                "template": "example.X",
                "sites": f"xy_from_vector::{DATA_ROOT_TOKEN}/Sri_Lanka/shapes/Sri_Lanka.shp",
                "id_soil": f"lookup_ghr::raster::{DATA_ROOT_TOKEN}/raster/ggcmi_soils_2.tif",
            },
            "dssat": {"executable": DSSAT_EXECUTABLE_TOKEN},
            "runs": [
                {
                    "harvestArea": f"raster::{DATA_ROOT_TOKEN}/raster/spam2010V2r0_global_H_MAIZ_H.tif"
                }
            ],
        }
        (root / "Sri_Lanka" / name).write_text(json.dumps(config), encoding="utf-8")
    return root


def test_configure_and_validate_example_data(tmp_path):
    root = _make_example_package(tmp_path)
    executable = tmp_path / "dscsm048"
    executable.write_text("executable", encoding="utf-8")

    assert len(validate_example_data(root, allow_placeholders=True)) == 3
    configured = configure_example_data(root, executable)
    assert len(configured) == 3
    assert len(validate_example_data(root)) == 3

    for path in configured:
        text = path.read_text(encoding="utf-8")
        assert DATA_ROOT_TOKEN not in text
        assert DSSAT_EXECUTABLE_TOKEN not in text
        assert root.as_posix() in text
        assert executable.as_posix() in text
        assert path.with_suffix(".json.template").is_file()

    second_executable = tmp_path / "DSSAT48.exe"
    second_executable.write_text("executable", encoding="utf-8")
    configure_example_data(root, second_executable)
    for path in configured:
        text = path.read_text(encoding="utf-8")
        assert second_executable.as_posix() in text
        assert executable.as_posix() not in text


def test_unconfigured_example_is_rejected(tmp_path):
    root = _make_example_package(tmp_path)
    with pytest.raises(ExampleDataError, match="not configured yet"):
        validate_example_data(root)


def test_missing_required_file_is_reported(tmp_path):
    root = _make_example_package(tmp_path)
    (root / "eGHR" / "GHR.db").unlink()
    with pytest.raises(ExampleDataError, match="GHR.db"):
        validate_example_data(root, allow_placeholders=True)


def test_release_archive_is_portable_and_excludes_local_files(tmp_path):
    root = _make_example_package(tmp_path)
    (root / ".history").mkdir()
    (root / ".history" / "old.json").write_text("{}", encoding="utf-8")
    (root / "OUTPUT" / "old-run").mkdir(parents=True)
    (root / "OUTPUT" / "old-run" / "result.csv").write_text("result", encoding="utf-8")
    (root / ".DS_Store").write_bytes(b"local")

    executable = tmp_path / "dscsm048"
    executable.write_text("executable", encoding="utf-8")
    configure_example_data(root, executable)

    readme = tmp_path / "README.md"
    readme.write_text("example", encoding="utf-8")
    archive, checksum, _ = build_example_archive(root, tmp_path / "example.zip", readme)
    manifest = inspect_archive(archive)

    assert checksum.is_file()
    assert manifest["excluded_members"] == []
    assert "Simulation_Data/OUTPUT/" in manifest["members"]
    assert "Simulation_Data/OUTPUT/old-run/result.csv" not in manifest["members"]
    for config in manifest["configs"].values():
        serialized = json.dumps(config)
        assert DATA_ROOT_TOKEN in serialized
        assert DSSAT_EXECUTABLE_TOKEN in serialized
