import datetime
import logging

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


def xy_from_list(l):
    return [tuple(x[::-1]) for x in l]


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


def lookup_hc27(k, run, context, _):
    args = run[k].split("::")[1:]
    if "raster" in args:
        return {k: "HC_GEN{:0>4}".format(context[k])}
    else:
        return {k: "HC_GEN{:0>4}".format(args[0])}


def lookup_wth(k, run, context, _):
    args = run[k].split("::")[1:]
    if isinstance(run["sites"], list):
        finder = pythia.io.find_closest_vector_coords
    else:
        finder = pythia.io.find_vector_coords
    if "vector" in args:
        idx = args.index("vector")
        cell_id = finder(
            args[idx + 1], context["lng"], context["lat"], args[idx + 2]
        )
    return {k: args[0], "wthFile": "{}.WTH".format(cell_id)}


def generate_ic_layers(k, run, context, _):
    args = run[k].split("::")[1:]
    if args[0].startswith("$"):
        profile = args[0][1:]
    else:
        profile = args[0]
    soil_file = pythia.soil_handler.findSoilProfile(context[profile], context["soilFiles"])
    layers = pythia.soil_handler.readSoilLayers(context[profile], soil_file)
    calculated_layers = pythia.soil_handler.calculateICLayerData(layers, run)
    layer_labels = ["icbl", "sh2o", "snh4", "sno3"]
    return {k: [dict(zip(layer_labels, cl)) for cl in calculated_layers]}


def lookup_ghr(k, run, context, config):
    import os
    import sqlite3

    args = run[k].split("::")[1:]
    if "raster" in args:
        logging.debug("lookup_ghr - context[%s] => %s", k, context[k])
        with sqlite3.connect(os.path.join(config["ghr_root"], "GHR.db")) as conn:
            c = conn.cursor()
            tif_profile_id = (int(str(context[k])),)
            c.execute("SELECT profile from profile_map WHERE id=?", tif_profile_id)
            id_soil = c.fetchone()
            if id_soil and id_soil[0].strip() != "":
                id_soil = id_soil[0]
                sol_file = "{}.SOL".format(id_soil[:2].upper())
                return {k: id_soil, "soilFiles": [os.path.join(config["ghr_root"], sol_file)]}
            else:
                logging.error("Soil NOT found")
                logging.error(context)
                return None


def split_fert_dap_percent(k, run, context, _):
    args = run[k].split("::")[1:]
    if args[0].startswith("$"):
        total = run[args[0][1:]]
    else:
        total = float(args[0])
    # splits = int(args[1])
    split_amounts = args[2:]
    if any(n.startswith("-") for n in split_amounts):
        logging.error("No arguments for split_applications_dap_percent should be negative")
        return None
    daps = [int(i) for i in split_amounts[0::2]]
    percents = [float(i) / 100.0 for i in split_amounts[1::2]]
    if len(daps) != len(percents):
        logging.error("Not enough arguments for split_applications_dap_percent")
        return None
    if sum(percents) != 1.0:
        logging.error("The sum of all percents needs to be 100 in split_applications_dap_percent")
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
