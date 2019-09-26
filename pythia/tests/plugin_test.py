from pythia.plugin import PluginHook, register_plugin_function, load_plugins, run_plugin_functions


def test_register_with_invalid_hook():
    plugins = {}
    plugins1 = register_plugin_function("false_hook", "not a function", "", plugins)
    assert plugins1 == {}


def test_register_with_invalid_fun():
    plugins = {}
    plugins1 = register_plugin_function(PluginHook.analyze_file, "not a function", "", plugins)
    assert plugins1 == {}


def test_register_with_invalid_config():
    plugins = {}
    plugins1 = register_plugin_function(PluginHook.post_analysis, sample_function, "", plugins)
    assert plugins1 == {}


def test_register_twice():
    plugins = {}
    plugins1 = {}
    plugins2 = {}
    plugins1 = register_plugin_function(PluginHook.analyze_file, sample_function, {}, plugins)
    plugins2 = register_plugin_function(
        PluginHook.analyze_file, sample_function, {"a": 1}, plugins1
    )
    assert plugins1 == {PluginHook.analyze_file: [{"fun": sample_function, "config": {}}]}
    assert plugins1 == plugins2


def test_register_properly():
    plugins = {}
    plugins1 = {}
    plugins1 = register_plugin_function(PluginHook.post_build_context, sample_function, {}, plugins)
    assert plugins1 == {PluginHook.post_build_context: [{"fun": sample_function, "config": {}}]}


def sample_function(config, context):
    return context


def test_load_plugin():
    import pythia.plugins.test_plugin

    config = {"plugins": [{"plugin": "test_plugin", "params": {}}]}
    plugins = {}
    plugins1 = {}
    plugins1 = load_plugins(config, plugins)
    assert PluginHook.post_config in plugins1
    assert plugins1[PluginHook.post_config] == [
        {"fun": pythia.plugins.test_plugin.sample_function, "config": {}}
    ]
    assert plugins1 != {PluginHook.post_config: [{"fun": sample_function, "config": {}}]}


def test_plugin_manual_execution():
    config = {"plugins": [{"plugin": "test_plugin", "params": {}}]}
    plugins = {}
    plugins1 = {}
    plugins1 = load_plugins(config, plugins)

    for plugin in plugins1[PluginHook.post_config]:
        assert 1 == plugin["fun"]()


def test_plugin_auto_execution():
    config = {"plugins": [{"plugin": "test_plugin", "params": {}}]}
    plugins = {}
    plugins1 = {}
    plugins1 = load_plugins(config, plugins)
    context = {"context_value": 7}
    context1 = run_plugin_functions(PluginHook.post_build_context, plugins1, context=context)
    context2 = run_plugin_functions(PluginHook.post_build_context, plugins1)
    assert context1 != context
    assert context1["context_value"] == 8
    assert context2["context_value"] == 3


def test_no_plugin_does_not_change_context():
    config = {"plugins": [{"plugin": "test_plugin", "params": {}}]}
    plugins = {}
    plugins1 = load_plugins(config, plugins)
    context = {"hello": "there"}
    context1 = run_plugin_functions(PluginHook.post_build_context, plugins, context=context)
    assert context == context1
    context2 = run_plugin_functions(PluginHook.post_build_context, plugins1, context=context)
    assert context1 != context2
    assert(context2 == {**context, **{"context_value": 3}})
