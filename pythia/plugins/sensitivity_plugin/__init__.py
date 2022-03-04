import datetime
import itertools
import logging
import os
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
    "no_rename": true, (optional, defaults to false)
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
    cfg = config["params"]
    cfg["no_rename"] = config.get("no_rename", False)
    plugins = register_plugin_function(
        PluginHook.post_config, generate_sensitivity_runs, cfg, plugins
    )
    plugins = register_plugin_function(
        PluginHook.post_build_context, post_build_context_apply_factors, cfg, plugins
    )
    plugins = register_plugin_function(
        PluginHook.post_build_context,
        post_build_context_apply_static_factors,
        cfg,
        plugins,
    )
    return plugins


def _assign_static(sens, hook, key, plugin_config):
    if key not in sens[hook]:
        sens[hook][key] = []
    sens[hook][key].append(
        {
            "var": key,
            "method": plugin_config[key]["method"],
            "val": plugin_config[key]["value"],
            "hook": hook,
            "from": plugin_config[key].get("from", key),
        }
    )


def _assign_factorial(sens, hook, key, plugin_config):
    if key not in sens[hook]:
        sens[hook][key] = []
    for v in plugin_config[key]["values"]:
        sens[hook][key].append(
            {"var": key, "method": plugin_config[key]["method"], "val": v, "hook": hook}
        )


def merge_static(statics, factor):
    return list(factor) + statics


def _uniq_factors(factor_list):
    uniq = []
    for factors in factor_list:
        if len(uniq) == 0:
            uniq.append(factors)
        else:
            uniq_test = [u == factors for u in uniq]
            if True in uniq_test:
                pass
            else:
                uniq.append(factors)
    return uniq




def generate_sensitivity_runs(plugin_config={}, full_config={}):
    sens = {
        "_sens_pre_context": {},
        "_sens_pre_context_static": {},
        "_sens_post_context": {},
        "_sens_post_context_static": {},
    }
    # First we organize them
    runs = full_config.get("runs", {})
    for k in plugin_config.keys():
        if k == "no_rename":
            continue
        hook = plugin_config[k].get("hook", "post_config").casefold()
        static = plugin_config[k].get("static", False)
        context_string = None
        if hook == "post_config":
            context_string = "_sens_pre_context"
        elif hook == "post_build_context":
            context_string = "_sens_post_context"
        if static:
            _assign_static(sens, context_string + "_static", k, plugin_config)
        else:
            _assign_factorial(sens, context_string, k, plugin_config)

    factorial = list(
        itertools.product(
            *[*sens["_sens_pre_context"].values(), *sens["_sens_post_context"].values()]
        )
    )
    statics = list(
        itertools.chain.from_iterable(
            [
                *sens["_sens_pre_context_static"].values(),
                *sens["_sens_post_context_static"].values(),
            ]
        )
    )
    combined_factors = [merge_static(statics, f) for f in factorial]
    # Next we generate the new runs for each analysis
    out_runs = []
    for run in runs:
        current_name = run["name"]
        current_workDir = run["workDir"]
        prefilter = [filter_unfactorable(run, f) for f in combined_factors]
        uniq = _uniq_factors(prefilter)
        for factors in uniq:
            if not plugin_config.get("no_rename", False):
                f = generate_factorial_name(factors)
                run["name"] = current_name + "__" + f
                run["workDir"] = current_workDir + "__" + f
            out_runs.append({**run, **{"_sens": factors}})
    out_runs = [apply_factors("_sens_pre_context", run) for run in out_runs]
    out_runs = [apply_factors("_sens_pre_context_static", run) for run in out_runs]
    full_config["runs"] = out_runs
    return full_config


def generate_factorial_name(factors):
    return "__".join(
        [
            factor["var"] + str(factor["val"])
            for factor in factors
            if factor["hook"].endswith("context")
        ]
    )


def _factorable(run, factor):
    if factor["hook"].endswith("static"):
        var = factor["from"]
    else:
        var = factor["var"]
    if factor["method"] != "env_mod" and var not in run:
        logging.error("sensitivity_plugin: %s requires %s to be specified in the JSON config file. This factor is NOT being applied to run %s", factor["method"], var, run["name"]) 
        return False 
    else:
        return True


def filter_unfactorable(run, factors):
    return [f for f in factors if _factorable(run, f)]


def post_build_context_apply_factors(config={}, context={}):
    return apply_factors("_sens_post_context", context)


def post_build_context_apply_static_factors(config={}, context={}):
    return apply_factors("_sens_post_context_static", context)


def apply_factors(hook, current_context):
    if current_context is None:
        return
    call_list = {"date_offset": date_offset, "offset": offset, "env_mod": env_mod}
    current_factors = [f for f in current_context["_sens"] if f["hook"] == hook]
    for cf in current_factors:
        cval = None
        if hook.endswith("static"):
            cvar = cf["from"]
        else:
            cvar = cf["var"]
        cval = current_context.get(cvar, -99)
        if cval == -99 and cf["method"] != "env_mod":
            logging.error("sensitivity_plugin: %s requires %s to be specified in the JSON config file. This factor is NOT being applied.", cf["method"], cvar) 
        else:
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
    return v + offset


def env_mod(v, value):
    return value
