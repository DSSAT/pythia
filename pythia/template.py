from jinja2 import Environment, FileSystemLoader

_t_formats = {
    "icrt": {"length": 6},
    "icres": {"length": 6},
    "icren": {"length": 6},
    "icbl": {"length": 6},
    "sh2o": {"length": 6},
    "snh4": {"length": 6},
    "sno3": {"length": 6}
}


def init_engine(template_dir):
    return Environment(loader=FileSystemLoader(template_dir),
                       trim_blocks=True,
                       lstrip_blocks=True
                       )


def auto_format_dict(d):
    if isinstance(d, str):
        return d
    clean = {}
    for k, v in d.items():
        if k in _t_formats:
            fmt_align = _t_formats[k].get("align", ":>")
            fmt_pad = _t_formats[k].get("pad_with", "")
            if isinstance(v, float):
                fmt_len = "{}.1f".format(_t_formats[k]["length"])
            elif isinstance(v, int):
                fmt_len = "{}d".format(_t_formats[k]["length"])
            else:
                fmt_len = "{0}.{0}".format(_t_formats[k]["length"])
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
