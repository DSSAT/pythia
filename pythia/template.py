from jinja2 import Environment, FileSystemLoader

_t_formats = {
    "icrt": {"length": 5},
    "icres": {"length": 5},
    "icren": {"length": 5},
    "icbl": {"length": 4},
    "sh2o": {"length": 5},
    "snh4": {"length": 5},
    "sno3": {"length": 5}
}

def init_engine(template_dir):
    return Environment(loader=FileSystemLoader(template_dir),
    trim_blocks=True,
    lstrip_blocks=True
    )

def auto_format_dict(d):
    klean = {}
    for k,v in d.items():
        if k in _t_formats:
            fmt_align = _t_formats[k].get("align", ":>")
            fmt_pad = _t_formats[k].get("padwith", "")
            if isinstance(v, float):
                fmt_len = "{}.1f".format(_t_formats[k]["length"])
            elif isinstance(v, int):
                fmt_len = "{}d".format(_t_formats[k]["length"])
            else:
                fmt_len = "{0}.{0}".format(_t_formats[k]["length"])
            fmt = "{"+fmt_align+fmt_pad+fmt_len+"}"
            klean[k] = fmt.format(v)
        else:
            klean[k] = v
    return klean

def render_template(env, template_file, context):
    template = env.get_template(template_file)
    return template.render(context)