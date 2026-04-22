"""
======================================================================
 Basic Functional Tests for pythia.functions
----------------------------------------------------------------------
This file contains lightweight tests designed to validate individual
helper functions used throughout the Pythia workflow, including:

 - ASCII/soil-code builders
 - Raster path parsing
 - String parsing helpers
 - Fertilizer splitting logic
 - Value assignment via raster
 - Date manipulation helpers
 - Soil lookup via raster (core integration test)

These tests DO NOT simulate a full Pythia run - they only confirm that
key low-level pieces behave correctly in isolation.
======================================================================
"""

from pathlib import Path
import pythia.functions as fn


def test_prefix_and_profile_code_from_bands():
    print("\n=== Running test_prefix_and_profile_code_from_bands ===")

    # 66='B', 82='R' => "6682" (legacy 2-letter encoding)
    prefix_code = 6682
    prefix = fn.decode_prefix(prefix_code)
    print("decode_prefix(6682) =", prefix)
    assert prefix == "BR", "decode_prefix failed for 2-letter encoding"

    code = fn.build_profile_code_from_bands(prefix_code, 5142095)
    print("build_profile_code_from_bands(6682, 5142095) =", code)
    assert code == "BR05142095", "build_profile_code_from_bands failed"

    print("[OK] test_prefix_and_profile_code_from_bands")


def test_extract_raster():
    print("\n=== Running test_extract_raster ===")

    s = "lookup_ghr::raster::../rasters/eGHR_soils_raster.tif"
    print("Input string:", s)

    raster_path = fn.extract_raster(s)
    print("Extracted path:", raster_path)

    expected = "../rasters/eGHR_soils_raster.tif"
    print("Expected path :", expected)

    assert raster_path == expected, f"Expected {expected}, got {raster_path}"

    print("[OK] test_extract_raster")


def test_string_to_number():
    print("\n=== Running test_string_to_number ===")

    assert fn.string_to_number("10") == 10
    assert fn.string_to_number("3.14") == 3.14

    # Should log an error and return None
    result = fn.string_to_number("abc")
    print("string_to_number('abc') →", result)
    assert result is None

    print("[OK] test_string_to_number")


def test_split_fert_dap_percent():
    print("\n=== Running test_split_fert_dap_percent ===")

    run = {
        "fert": "split_fert_dap_percent::100::2::10::50::20::50"
    }
    context = {}

    out = fn.split_fert_dap_percent("fert", run, context, None)
    apps = out["fert"]

    print("Resulting applications:", apps)

    assert len(apps) == 2, "Should have 2 applications"

    # Application 1
    assert apps[0]["fdap"] == 10
    assert abs(apps[0]["famn"] - 50.0) < 1e-6

    # Application 2
    assert apps[1]["fdap"] == 20
    assert abs(apps[1]["famn"] - 50.0) < 1e-6

    print("[OK] test_split_fert_dap_percent")


def test_assign_by_raster_value():
    print("\n=== Running test_assign_by_raster_value ===")

    run = {
        "treat": "assign_by_raster_value::raster::dummy.tif::1::OptionA::2::OptionB"
    }
    context = {"treat": 2}

    out = fn.assign_by_raster_value("treat", run, context, None)
    print("assign_by_raster_value →", out)

    assert out["treat"] == "OptionB", "Assignment based on raster value failed"

    print("[OK] test_assign_by_raster_value")


def test_date_offset():
    print("\n=== Running test_date_offset ===")

    run = {
        "harvest": "date_offset::$pdate::10"
    }
    context = {"pdate": "2020-01-01"}

    out = fn.date_offset("harvest", run, context, None)
    print("date_offset →", out)

    assert out["harvest"] == "2020-01-11"

    print("[OK] test_date_offset")


def test_get_profile_from_raster():
    print("\n=== Running test_get_profile_from_raster ===")

    raster_path = Path("rasters/eGHR_soils_raster.tif")  # adjust to your path
    lat, lon = -9.208, -72.041  # known valid point from your README

    profile_code = fn.get_profile_from_raster(lat, lon, raster_path)
    print("get_profile_from_raster →", profile_code)

    assert profile_code is not None, "Raster lookup failed"
    assert len(profile_code) >= 3
    assert profile_code[:2].isalpha()

    print("[OK] test_get_profile_from_raster")


def test_lookup_ghr_integration():
    print("\n=== Running test_lookup_ghr_integration ===")

    run = {
        "id_soil": "lookup_ghr::raster::rasters/eGHR_soils_raster.tif"
    }
    context = {
        "lat": -9.208,
        "lng": -72.041,
    }
    config = {
        "ghr_root": "eGHR"  # adjust to your real SOL path
    }

    print("Extracting raster path from run['id_soil']...")
    raster_path_str = fn.extract_raster(run["id_soil"])
    print("→", raster_path_str)

    print("\nCalling lookup_ghr...")
    result = fn.lookup_ghr("id_soil", run, context, config)
    print("lookup_ghr output:", result)

    assert result is not None, "lookup_ghr returned None"
    assert "id_soil" in result
    assert "soilFiles" in result
    assert len(result["soilFiles"]) == 1

    sol_path = Path(result["soilFiles"][0])
    print("Resolved SOL path:", sol_path)

    assert sol_path.exists(), "SOL file does not exist — adjust ghr_root"

    print("[OK] test_lookup_ghr_integration")


def test_lookup_ghr_and_ic_layers():
    print("\n=== Running test_lookup_ghr_and_ic_layers ===")

    run = {
        "id_soil": "lookup_ghr::raster::rasters/eGHR_soils_raster.tif",
        "ic_layers": "generate_ic_layers::$id_soil",
        # parâmetros mínimos que calculateICLayerData usa:
        "icin": 50,    # N inicial total (exemplo)
        "icsw%": 50,   # água disponível inicial (exemplo)
    }

    context = {
        "lat": -9.208,
        "lng": -72.041,
    }
    config = {
        "ghr_root": "eGHR"
    }

    # 1) Resolve solo e soilFiles
    lookup = fn.lookup_ghr("id_soil", run, context, config)
    context.update(lookup)

    # 2) Gera camadas IC
    ic_result = fn.generate_ic_layers("ic_layers", run, context, None)
    print("generate_ic_layers →", ic_result)

    assert ic_result is not None
    assert "ic_layers" in ic_result
    assert isinstance(ic_result["ic_layers"], list)
    assert len(ic_result["ic_layers"]) > 0

    print("[OK] test_lookup_ghr_and_ic_layers")


if __name__ == "__main__":
    print("\n============================================")
    print(" Running Basic Tests for pythia.functions")
    print("============================================\n")

    test_prefix_and_profile_code_from_bands()
    test_extract_raster()
    test_string_to_number()
    test_split_fert_dap_percent()
    test_assign_by_raster_value()
    test_date_offset()
    test_get_profile_from_raster()
    test_lookup_ghr_integration()
    test_lookup_ghr_and_ic_layers()

    print("\n============================================")
    print(" All tests finished successfully.")
    print("============================================\n")
