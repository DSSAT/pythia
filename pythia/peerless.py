import itertools
import logging
import multiprocessing as mp
import os

import pythia.functions
import pythia.io
import pythia.template
import pythia.util


def build_context(args):
    print("+", end="", flush=True)
    run, ctx, config = args
    context = run.copy()
    context = {**context, **ctx}
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
    return context


def _generate_context_args(runs, peers, config):
    for idx, run in enumerate(runs):
        for peer in peers[idx]:
            yield run, peer, config


def symlink_wth_soil(output_dir, config, context):
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
    print(".", end="", flush=True)
    y, x = pythia.util.translate_coords_news(context["lat"], context["lng"])
    this_output_dir = os.path.join(context["workDir"], y, x)
    pythia.io.make_run_directory(this_output_dir)
    symlink_wth_soil(this_output_dir, config, context)
    xfile = pythia.template.render_template(env, context["template"], context)
    with open(os.path.join(this_output_dir, context["template"]), "w") as f:
        f.write(xfile)


def execute(config):
    runs = config.get("runs", [])
    if len(runs) == 0:
        return
    peers = [pythia.io.peer(r, config.get("sample", None)) for r in runs]
    pool_size = config.get("threads", mp.cpu_count() * 10)
    print("RUNNING WITH POOL SIZE: {}".format(pool_size))
    env = pythia.template.init_engine(config["templateDir"])
    with mp.pool.ThreadPool(pool_size) as pool:
        for context in pool.imap_unordered(
            build_context, _generate_context_args(runs, peers, config), 250
        ):
            if context is not None:
                compose_peerless(context, config, env)
            else:
                print("X", end="", flush=True)
    print()
