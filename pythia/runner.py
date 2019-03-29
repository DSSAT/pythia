import os
import shutil
import threading
import queue
import pythia.util

q = queue.Queue()


def build_context(run, ctx):
    for k, v in run.items():
        if "::" in str(v) and k != "sites":
            fn = v.split("::")[0]
            if fn != "raster":
                res = getattr(pythia.functions, fn)(k, run, ctx)
                ctx = {**ctx, **res}
    return ctx


def compose_peerless(ctx):
    run, p, config, env = ctx
    context = build_context(run, p)
    y, x = pythia.util.translate_coords_news(p["lat"], p["lng"])
    ctxOutputDir = os.path.join(config["workDir"], y, x)
    pythia.io.make_run_directory(ctxOutputDir)
    if "weatherDir" in config:
        shutil.copy2(os.path.join(config["weatherDir"], context["wthFile"]), os.path.join(
            ctxOutputDir, "{}.WTH".format(context["wsta"])))
    for soil in run["soils"]:
        shutil.copy2(soil, ctxOutputDir)
    xfile = pythia.template.render_template(env, run["template"], context)
    with open(os.path.join(ctxOutputDir, run["template"]), "w") as f:
        f.write(xfile)


def oracle():
    while True:
        item = q.get()
        if item is None:
            break
        compose_peerless(item)
        q.task_done()


def run_peerless(run, peerless, config):
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
