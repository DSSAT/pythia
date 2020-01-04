import datetime
import itertools
import logging
from pythia.plugin import register_plugin_function, PluginHook
import pythia.util


"""
Configuration:

"plugins": [
    "plugin": "sensitivity_plugin",
    "params": {
        "fen_tot" : {
            "method": "offset",
            "values": [0, 25, 50, 75, 100]
        },
        "erain" : {
            "method": "env_mod",
            "values" : ["M0.25", "M1.0", "M1.25"]
        }
    },
    "order": 1
]
"""


"""
Post application:
{
    "fen_tot": 125,
    "erain":"M0.25",
    "_sens_post_context":[{},{}]
}
"""


def initialize(config, plugins, full_config):
    logging.info("[Sensitivity Plugin] Initializing plugin")
    plugins = register_plugin_function(PluginHook.post_config, generate_sensitivity_runs, config,
                                       plugins)
    plugins = register_plugin_function(PluginHook.post_build_context, post_build_context_apply_factors, config, plugins)
    plugins = register_plugin_function(PluginHook.post_build_context,
                                       post_build_context_apply_static_factors, config, plugins)
    return plugins


def _assign_static(sens, hook, key, plugin_config):
    if key not in sens[hook]:
        sens[hook][key] = []
    sens[hook][key].append({"var": key, "method": plugin_config[key]["method"],
                            "val": plugin_config[key]["value"], "hook": hook,
                            "from": plugin_config[key].get("from", key)})


def _assign_factorial(sens, hook, key, plugin_config):
    if key not in sens[hook]:
        sens[hook][key] = []
    for v in plugin_config[key]["values"]:
        sens[hook][key].append({"var": key, "method": plugin_config[key]["method"], "val": v, "hook": hook})


def merge_static(statics, factor):
    return list(factor) + statics


def generate_sensitivity_runs(plugin_config={}, full_config={}):
    sens = {"_sens_pre_context": {},
            "_sens_pre_context_static": {},
            "_sens_post_context": {},
            "_sens_post_context_static": {}}
    # First we organize them
    for k in plugin_config.keys():
        hook = plugin_config[k].get("hook", "post_config").casefold()
        static = plugin_config[k].get("static", False)
        context_string = None
        if hook == "post_config":
            context_string = "_sens_pre_context"
        elif hook == "post_build_context":
            context_string = "_sens_post_context"
        if static:
            _assign_static(sens, context_string+"_static", k, plugin_config)
        else:
            _assign_factorial(sens, context_string, k, plugin_config)

    factorial = list(itertools.product(*[*sens["_sens_pre_context"].values(), *sens["_sens_post_context"].values()]))
    statics = list(itertools.chain.from_iterable(
        [*sens["_sens_pre_context_static"].values(), *sens["_sens_post_context_static"].values()]))
    factors = [merge_static(statics, f) for f in factorial]
    # Next we generate the new runs for each analysis
    runs = full_config.get("runs", [])
    out_runs = []
    for run in runs:
        current_name = run["name"]
        current_workDir = run["workDir"]
        for factor in factors:
            f = generate_factorial_name(factor)
            run["name"] = current_name + "__" + f
            run["workDir"] = current_workDir + "__" + f
            out_runs.append({**run, **{"_sens": factor}})
    out_runs = [apply_factors("_sens_pre_context", run) for run in out_runs]
    out_runs = [apply_factors("_sens_pre_context_static", run) for run in out_runs]
    full_config["runs"] = out_runs
    return full_config


def generate_factorial_name(factors):
    return "__".join([factor["var"]+str(factor["val"]) for factor in factors if factor["hook"].endswith("context")])


def post_build_context_apply_factors(config={}, context={}):
    return apply_factors("_sens_post_context", context)


def post_build_context_apply_static_factors(config={}, context={}):
    return apply_factors("_sens_post_context_static", context)


def apply_factors(hook, current_context):
    if current_context is None:
        return
    call_list = {"date_offset": date_offset,
                 "offset": offset,
                 "env_mod": env_mod}
    current_factors = [f for f in current_context["_sens"] if f["hook"] == hook]
    for cf in current_factors:
        cval = None
        if hook.endswith("static"):
            cval = current_context[cf["from"]]
        else:
            cval = current_context[cf["var"]]
        if cf["method"] in call_list:
            current_context[cf["var"]] = call_list[cf["method"]](cval, cf["val"])
    return current_context


def date_offset(d, offset):
    c_date = None
    if isinstance(d, datetime.datetime):
        c_date = d
    else:
        if len(d) == 5:
            c_date = pythia.util.from_julian_date(d)
        else:
            c_date = pythia.util.from_iso_date(d)
    c_offset = datetime.timedelta(offset)
    return pythia.util.to_iso_date(c_date + c_offset)


def offset(v, offset):
    return v+offset


def env_mod(v, value):
    return value
