import logging
from pythia.plugin import PluginHook, register_plugin_function


def initialize(config, plugins, full_config):
    logging.info("[TEST PLUGIN] Initializing plugin")
    plugin_config = config.get("params", {})
    plugins = register_plugin_function(
        PluginHook.post_config, sample_function, plugin_config, plugins
    )
    plugins = register_plugin_function(
        PluginHook.post_build_context, contexted_function, plugin_config, plugins
    )
    plugins = register_plugin_function(
        PluginHook.post_peerless_pixel_success,
        on_peerless_success,
        plugin_config,
        plugins,
    )
    plugins = register_plugin_function(
        PluginHook.post_peerless_pixel_skip, on_peerless_skip, plugin_config, plugins
    )
    plugins = register_plugin_function(
        PluginHook.post_run_pixel_success,
        on_run_pixel_success,
        plugin_config,
        plugins,
    )
    plugins = register_plugin_function(
        PluginHook.post_run_pixel_failed, on_run_pixel_failed, plugin_config, plugins
    )
    return plugins


def sample_function(config=None, **kwargs):
    config = config or {}
    retval = config.get("value", 1)
    logging.info("[TEST PLUGIN] Running the sample_function()")
    return {**kwargs, "config": config, "retval": retval}


def contexted_function(config=None, context=None, **kwargs):
    logging.info("[TEST PLUGIN] Running the contexted_function()")
    context = dict(context or {})
    context["context_value"] = context.get("context_value", 2) + 1
    return {**kwargs, "context": context}


def on_peerless_success(*args, **kwargs):
    logging.info("[TEST PLUGIN] peerless success")
    return kwargs


def on_peerless_skip(*args, **kwargs):
    logging.info("[TEST PLUGIN] peerless skip")
    return kwargs


def on_run_pixel_success(*args, **kwargs):
    logging.info("[TEST PLUGIN] run pixel success")
    return kwargs


def on_run_pixel_failed(*args, **kwargs):
    logging.info("[TEST PLUGIN] run pixel failed")
    return kwargs
