from jinja2 import Environment, FileSystemLoader
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
    "sh2o": {"length": 6},
    "snh4": {"length": 6},
    "sno3": {"length": 6},
    "fdate": {"length": 5},
    "fdap": {"length": 5},
    "famn": {"length": 5},
    "ramt": {"length": 6},
    "sdate": {"length": 5},
    "nyers": {"length": 5},
    "flhst": {"length": 5},
    "fhdur": {"length": 5},
    "irrig": {"length": 5},
    "erain": {"length": 5}
}

_t_date_fields = ["sdate", "fdate", "pfrst", "plast", "pdate"]


def init_engine(template_dir):
    return Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)


def auto_format_dict(d):
    if isinstance(d, str):
        return d
    clean = {}
    for k, v in d.items():
        if k in _t_date_fields and "::" not in v:
            clean[k] = pythia.util.to_julian_date(pythia.util.from_iso_date(v))
        elif k in _t_formats:
            fmt = ""
            if "fmt" in _t_formats[k]:
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
            clean[k] = fmt.format(v)
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
