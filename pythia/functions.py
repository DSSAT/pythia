import datetime

import logging
import os

from pythia.cache_manager import cache
import pythia.io
import pythia.soil_handler
import pythia.template
import pythia.util


def extract_raster(s):
    args = s.split("::")
    raster_idx = args.index("raster")
    return args[raster_idx + 1]


def xy_from_vector(v):
    args = v.split("::")
    return pythia.io.extract_vector_coords(args[1])


def xy_from_list(lst):
    return [tuple(x[::-1]) for x in lst]


def auto_planting_window(k, run, context, _):
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


def build_ghr_cache(config):
    import sqlite3

    with sqlite3.connect(os.path.join(config["ghr_root"], "GHR.db")) as conn:
        ghr_profiles = {}
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profile_map where profile != ''")
        for row in cursor.fetchall():
            ghr_profiles[row["id"]] = row["profile"]

        cache["ghr_profiles"] = ghr_profiles;

    pass


def lookup_ghr(k, run, context, config):
    args = run[k].split("::")[1:]
    if "raster" in args:
        logging.debug("lookup_ghr - context[%s] => %s", k, context[k])
        if "ghr_profiles" not in cache:
            build_ghr_cache(config)
        tif_profile_id = int(float(str(context[k])))
        if tif_profile_id not in cache["ghr_profiles"]:
            logging.error(
                "Invalid soil ID (%d) at (%f,%f)",
                tif_profile_id,
                context["lng"],
                context["lat"],
            )
            return None
        id_soil = cache["ghr_profiles"][tif_profile_id]
        if id_soil and id_soil.strip() != "":
            sol_file = "{}.SOL".format(id_soil[:2].upper())
            return {
                k: id_soil,
                "soilFiles": [os.path.join(config["ghr_root"], sol_file)],
            }
        else:
            logging.error(
                "Soil NOT found for id: %s at (%f,%f)",
                tif_profile_id,
                context["lng"],
                context["lat"],
            )
            return None


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
