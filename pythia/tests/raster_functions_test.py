import logging
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import pythia.functions as fn
import pythia.io


SRI_LANKA_LAT = 8.541666666666686
SRI_LANKA_LON = 81.12500000000011
# Values from the public Sri Lanka example at the coordinate reported by users.
PROFILE_ID = "LK04202172"
LEGACY_SOIL_ID = 5130973


def _write_raster(path: Path, bands, nodata=0, crs="EPSG:4326") -> Path:
    data = np.asarray(bands, dtype="uint32")
    if data.ndim == 2:
        data = data[np.newaxis, :, :]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[2],
        height=data.shape[1],
        count=data.shape[0],
        dtype=data.dtype,
        nodata=nodata,
        crs=crs,
        transform=from_origin(80.0, 10.0, 1.0, 1.0),
    ) as dst:
        dst.write(data)
    return path


def _write_soil_file(ghr_root: Path, profile_id=PROFILE_ID) -> Path:
    soil_path = ghr_root / f"{profile_id[:2]}.SOL"
    soil_path.write_text(
        "*{0} Test soil\n"
        "@SITE        COUNTRY          LAT     LONG\n"
        " TEST        SRI_LANKA       8.54    81.12\n"
        "@  SLB  SBDM  SLLL  SDUL\n"
        "    20   1.2  0.10  0.20\n"
        "    60   1.3  0.12  0.25\n\n".format(profile_id),
        encoding="utf-8",
    )
    return soil_path


def _write_ghr_database(ghr_root: Path, soil_id=LEGACY_SOIL_ID, profile=PROFILE_ID) -> Path:
    db_path = ghr_root / "GHR.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE profile_map (id INTEGER PRIMARY KEY, profile TEXT)")
        conn.execute(
            "INSERT INTO profile_map (id, profile) VALUES (?, ?)",
            (soil_id, profile),
        )
    return db_path


@pytest.fixture
def soil_data(tmp_path):
    # A path with spaces exercises the same Path-based code used for Windows paths.
    root = tmp_path / "Simulation Data" / "soil"
    root.mkdir(parents=True)
    soil_file = _write_soil_file(root)
    database = _write_ghr_database(root)

    legacy_values = np.zeros((3, 3), dtype="uint32")
    legacy_values[1, 1] = LEGACY_SOIL_ID
    legacy_raster = _write_raster(root / "ggcmi_soils_2.tif", legacy_values)

    prefix_values = np.zeros((3, 3), dtype="uint32")
    numeric_values = np.zeros((3, 3), dtype="uint32")
    prefix_values[1, 1] = 7675  # ASCII decimal pairs: L=76, K=75
    numeric_values[1, 1] = 4202172
    encoded_raster = _write_raster(
        root / "encoded_soils.tif",
        np.stack([prefix_values, numeric_values]),
    )

    return {
        "root": root,
        "soil_file": soil_file,
        "database": database,
        "legacy_raster": legacy_raster,
        "encoded_raster": encoded_raster,
    }


def _lookup(raster_path, ghr_root, context=None):
    run = {"id_soil": f"lookup_ghr::raster::{raster_path}"}
    base_context = {"lat": SRI_LANKA_LAT, "lng": SRI_LANKA_LON}
    if context:
        base_context.update(context)
    return fn.lookup_ghr(
        "id_soil",
        run,
        base_context,
        {"ghr_root": str(ghr_root)},
    )


def test_prefix_and_profile_code_from_bands():
    assert fn.decode_prefix(6682) == "BR"
    assert fn.build_profile_code_from_bands(6682, 5142095) == "BR05142095"
    assert fn.build_profile_code_from_bands(7675, 4202172) == PROFILE_ID


@pytest.mark.parametrize(
    "prefix_code,numeric_id",
    [(3333, 1), (6682, -1), (6682, 100000000)],
)
def test_invalid_encoded_profile_values(prefix_code, numeric_id):
    with pytest.raises(ValueError):
        fn.build_profile_code_from_bands(prefix_code, numeric_id)


def test_extract_raster():
    value = "lookup_ghr::raster::../rasters/eGHR_soils_raster.tif"
    assert fn.extract_raster(value) == "../rasters/eGHR_soils_raster.tif"


def test_string_to_number():
    assert fn.string_to_number("10") == 10
    assert fn.string_to_number("3.14") == 3.14
    assert fn.string_to_number("abc") is None


def test_split_fert_dap_percent():
    run = {"fert": "split_fert_dap_percent::100::2::10::50::20::50"}
    applications = fn.split_fert_dap_percent("fert", run, {}, None)["fert"]
    assert applications == [
        {"fdap": 10, "famn": 50.0},
        {"fdap": 20, "famn": 50.0},
    ]


def test_assign_by_raster_value():
    run = {
        "treat": "assign_by_raster_value::raster::dummy.tif::1::OptionA::2::OptionB"
    }
    assert fn.assign_by_raster_value("treat", run, {"treat": 2}, None) == {
        "treat": "OptionB"
    }


def test_date_offset():
    run = {"harvest": "date_offset::$pdate::10"}
    result = fn.date_offset("harvest", run, {"pdate": "2020-01-01"}, None)
    assert result["harvest"] == "2020-01-11"


def test_legacy_one_band_lookup_uses_ghr_database(soil_data):
    result = _lookup(
        soil_data["legacy_raster"],
        soil_data["root"],
        {"id_soil": float(LEGACY_SOIL_ID)},
    )
    assert result == {
        "id_soil": PROFILE_ID,
        "soilFiles": [str(soil_data["soil_file"])],
    }


def test_two_band_lookup_remains_supported(soil_data):
    result = _lookup(soil_data["encoded_raster"], soil_data["root"])
    assert result == {
        "id_soil": PROFILE_ID,
        "soilFiles": [str(soil_data["soil_file"])],
    }


def test_get_profile_from_two_band_raster(soil_data):
    result = fn.get_profile_from_raster(
        SRI_LANKA_LAT,
        SRI_LANKA_LON,
        soil_data["encoded_raster"],
    )
    assert result == PROFILE_ID


def test_lookup_and_generate_initial_condition_layers(soil_data):
    lookup = _lookup(
        soil_data["legacy_raster"],
        soil_data["root"],
        {"id_soil": LEGACY_SOIL_ID},
    )
    context = {**lookup}
    run = {
        "ic_layers": "generate_ic_layers::$id_soil",
        "icin": 50,
        "icsw%": 50,
    }
    result = fn.generate_ic_layers("ic_layers", run, context, None)
    assert len(result["ic_layers"]) == 2
    assert result["ic_layers"][0]["icbl"] == "20"


def test_legacy_lookup_reports_missing_database(tmp_path, caplog):
    root = tmp_path / "soil"
    root.mkdir()
    _write_soil_file(root)
    values = np.zeros((3, 3), dtype="uint32")
    values[1, 1] = LEGACY_SOIL_ID
    raster_path = _write_raster(root / "legacy.tif", values)

    with caplog.at_level(logging.ERROR):
        result = _lookup(raster_path, root, {"id_soil": LEGACY_SOIL_ID})

    assert result is None
    assert "GHR.db was not found" in caplog.text


def test_legacy_lookup_reports_unknown_id(soil_data, caplog):
    with caplog.at_level(logging.ERROR):
        result = _lookup(
            soil_data["legacy_raster"],
            soil_data["root"],
            {"id_soil": 999},
        )
    assert result is None
    assert "was not found in GHR.db" in caplog.text


def test_lookup_reports_missing_sol_file(soil_data, caplog):
    soil_data["soil_file"].unlink()
    with caplog.at_level(logging.ERROR):
        result = _lookup(
            soil_data["legacy_raster"],
            soil_data["root"],
            {"id_soil": LEGACY_SOIL_ID},
        )
    assert result is None
    assert "DSSAT soil file was not found" in caplog.text


def test_lookup_reports_profile_missing_inside_sol_file(soil_data, caplog):
    soil_data["soil_file"].write_text("*LK99999999 Another soil\n", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = _lookup(
            soil_data["legacy_raster"],
            soil_data["root"],
            {"id_soil": LEGACY_SOIL_ID},
        )
    assert result is None
    assert "was not found inside DSSAT soil file" in caplog.text


@pytest.mark.parametrize(
    "lat,lon",
    [(91.0, 81.0), (-91.0, 81.0), (8.0, 181.0), (8.0, -181.0)],
)
def test_coordinates_outside_raster_return_none(soil_data, lat, lon):
    assert fn.get_profile_from_raster(lat, lon, soil_data["encoded_raster"]) is None


def test_partially_missing_encoded_profile_returns_none(tmp_path):
    prefix = np.zeros((3, 3), dtype="uint32")
    numeric = np.zeros((3, 3), dtype="uint32")
    prefix[1, 1] = 7675
    raster_path = _write_raster(
        tmp_path / "partial.tif",
        np.stack([prefix, numeric]),
    )
    assert fn.get_profile_from_raster(SRI_LANKA_LAT, SRI_LANKA_LON, raster_path) is None


def test_unsupported_band_count_is_rejected(tmp_path, caplog):
    root = tmp_path / "soil"
    root.mkdir()
    _write_soil_file(root)
    raster_path = _write_raster(
        root / "three-bands.tif",
        np.zeros((3, 3, 3), dtype="uint32"),
    )
    with caplog.at_level(logging.ERROR):
        result = _lookup(raster_path, root)
    assert result is None
    assert "expected 1 legacy band or 2 encoded bands" in caplog.text


def test_peer_raster_read_rejects_negative_and_overflowing_indexes(soil_data):
    with rasterio.open(soil_data["legacy_raster"]) as dataset:
        band = dataset.read(1, masked=True)
        assert pythia.io.get_site_raster_value(dataset, band, (79.0, 11.0)) is None
        assert pythia.io.get_site_raster_value(dataset, band, (84.0, 8.0)) is None
