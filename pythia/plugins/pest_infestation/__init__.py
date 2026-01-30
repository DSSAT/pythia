import pythia.plugin as plugin

def initialize(plugin_config, plugins, config):
    """
    Initializes the pest infestation plugin.

    Args:
        plugin_config (dict): The plugin configuration.
        plugins (dict): The dictionary of registered plugins.
        config (dict): The global configuration.

    Returns:
        dict: The updated dictionary of registered plugins.
    """
    plugins = plugin.register_plugin_function(
        plugin.PluginHook.post_build_context, run, plugin_config, plugins
    )
    return plugins

def run(config, context, **kwargs):
    """
    Runs the pest infestation plugin.

    This plugin simulates the impact of pest infestation on crop yield by reducing
    the harvest yield by a configurable percentage. The severity of the infestation
    is controlled by the `pest_severity` parameter in the plugin configuration.

    Args:
        config (dict): The plugin configuration.
        context (dict): The context for the current run.
        **kwargs: Additional keyword arguments.

    Returns:
        dict: The updated context.
    """
    if "pest_severity" in config:
        pest_severity = float(config["pest_severity"])
        if "HARVS" in context:
            for harvest in context["HARVS"]:
                # Reduce the harvest yield by the pest severity percentage
                harvest["HWAM"] *= (1.0 - pest_severity)
    return context
