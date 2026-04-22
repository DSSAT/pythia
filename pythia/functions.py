import datetime
import logging
import os
from pathlib import Path
from typing import Optional

import rasterio

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

    first = datetime.datetime(run["startYear"], 1, 1) + datetime.timedelta(int(cell_doy) + int(args[idx + 3]) )
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
    return {k: args[0], "wthFile": "{}.WTH".format(int(cell_id))}


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
        return chr(a) + chr(b)

    b0 = (code >> 24) & 0xFF
    b1 = (code >> 16) & 0xFF
    b2 = (code >> 8) & 0xFF
    b3 = code & 0xFF

    for x in (b0, b1, b2, b3):
        if not (32 <= x <= 126):
            raise ValueError("invalid packed-ascii byte")

    return bytes([b0, b1, b2, b3]).decode("ascii")


def build_profile_code_from_bands(prefix_code: int, numeric_id: int) -> str:
    prefix = decode_prefix(prefix_code)
    n = int(numeric_id)

    if len(prefix) == 2:
        return f"{prefix}{n:08d}"
    if len(prefix) == 4:
        return f"{prefix}{n:06d}"

    raise ValueError("invalid decoded prefix length")


def get_profile_from_raster(lat: float, lon: float, raster_path: Path) -> Optional[str]:
    if not raster_path.exists():
        logging.error("Raster not found: %s", str(raster_path))
        return None

    with rasterio.open(str(raster_path)) as src:
        try:
            row, col = src.index(lon, lat)
        except Exception:
            logging.warning("Point (%s, %s) outside raster.", lat, lon)
            return None

        if src.count < 2:
            logging.error("Raster '%s' must have 2 bands. Found %d.", str(raster_path), src.count)
            return None

        b1 = src.read(1)[row, col]
        b2 = src.read(2)[row, col]

        nodata = src.nodata if src.nodata is not None else 0

        try:
            b1i = int(b1)
            b2i = int(b2)
        except Exception:
            logging.error("Non-integer band values at (%s, %s): b1=%s b2=%s", lat, lon, str(b1), str(b2))
            return None

        if b1i == int(nodata) and b2i == int(nodata):
            return None

        try:
            return build_profile_code_from_bands(b1i, b2i)
        except Exception:
            logging.error("Failed to decode bands at (%s, %s): b1=%d b2=%d", lat, lon, b1i, b2i)
            return None


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

    try:
        lat = float(context["lat"])
        lon = float(context["lng"])
    except Exception:
        logging.error("lookup_ghr: Invalid lat/lng in context.")
        return None

    profile_code = get_profile_from_raster(lat, lon, raster_path)
    if not profile_code:
        logging.error("lookup_ghr: No profile found for (%s, %s) in %s", lat, lon, str(raster_path))
        return None

    sol_prefix = profile_code[:2].upper()
    sol_path = os.path.join(config["ghr_root"], f"{sol_prefix}.SOL")

    return {
        k: profile_code,
        "soilFiles": [sol_path],
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
        args = init_args[init_args.index("raster") + 2 :]
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
