import pythia.plugin
import numpy as np
import pandas as pd

def pest_infestation(config, input, **kwargs):
    """
    This is a simple pest infestation model that reduces yield based on a severity parameter.
    """
    if "err" in input and len(input["err"].decode()) > 0:
        return None
    if "params" not in config or "pest_infestation_severity" not in config["params"]:
        return None

    severity = config["params"]["pest_infestation_severity"]
    biomass_effect = config["params"].get("pest_infestation_biomass_effect", 0.5)
    summary_file = f"{input['loc']}/summary.csv"
    try:
        summary = pd.read_csv(summary_file)
        summary["HWAM"] = summary["HWAM"] * (1 - severity)
        summary["CWAM"] = summary["CWAM"] * (1 - severity * biomass_effect)
        summary.to_csv(summary_file, index=False)
    except FileNotFoundError:
        pass
    return input


def initialize(plugin_config, plugins, config):
    """
    This function is called by the plugin manager to initialize the plugin.
    """
    plugins = pythia.plugin.register_plugin_function(
        pythia.plugin.PluginHook.post_run_pixel_success,
        pest_infestation,
        plugin_config,
        plugins,
    )
    return plugins
