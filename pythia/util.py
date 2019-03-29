import datetime

import pythia.functions


def to_julian_date(d):
    return d.strftime("%y%j")


def from_julian_date(s):
    return datetime.datetime.strptime(s, "%y%j").date()


def build_template_default_formats(keys):
    return ["{" + ":> {}".format(len(k)) + "d}" for k in keys]

# destructive and I don't like it! Refactor this!
def override_template_default_format(keys, formats, kv):
    for key, fmt in kv.items():
        if key in keys:
            idx = keys.index(key)
            formats[idx] = fmt

def build_template_default_values(formats, value):
    return [s.format(value) for s in formats]

def template_format_helper(keys, formats, key, value):
    if key in keys:
        idx = keys.index(key)
        return formats[idx].format(value)

def get_rasters_list(iter):
    return list(set([pythia.functions.extract_raster(raster) for raster in list(filter(lambda x: "raster::" in str(x), iter))]))

def get_rasters_dict(iter):
    return {k:pythia.functions.extract_raster(v) for (k,v) in iter.items() if "raster::" in str(v)}

def translate_coords_news(lat,lng):
    y = ""
    x = ""
    if lng >= 0:
        y = "{:.3f}N".format(lng).replace(".", "_")
    else:
        y = "{:.3f}S".format(abs(lng)).replace(".", "_")
    if lat >= 0:
        x = "{:.3f}E".format(lat).replace(".", "_")
    else:
        x = "{:.3f}W".format(abs(lat)).replace(".", "_")
    return (y,x)

