import datetime

import pythia.io
import pythia.soil_handler
import pythia.util


def extract_raster(s):
    args = s.split("::")
    raster_idx = args.index("raster")
    return args[raster_idx+1]


def xy_from_vector(v):
    args = v.split("::")
    return pythia.io.extract_vector_coords(args[1])


def auto_planting_window(k, run, context):
    """multiple rasters not yet supported"""
    args = run[k].split("::")[1:]
    raster_idx = args.index("raster")
    args[raster_idx+1] = context[k]
    args.pop(raster_idx)
    vals = [int(v) for v in args]
    first = datetime.date(run["startYear"], vals[0], vals[1])
    td = datetime.timedelta(days=vals[2])
    last = first + td
    return {"pdate": pythia.util.to_julian_date(first),
            "pfrst": pythia.util.to_julian_date(first),
            "plast": pythia.util.to_julian_date(last)}

def lookup_hc27(k, run, context):
    args = run[k].split("::")[1:]
    if "raster" in args:
        return {k: "HC_GEN{:0>4}".format(context[k])}
    else:
        return {k: "HC_GEN{:0>4}".format(args[0])}

def lookup_wth(k, run, context):
    args = run[k].split("::")[1:]
    if "vector" in args:
        idx = args.index("vector")
        cellid = pythia.io.find_vector_coords(args[idx+1],context["lng"], context["lat"], args[idx+2])
        return {k:args[0], "wthFile": "{}.WTH".format(cellid)}

def generate_ic_layers(k, run, context):
    args = run[k].split("::")[1:]
    if args[0].startswith("$"):
        profile = args[0][1:]
    else:
        profile = args[0]
    soilFile = pythia.soil_handler.findSoilProfile(context[profile], run["soils"])
    layers = pythia.soil_handler.readSoilLayers(context[profile], soilFile)
    calculatedLayers = pythia.soil_handler.calculateICLayerData(layers, run)
    l = ["icbl", "sh2o", "snh4", "sno3"]
    return {k: [pythia.template.auto_format_dict(dict(zip(l, cl))) for cl in calculatedLayers]}

