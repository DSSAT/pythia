from jinja2 import Environment, FileSystemLoader

_t_formats = {
    "xcrd": {"format": "{:>7.3f}"},
    "ycrd": {"format": "{:>7.3f}"},
    "tname": {"length": 25, "align": ":<"},
    "mp": {"length": 2},
    "mh": {"length": 2},
    "icrt": {"length": 6},
    "icres": {"length": 6},
    "icren": {"length": 6},
    "icbl": {"length": 6},
    "sh2o": {"format":"{:>5.2f}"},
    "snh4": {"length": 6},
    "sno3": {"length": 6},
    "pdate": {"length": 5},
    "hdate": {"length": 5},
    "nyers": {"length": 5},
    "id_soil": {"length": 10}
}


def init_engine(template_dir):
    return Environment(loader=FileSystemLoader(template_dir),
                       trim_blocks=True,
                       lstrip_blocks=True
                       )


def auto_format_dict(d):
    if isinstance(d, str) or isinstance(d, tuple):
        return d
    clean = {}
    for k, v in d.items():
        if k in _t_formats:
            if "format" in _t_formats[k]:
                fmt = _t_formats[k]["format"]
            else:
                fmt_align = _t_formats[k].get("align", ":>")
                fmt_pad = _t_formats[k].get("pad_with", "")
                if isinstance(v, float):
                    fmt_len = "{}f".format(_t_formats[k]["length"])
                elif isinstance(v, int):
                    fmt_len = "{}d".format(_t_formats[k]["length"])
                else:
                    fmt_len = "{0}.{0}".format(_t_formats[k]["length"], _t_formats[k].get("precision",2))
                fmt = "{" + fmt_align + fmt_pad + fmt_len + "}"
            clean[k] = fmt.format(v)
        elif isinstance(v, dict):
            clean[k] = auto_format_dict(v)
        elif isinstance(v, list) and not isinstance(v, str):
            clean[k] = [auto_format_dict(intern) for intern in v]
        else:
            clean[k] = v
    return clean


def render_template(env, template_file, context, auto_format=True):
    template = env.get_template(template_file)
    if auto_format:
        context = auto_format_dict(context)
    return template.render(context)
