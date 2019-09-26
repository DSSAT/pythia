import logging
from pythia.plugin import PluginHook, register_plugin_function


def initialize(config, plugins, full_config):
    logging.info("[TEST PLUGIN] Initializing plugin")
    plugins = register_plugin_function(PluginHook.post_config, sample_function, config, plugins)
    plugins = register_plugin_function(
        PluginHook.post_build_context, contexted_function, config, plugins
    )
    return plugins


def sample_function(config={}):
    retval = config.get("value", 1)
    logging.info("[TEST PLUGIN] Running the sample_function()")
    return retval


def contexted_function(config={}, context={}):
    logging.info("[TEST PLUGIN] Running the contexted_function()")
    context["context_value"] = context.get("context_value", 2) + 1
    return context
