import os
import queue
import shutil
import threading

import pythia.functions
import pythia.io
import pythia.template
import pythia.util

q = queue.Queue()


def build_context(run, ctx, config):
    context = run.copy()
    context = {**context, **ctx}
    for k, v in run.items():
        if "::" in str(v) and k != "sites":
            fn = v.split("::")[0]
            if fn != "raster":
                res = getattr(pythia.functions, fn)(k, run, context, config)
                context = {**context, **res}
    return context


def symlink_wth_soil(output_dir, config, context):
    if "weatherDir" in config:
        weather_file = os.path.join(output_dir,
                                    "{}.WTH".format(context["wsta"]))
        if not os.path.exists(weather_file):
            os.symlink(
                os.path.abspath(
                    os.path.join(config["weatherDir"], context["wthFile"])),
                os.path.join(weather_file),
            )
    for soil in context["soilFiles"]:
        soil_file = os.path.join(output_dir, os.path.basename(soil))
        if not os.path.exists(soil_file):
            os.symlink(os.path.abspath(soil),
                       os.path.join(output_dir, os.path.basename(soil)))


def compose_peerless(ctx):
    run, p, config, env = ctx
    context = build_context(run, p, config)
    y, x = pythia.util.translate_coords_news(p["lat"], p["lng"])
    this_output_dir = os.path.join(context["workDir"], y, x)
    pythia.io.make_run_directory(this_output_dir)
    symlink_wth_soil(this_output_dir, config, context)
    xfile = pythia.template.render_template(env, run["template"], context)
    with open(os.path.join(this_output_dir, run["template"]), "w") as f:
        f.write(xfile)


def oracle():
    while True:
        item = q.get()
        if item is None:
            break
        compose_peerless(item)
        q.task_done()


def execute(run, peerless, config):
    threads = []
    for i in range(config["threads"]):
        t = threading.Thread(target=oracle)
        t.start()
        threads.append(t)
    for p in peerless:
        q.put((run, p, config, pythia.template.init_engine(
            config["templateDir"])))
    for i in range(config["threads"]):
        q.put(None)
    for t in threads:
        t.join()
