import os
import queue
import shutil
import threading

import pythia.functions
import pythia.io
import pythia.template
import pythia.util
import pythia.plugins.iita.functions as iita

q = queue.Queue()


def build_context(run, ctx):
    context = run.copy()
    context = {**context, **ctx}
    for k, v in run.items():
        if "::" in str(v) and k != "sites":
            fn = v.split("::")[0]
            if fn != "raster":
                if "." not in fn:
                    res = getattr(pythia.functions, fn)(k, run, context)
                    context = {**context, **res}
                else:
                    # dynamic plugin loader here
                    pass
    return context


def split_levels(levels, max_size):
    for i in range(0, len(levels), max_size):
        yield levels[i:i + max_size]


def iita_build_treatments(context):
    pdates = iita.pdate_factors(context["startYear"], 3, 7, 52)
    hdates = iita.hdate_factors(pdates, 293, 7, 23)
    context["pdates"] = pdates
    context["hdates"] = hdates
    context["factors"] = [{
        "tname":
        "iita_p{}_h{}".format(pdates[pf - 1], hdates[hf - 1]),
        "mp":
        pf,
        "mh":
        hf
    } for pf, hf in iita.generate_factor_list(52, 23)]
    return context


def compose_peerless(ctx):
    run, p, config, env = ctx
    context = build_context(run, p)
    y, x = pythia.util.translate_coords_news(p["lat"], p["lng"])
    context["xcrd"] = p["lat"]
    context["ycrd"] = p["lng"]
    this_output_dir = os.path.join(context["workDir"], y, x)
    pythia.io.make_run_directory(this_output_dir)
    if "weatherDir" in config:
        shutil.copy2(
            os.path.join(config["weatherDir"], context["wthFile"]),
            os.path.join(this_output_dir, "{}.WTH".format(context["wsta"])))
    for soil in context["soilFiles"]:
        shutil.copy2(soil, this_output_dir)
    context = iita_build_treatments(context)
    for out_suffix, split in enumerate(split_levels(context["factors"], 99)):
        context["treatments"] = split
        xfile = pythia.template.render_template(env, run["template"], context)
        with open(
                os.path.join(this_output_dir,
                             "NGSP00{:>02d}.CSX".format(out_suffix)),
                "w") as f:
            f.write(xfile)
    # Write the batch file
    if config["dssat"].get("mode", "A") == "B":
        with open(
                os.path.join(this_output_dir,
                             config["dssat"].get("batchFile", "DSSBATCH.v47")),
                "w") as f:
            f.write("$BATCH(PYTHIA)\n")
            f.write(
                "@FILEX                                                                                        TRTNO     RP     SQ     OP     CO\n"
            )
            for out_suffix, treatments in enumerate(
                    split_levels(context["factors"], 99)):
                for trtno, _ in enumerate(treatments):
                    filename = "NGSP00{:>02d}.CSX".format(out_suffix)
                    f.write(
                        "{:<94s}{:>5d}      1      0      0      0\n".format(
                            filename, trtno + 1))


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
        q.put((run, p, config,
               pythia.template.init_engine(config["templateDir"])))
    for i in range(config["threads"]):
        q.put(None)
    for t in threads:
        t.join()
