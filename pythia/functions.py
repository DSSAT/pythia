import datetime
import logging
import math
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.errors import RasterioIOError
from rasterio.warp import transform as transform_coordinates
from rasterio.windows import Window

import pythia.io
import pythia.soil_handler
import pythia.template
import pythia.util


def extract_raster(s):
    """
    Extracts the raster filepath from a DSSAT-style lookup string. It scans for the
    'raster' keyword and returns the element that follows it.

    :param s: Lookup string containing the raster specification using '::' separators.
    :returns: The raster filepath extracted from the lookup string.
    :raises ValueError: If 'raster' is not found in the lookup string.
    """
    args = s.split("::")
    raster_idx = args.index("raster")
    return args[raster_idx + 1]


def xy_from_vector(v):
    """
    Extracts XY coordinates from a vector-based lookup string. This function parses
    the lookup specification and delegates coordinate extraction to Pythia's I/O module.

    :param v: Lookup string in the format 'xy_from_vector::<path_to_vector>'.
    :returns: A list or array of XY coordinate pairs extracted from the vector file.
    :raises IndexError: If the lookup string is malformed or missing components.
    """
    args = v.split("::")
    return pythia.io.extract_vector_coords(args[1])


def xy_from_list(lst):
    """
    Converts a list of coordinate-like sequences into (x, y) tuples. Coordinates are
    reversed to match the expected ordering.

    :param lst: Iterable containing coordinate pairs or sequences.
    :returns: A list of (x, y) tuples with reversed coordinate order.
    """
    return [tuple(x[::-1]) for x in lst]


def auto_planting_window(k, run, context, _):
    """
    Computes an automatic planting window based on planting-date parameters encoded in
    a lookup string. It replaces the raster-dependent field with contextual values and
    derives the start and end dates accordingly.

    :param k: Key identifying the planting configuration field in the run dictionary.
    :param run: Dictionary containing run-level configuration values, including the lookup string.
    :param context: Dictionary with resolved lookup values that replace raster-dependent entries.
    :param _: Unused placeholder parameter kept for interface compatibility.
    :returns: A dictionary with ISO-formatted planting dates (`pdate`, `pfrst`, `plast`).
    :raises ValueError: If the lookup string is malformed or missing expected components.
    """
    """multiple rasters not yet supported"""
    args = run[k].split("::")[1:]
    raster_idx = args.index("raster")
    args[raster_idx + 1] = context[k]
    args.pop(raster_idx)
    vals = [int(v) for v in args]
    first = datetime.date(run["startYear"], vals[0], vals[1])
    td = datetime.timedelta(days=vals[2])
    last = first + td
    return {
        "pdate": pythia.util.to_iso_date(first),
        "pfrst": pythia.util.to_iso_date(first),
        "plast": pythia.util.to_iso_date(last),
    }


def auto_planting_window_doy(k, run, context, _):
    """multiple rasters not yet supported"""
    args = run[k].split("::")[1:]
    raster_idx = args.index("raster")
    args[raster_idx + 1] = context[k]
    args.pop(raster_idx)
    vals = [int(v) for v in args]
    first = datetime.datetime(run["startYear"], 1, 1) + datetime.timedelta(vals[0] + vals[1] - 1)
    td = datetime.timedelta(days=vals[2])
    last = first + td
    return {
        "pdate": pythia.util.to_iso_date(first),
        "pfrst": pythia.util.to_iso_date(first),
        "plast": pythia.util.to_iso_date(last),
    }


def auto_planting_window_doy_shape(k, run, context, _):
    """multiple rasters not yet supported"""
    args = run[k].split("::")[1:]
    finder = pythia.io.find_closest_vector_coords
    cell_doy = None
    if "vector" in args:
        idx = args.index("vector")
        cell_doy = finder(args[idx + 1], context["lng"], context["lat"], args[idx + 2])

    first = datetime.datetime(run["startYear"], 1, 1) + datetime.timedelta(int(cell_doy) + int(args[idx + 3]))
    td = datetime.timedelta(days=int(args[idx + 4]))
    last = first + td
    return {
        "pdate": pythia.util.to_iso_date(first),
        "pfrst": pythia.util.to_iso_date(first),
        "plast": pythia.util.to_iso_date(last),
    }


def lookup_hc27(k, run, context, _):
    args = run[k].split("::")[1:]
    if "raster" in args:
        return {k: "HC_GEN{:0>4}".format(context[k])}
    else:
        return {k: "HC_GEN{:0>4}".format(args[0])}


def lookup_wth(k, run, context, _):
    args = run[k].split("::")[1:]
    finder = pythia.io.find_closest_vector_coords
    cell_id = None
    if "vector" in args:
        idx = args.index("vector")
        cell_id = finder(args[idx + 1], context["lng"], context["lat"], args[idx + 2])
    return {k: args[0], "wthFile": "{}.WTH".format(cell_id)}


def generate_ic_layers(k, run, context, _):
    args = run[k].split("::")[1:]
    if args[0].startswith("$"):
        profile = args[0][1:]
    else:
        profile = args[0]
    soil_file = pythia.soil_handler.findSoilProfile(
        context[profile], context["soilFiles"]
    )
    layers = pythia.soil_handler.readSoilLayers(context[profile], soil_file)
    calculated_layers = pythia.soil_handler.calculateICLayerData(layers, run)
    layer_labels = ["icbl", "sh2o", "snh4", "sno3"]
    return {k: [dict(zip(layer_labels, cl)) for cl in calculated_layers]}


def decode_prefix(prefix_code: int) -> str:
    code = int(prefix_code)

    if 0 <= code <= 9999:
        s = f"{code:04d}"
        a = int(s[:2])
        b = int(s[2:])
        if not (32 <= a <= 126 and 32 <= b <= 126):
            raise ValueError("invalid 2-letter ascii pair")
        prefix = chr(a) + chr(b)
        if not prefix.isalpha():
            raise ValueError("invalid 2-letter ascii prefix")
        return prefix

    b0 = (code >> 24) & 0xFF
    b1 = (code >> 16) & 0xFF
    b2 = (code >> 8) & 0xFF
    b3 = code & 0xFF

    for x in (b0, b1, b2, b3):
        if not (32 <= x <= 126):
            raise ValueError("invalid packed-ascii byte")

    prefix = bytes([b0, b1, b2, b3]).decode("ascii")
    if not prefix.isalpha():
        raise ValueError("invalid 4-letter ascii prefix")
    return prefix


def build_profile_code_from_bands(prefix_code: int, numeric_id: int) -> str:
    prefix = decode_prefix(prefix_code)
    n = int(numeric_id)

    if len(prefix) == 2:
        if n < 0 or n > 99999999:
            raise ValueError("numeric ID does not fit the 2-letter profile format")
        return f"{prefix}{n:08d}"
    if len(prefix) == 4:
        if n < 0 or n > 999999:
            raise ValueError("numeric ID does not fit the 4-letter profile format")
        return f"{prefix}{n:06d}"

    raise ValueError("invalid decoded prefix length")


def _point_to_raster_pixel(src, lat: float, lon: float) -> Optional[Tuple[int, int]]:
    """Return a checked raster pixel for a WGS84 latitude/longitude pair."""
    x = float(lon)
    y = float(lat)

    if not math.isfinite(x) or not math.isfinite(y):
        logging.error("Invalid non-finite coordinates: (%s, %s).", lat, lon)
        return None

    try:
        if src.crs is not None and src.crs != CRS.from_epsg(4326):
            xs, ys = transform_coordinates(CRS.from_epsg(4326), src.crs, [x], [y])
            x, y = xs[0], ys[0]
    except Exception as exc:
        logging.error(
            "Could not transform point (%s, %s) to raster CRS %s: %s",
            lat,
            lon,
            src.crs,
            exc,
        )
        return None

    bounds = src.bounds
    if not (bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top):
        logging.warning("Point (%s, %s) is outside raster '%s'.", lat, lon, src.name)
        return None

    try:
        row, col = src.index(x, y)
    except Exception as exc:
        logging.warning(
            "Could not locate point (%s, %s) in raster '%s': %s",
            lat,
            lon,
            src.name,
            exc,
        )
        return None

    if row < 0 or row >= src.height or col < 0 or col >= src.width:
        logging.warning("Point (%s, %s) is outside raster '%s'.", lat, lon, src.name)
        return None
    return row, col


def _integer_band_value(value, band: int, lat: float, lon: float) -> Optional[int]:
    if np.ma.is_masked(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        logging.error(
            "Invalid value in soil raster band %d at (%s, %s): %r.",
            band,
            lat,
            lon,
            value,
        )
        return None
    if not math.isfinite(number) or not number.is_integer():
        logging.error(
            "Soil raster band %d must contain integer values at (%s, %s); found %r.",
            band,
            lat,
            lon,
            value,
        )
        return None
    return int(number)


def _get_profile_from_dataset(src, lat: float, lon: float) -> Optional[str]:
    if src.count != 2:
        logging.error(
            "Encoded soil raster '%s' must have exactly 2 bands. Found %d.",
            src.name,
            src.count,
        )
        return None

    pixel = _point_to_raster_pixel(src, lat, lon)
    if pixel is None:
        return None
    row, col = pixel

    try:
        values = src.read(
            indexes=(1, 2),
            window=Window(col, row, 1, 1),
            masked=True,
        )
    except Exception as exc:
        logging.error(
            "Could not read soil raster '%s' at (%s, %s): %s",
            src.name,
            lat,
            lon,
            exc,
        )
        return None

    b1 = _integer_band_value(values[0, 0, 0], 1, lat, lon)
    b2 = _integer_band_value(values[1, 0, 0], 2, lat, lon)
    if b1 is None and b2 is None:
        return None
    if b1 is None or b2 is None:
        logging.error(
            "Incomplete encoded soil profile at (%s, %s) in '%s'.",
            lat,
            lon,
            src.name,
        )
        return None

    try:
        return build_profile_code_from_bands(b1, b2)
    except (TypeError, ValueError, OverflowError) as exc:
        logging.error(
            "Failed to decode soil raster bands at (%s, %s): b1=%d b2=%d (%s).",
            lat,
            lon,
            b1,
            b2,
            exc,
        )
        return None


def get_profile_from_raster(lat: float, lon: float, raster_path: Path) -> Optional[str]:
    """Resolve a profile from a two-band encoded soil raster."""
    raster_path = Path(raster_path)
    if not raster_path.exists():
        logging.error("Soil raster not found: %s", str(raster_path))
        return None

    try:
        with rasterio.open(str(raster_path)) as src:
            return _get_profile_from_dataset(src, lat, lon)
    except (OSError, RasterioIOError) as exc:
        logging.error("Could not open soil raster '%s': %s", raster_path, exc)
        return None


@lru_cache(maxsize=8)
def _load_ghr_profiles_cached(db_path: str, modified_ns: int) -> Dict[int, str]:
    """Load the legacy profile map; ``modified_ns`` invalidates stale cache entries."""
    del modified_ns
    profiles = {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT id, profile FROM profile_map "
            "WHERE profile IS NOT NULL AND TRIM(profile) != ''"
        )
        for soil_id, profile in cursor.fetchall():
            profiles[int(soil_id)] = str(profile).strip()
    return profiles


def _ghr_database_path(config) -> Path:
    ghr_root = config.get("ghr_root") if config else None
    if not ghr_root:
        raise ValueError("Missing 'ghr_root' in the Pythia configuration.")

    db_path = Path(ghr_root) / "GHR.db"
    if not db_path.is_file():
        raise FileNotFoundError(
            "Legacy one-band soil raster detected, but GHR.db was not found "
            f"under ghr_root: {ghr_root}"
        )
    return db_path.resolve()


def build_ghr_cache(config) -> Dict[int, str]:
    """Load the complete legacy profile map for API compatibility.

    Runtime lookups query and cache individual IDs to avoid copying the full GHR
    database into every worker process, especially on Windows.
    """
    resolved = _ghr_database_path(config)
    return _load_ghr_profiles_cached(str(resolved), resolved.stat().st_mtime_ns)


@lru_cache(maxsize=32768)
def _lookup_ghr_profile_cached(
    db_path: str, modified_ns: int, soil_id: int
) -> Optional[str]:
    del modified_ns
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT profile FROM profile_map "
            "WHERE id = ? AND profile IS NOT NULL AND TRIM(profile) != ''",
            (soil_id,),
        ).fetchone()
    if row is None:
        return None
    return str(row[0]).strip()


def _lookup_ghr_profile(config, soil_id: int) -> Optional[str]:
    resolved = _ghr_database_path(config)
    return _lookup_ghr_profile_cached(
        str(resolved), resolved.stat().st_mtime_ns, soil_id
    )


def _legacy_profile_from_context(k, context, config) -> Optional[str]:
    if k not in context:
        logging.error(
            "Legacy one-band soil raster requires the raster value in context[%r].",
            k,
        )
        return None

    try:
        value = float(str(context[k]))
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError
        soil_id = int(value)
    except (TypeError, ValueError, OverflowError):
        logging.error("Invalid legacy soil ID in context[%r]: %r.", k, context[k])
        return None

    try:
        profile = _lookup_ghr_profile(config, soil_id)
    except (FileNotFoundError, OSError, ValueError, sqlite3.DatabaseError) as exc:
        logging.error("Could not load the legacy GHR soil mapping: %s", exc)
        return None

    if not profile:
        logging.error(
            "Legacy soil ID %d at (%s, %s) was not found in GHR.db.",
            soil_id,
            context.get("lat"),
            context.get("lng"),
        )
        return None
    return profile


@lru_cache(maxsize=256)
def _soil_profiles_in_file(path: str, modified_ns: int):
    del modified_ns
    profiles = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as soil_file:
        for line in soil_file:
            if line.startswith("*"):
                profile = line[1:].strip().split(maxsplit=1)
                if profile:
                    profiles.add(profile[0].upper())
    return profiles


def _soil_file_for_profile(profile_code: str, config) -> Optional[Path]:
    ghr_root = config.get("ghr_root") if config else None
    if not ghr_root:
        logging.error("Missing 'ghr_root' in the Pythia configuration.")
        return None

    soil_path = Path(ghr_root) / f"{profile_code[:2].upper()}.SOL"
    if not soil_path.is_file():
        logging.error(
            "Soil profile %s resolved successfully, but its DSSAT soil file was not found: %s",
            profile_code,
            soil_path,
        )
        return None
    try:
        resolved = soil_path.resolve()
        profiles = _soil_profiles_in_file(
            str(resolved), resolved.stat().st_mtime_ns
        )
    except OSError as exc:
        logging.error("Could not read DSSAT soil file '%s': %s", soil_path, exc)
        return None
    if profile_code.upper() not in profiles:
        logging.error(
            "Soil profile %s was not found inside DSSAT soil file: %s",
            profile_code,
            soil_path,
        )
        return None
    return soil_path


def lookup_ghr(k, run, context, config):
    args = run[k].split("::")[1:]
    if "raster" not in args:
        logging.error("lookup_ghr: Expected raster mode.")
        return None

    raster_idx = args.index("raster")
    if raster_idx + 1 >= len(args):
        logging.error("lookup_ghr: Missing raster path.")
        return None

    raster_path = Path(args[raster_idx + 1])
    if not raster_path.is_file():
        logging.error("Soil raster not found: %s", raster_path)
        return None

    try:
        lat = float(context["lat"])
        lon = float(context["lng"])
    except Exception:
        logging.error("lookup_ghr: Invalid lat/lng in context.")
        return None

    try:
        with rasterio.open(str(raster_path)) as src:
            if src.count == 1:
                logging.debug("Using legacy one-band GHR soil lookup for %s.", raster_path)
                if _point_to_raster_pixel(src, lat, lon) is None:
                    return None
                profile_code = _legacy_profile_from_context(k, context, config)
            elif src.count == 2:
                logging.debug("Using two-band encoded soil lookup for %s.", raster_path)
                profile_code = _get_profile_from_dataset(src, lat, lon)
            else:
                logging.error(
                    "Unsupported soil raster '%s': expected 1 legacy band or 2 encoded bands; found %d.",
                    raster_path,
                    src.count,
                )
                return None
    except (OSError, RasterioIOError) as exc:
        logging.error("Could not open soil raster '%s': %s", raster_path, exc)
        return None

    if not profile_code:
        logging.error(
            "lookup_ghr: No profile found for (%s, %s) in %s",
            lat,
            lon,
            str(raster_path),
        )
        return None

    sol_path = _soil_file_for_profile(profile_code, config)
    if sol_path is None:
        return None

    return {
        k: profile_code,
        "soilFiles": [str(sol_path)],
    }


def split_fert_dap_percent(k, run, context, _):
    args = run[k].split("::")[1:]
    if args[0].startswith("$"):
        search_context = args[0][1:]
        total = float(context[search_context])
    else:
        total = float(args[0])
    # splits = int(args[1])
    split_amounts = args[2:]
    if any(n.startswith("-") for n in split_amounts):
        logging.error(
            "No arguments for split_applications_dap_percent should be negative"
        )
        return None
    daps = [int(i) for i in split_amounts[0::2]]
    percents = [float(i) / 100.0 for i in split_amounts[1::2]]
    if len(daps) != len(percents):
        logging.error("Not enough arguments for split_applications_dap_percent")
        return None
    if sum(percents) != 1.0:
        logging.error(
            "The sum of all percents needs to be 100 in split_applications_dap_percent"
        )
        logging.error(percents)
        return None
    if len(daps) != len(set(daps)):
        logging.error("Days should not be the same in split_applications_dap_percent")
        return None
    out = []
    for i in range(len(daps)):
        app_total = total * percents[i]
        app_dap = daps[i]
        out.append({"fdap": app_dap, "famn": app_total})
    return {k: out}


def assign_by_raster_value(k, run, context, _):
    init_args = run[k].split("::")[1:]
    if "raster" in init_args:
        args = init_args[init_args.index("raster") + 2:]
    else:
        logging.error("Need to specify a raster for %s:assign_by_value", k)
        return None
    raster_val = [int(i) for i in args[0::2]]
    assignment = args[1::2]
    if len(raster_val) != len(assignment):
        logging.error(
            "The values and assignments don't pair up in %s:assign_by_raster_value", k
        )
        return None
    if context[k] in raster_val:
        rv_idx = raster_val.index(context[k])
        return {k: assignment[rv_idx]}
    else:
        logging.error("No assignment for value %d in %s:assign_by_value", context[k], k)
        return None


def date_from_doy_raster(k, run, context, _):
    init_args = run[k].split("::")[1:]
    if "raster" not in init_args:
        logging.error("date_from_doy_raster: No raster specified.")
        return None
    if context[k] < 1 or context[k] > 366:
        logging.error(
            "date_from_doy_raster: Invalid day of year found in raster: %d", context[k]
        )
        return None
    return {
        k: pythia.util.to_iso_date(
            pythia.util.from_julian_date(f'{run["startYear"]}{context[k]}')
        )
    }


def date_offset(k, run, context, _):
    args = run[k].split("::")[1:]
    offset_value = args[-1]
    try:
        offset_value = int(offset_value)
    except ValueError:
        logging.error("date_offset: %s is not an integer", offset_value)
        return None
    if args[0].startswith("$"):
        search_context = args[0][1:]
        if search_context not in context:
            logging.error("date_offset: %s is not in the current context.", args[0])
            return None
        context_date = context[search_context]
        cxt_date = pythia.util.from_iso_date(context_date)
        td = datetime.timedelta(days=offset_value)
        new_date = cxt_date + td
        return {k: pythia.util.to_iso_date(new_date)}
    else:
        logging.error("date_offset only works with references variables.")
        return None


def string_to_number(term):
    try:
        if "." in term:
            return float(term)
        else:
            return int(term)
    except ValueError:
        logging.error("string_to_number: %s is not a number", term)
        return None
