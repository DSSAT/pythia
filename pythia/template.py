from jinja2 import Environment, FileSystemLoader
import logging
import pythia.functions
import pythia.util

_t_formats = {
    "ingeno": {"length": 6},
    "cname": {"fmt": ""},  # leave alone
    "wsta": {"align": ":<", "length": 8},
    "id_soil": {"align": ":<", "length": 10},
    "xcrd": {"fmt": ":>15.3f"},
    "ycrd": {"fmt": ":>15.3f"},
    "icrt": {"length": 6},
    "icres": {"length": 6},
    "icren": {"length": 6},
    "icbl": {"length": 6},
    "sh2o": {"fmt": ":>6.3f"},
    "snh4": {"fmt": ":>6.2f"},
    "sno3": {"fmt": ":>6.2f"},
    "fdate": {"length": 5},
    "fdap": {"length": 5},
    "famn": {"length": 5},
    "ramt": {"length": 6},
    "sdate": {"length": 5},
    "nyers": {"length": 5},
    "flhst": {"length": 5},
    "fhdur": {"length": 5},
    "irrig": {"length": 5},
    "ph2ol": {"length": 5},
    "fodate": {"length": 7},
    "pdate": {"length": 5},
    "pfrst": {"length": 5},
    "plast": {"length": 5},
    "hdate": {"length": 5},
    "ppop": {"length": 5},
    "plrs": {"length": 3},
}

_t_date_fields = ["sdate", "fdate", "pfrst", "plast", "pdate", "hdate"]
_t_date_fields_4 = ["fodate"]
_t_envmod_fields = ["eday", "erad", "emax", "emin", "erain", "eco2", "edew", "ewind"]


def init_engine(template_dir):
    return Environment(
        loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    )


def wrap_format(k, v):
    fmt = ""
    if k in _t_formats:
        if "raw" in _t_formats[k]:
            fmt = _t_formats[k]["raw"]
        elif "fmt" in _t_formats[k]:
            fmt = "{" + _t_formats[k]["fmt"] + "}"
        else:
            fmt_align = _t_formats[k].get("align", ":>")
            fmt_pad = _t_formats[k].get("pad_with", "")
            if isinstance(v, float):
                fmt_len = "{}.1f".format(_t_formats[k]["length"])
            elif isinstance(v, int):
                fmt_len = "{}d".format(_t_formats[k]["length"])
            else:
                if "length" in _t_formats[k]:
                    fmt_len = "{}".format(_t_formats[k]["length"])
                else:
                    fmt_len = ""
            fmt = "{" + fmt_align + fmt_pad + fmt_len + "}"
    else:
        fmt = "{}"
    return fmt.format(v)


def envmod_format(v):
    fmt = "{}{:>4}"
    valid_mod = ["R", "A", "M", "S"]
    try:
        mod, raw = v[0], v[1:]
    except TypeError:
        logging.error("%s is not a valid value for envmod.", v)
        return fmt.format("A", "0")
    if mod not in valid_mod:
        logging.error('"%s" is not a valid envmod modifier.', mod)
        return fmt.format("A", "0")
    val = pythia.functions.string_to_number(raw)
    if val is None:
        return fmt.format("A", "0")
    return "{}{:>4}".format(mod, val)


def auto_format_dict(d):
    if isinstance(d, str):
        return d
    clean = {}
    for k in _t_formats:
        v = _t_formats[k]
        if "default" in v:
            clean[k] = wrap_format(k, v["default"])
        else:
            clean[k] = wrap_format(k, -99)
    for k in _t_envmod_fields:
        clean[k] = envmod_format("A0")
    for k, v in d.items():
        if v == "-99" or v == -99:
            clean[k] = wrap_format(k, v)
        else:
            if k in _t_date_fields and "::" not in v:
                clean[k] = pythia.util.to_julian_date(pythia.util.from_iso_date(v))
            elif k in _t_date_fields_4 and "::" not in v:
                clean[k] = pythia.util.to_julian_date_4(pythia.util.from_iso_date(v))
            elif k in _t_envmod_fields:
                clean[k] = envmod_format(v)
            elif k in _t_formats:
                clean[k] = wrap_format(k, v)
            elif isinstance(v, dict):
                clean[k] = auto_format_dict(v)
            elif isinstance(v, list) and not isinstance(v, str):
                if k == "sites":
                    continue
                else:
                    clean[k] = [auto_format_dict(intern) for intern in v]
            else:
                clean[k] = v
    return clean


def render_template(env, template_file, context, auto_format=True):
    template = env.get_template(template_file)
    if auto_format:
        context = auto_format_dict(context)
    return template.render(context)
