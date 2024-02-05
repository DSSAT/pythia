import logging
import multiprocessing as mp
import concurrent.futures
import os

import pythia.functions
import pythia.io
import pythia.plugin
import pythia.template
import pythia.util


def build_context(run, ctx, config, plugins):
    if not config["silence"]:
        print("+", end="", flush=True)
    context = run.copy()
    context = {**context, **ctx}
    y, x = pythia.util.translate_coords_news(context["lat"], context["lng"])
    context["contextWorkDir"] = os.path.join(context["workDir"], y, x)
    for k, v in run.items():
        if "::" in str(v) and k != "sites":
            fn = v.split("::")[0]
            if fn != "raster":
                res = getattr(pythia.functions, fn)(k, run, context, config)
                if res is not None:
                    context = {**context, **res}
                else:
                    context = None
                    break

    hook = pythia.plugin.PluginHook.post_peerless_pixel_success
    if context is None:
        hook = pythia.plugin.PluginHook.post_peerless_pixel_skip

    context = pythia.plugin.run_plugin_functions(
        hook,
        plugins,
        context=context,
        args={"run": run, "config": config, "ctx": ctx},
    ).get("context", context)

    return context


def _generate_context_args(runs, peers, config, plugins):
    for idx, run in enumerate(runs):
        for peer in peers[idx]:
            yield run, peer, config, plugins


def symlink_wth_soil(output_dir, config, context):
    if "include" in context:
        for include in context["include"]:
            if os.path.exists(include):
                include_file = os.path.join(output_dir, os.path.basename(include))
                if not os.path.exists(include_file):
                    os.symlink(os.path.abspath(include), include_file)
    if "weatherDir" in config:
        weather_file = os.path.join(output_dir, "{}.WTH".format(context["wsta"]))
        if not os.path.exists(weather_file):
            os.symlink(
                os.path.abspath(os.path.join(config["weatherDir"], context["wthFile"])),
                os.path.join(weather_file),
            )
    for soil in context["soilFiles"]:
        soil_file = os.path.join(output_dir, os.path.basename(soil))
        if not os.path.exists(soil_file):
            os.symlink(
                os.path.abspath(soil), os.path.join(output_dir, os.path.basename(soil))
            )


def compose_peerless(context, config, env):
    if not config["silence"]:
        print(".", end="", flush=True)
    this_output_dir = context["contextWorkDir"]
    symlink_wth_soil(this_output_dir, config, context)
    xfile = pythia.template.render_template(env, context["template"], context)
    with open(os.path.join(context["contextWorkDir"], context["template"]), "w") as f:
        f.write(xfile)
    return context["contextWorkDir"]


def process_context(context, plugins, config, env):
    if context is not None:
        pythia.io.make_run_directory(context["contextWorkDir"])
        # Post context hook
        logging.debug("[PEERLESS] Running post_build_context plugins")
        context = pythia.plugin.run_plugin_functions(
            pythia.plugin.PluginHook.post_build_context,
            plugins,
            context=context,
        ).get("context", context)
        compose_peerless_result = compose_peerless(context, config, env)
        compose_peerless_result = pythia.plugin.run_plugin_functions(
            pythia.plugin.PluginHook.post_compose_peerless_pixel_success,
            plugins,
            context=context,
            compose_peerless_result=compose_peerless_result,
            config=config,
            env=env,
        ).get("compose_peerless_result", compose_peerless_result)
        return os.path.abspath(compose_peerless_result)
    else:
        pythia.plugin.run_plugin_functions(
            pythia.plugin.PluginHook.post_compose_peerless_pixel_skip,
            plugins,
            context=context,
            config=config,
            env=env,
        )
        if not config["silence"]:
            print("X", end="", flush=True)


def execute(config, plugins):
    runs = config.get("runs", [])
    if len(runs) == 0:
        return
    runlist = []
    for run in runs:
        pythia.io.make_run_directory(os.path.join(config["workDir"], run["name"]))

    peers = [pythia.io.peer(r, config.get("sample", None)) for r in runs]
    pool_size = config.get("threads", mp.cpu_count())
    print("RUNNING WITH POOL SIZE: {}".format(pool_size))
    env = pythia.template.init_engine(config["templateDir"])
    pythia.functions.build_ghr_cache(config)

    # Parallelize the context build (build_context), it is CPU intensive because it
    #  runs the functions (functions.py) declared in the config files.
    with concurrent.futures.ProcessPoolExecutor(max_workers=pool_size) as executor:
        tasks = _generate_context_args(runs, peers, config, plugins)
        future_to_context = {executor.submit(build_context, *task): task for task in tasks}

        # process_context is mostly I/O intensive, no reason to parallelize it.
        for future in concurrent.futures.as_completed(future_to_context):
            context_result = future.result()
            if context_result is not None:
                processed_result = process_context(context_result, plugins, config, env)
                if processed_result is not None:
                    runlist.append(processed_result)

    if config["exportRunlist"]:
        with open(os.path.join(config["workDir"], "run_list.txt"), "w") as f:
            [f.write(f"{x}\n") for x in runlist]

    pythia.plugin.run_plugin_functions(
        pythia.plugin.PluginHook.post_compose_peerless_all,
        plugins,
        run_list=runlist,
        config=config,
        env=env,
    )
