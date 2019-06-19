from datetime import date, timedelta
import os
import logging
import queue
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
                    if res is None:
                        logging.error(
                            "Failed function %s, "
                            "attempting to return None", fn)
                        return None
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

    # date offset hack
    min_date = date(1984, 1, 1)
    sdates = [
        pythia.util.to_julian_date(
            pythia.functions._bounded_offset(pythia.util.from_julian_date(d),
                                             timedelta(days=-30),
                                             min_val=min_date)) for d in pdates
    ]
    context["pdates"] = pdates
    context["hdates"] = hdates
    context["sdates"] = sdates
    context["factors"] = [{
        "tname":
        "iita_p{}_h{}".format(pdates[pf - 1], hdates[hf - 1]),
        "mp":
        pf,
        "mh":
        hf,
    } for pf, hf in iita.generate_factor_list(52, 23)]
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
    context = build_context(run, p)
    if context is not None:
        y, x = pythia.util.translate_coords_news(p["lat"], p["lng"])
        context["xcrd"] = p["lat"]
        context["ycrd"] = p["lng"]
        context = iita_build_treatments(context)

        dssat_mode = config["dssat"].get("mode", "A")
        this_output_dir = os.path.join(context["workDir"], y, x)
        pythia.io.make_run_directory(this_output_dir)
        if dssat_mode == "B":
            batch_chunks = config["dssat"].get("batch_chunks", 99)
            symlink_wth_soil(this_output_dir, config, context)
        for out_suffix, split in enumerate(split_levels(
                context["factors"], batch_chunks)):
            if dssat_mode == "A":
                this_output_dir = os.path.join(this_output_dir,
                                               str(out_suffix))
                pythia.io.make_run_directory(this_output_dir)
                symlink_wth_soil(this_output_dir, config, context)
            context["treatments"] = split
            xfile = pythia.template.render_template(env, run["template"],
                                                    context)
            if dssat_mode == "B":
                xfile_name = "NGSP00{:>02d}.CSX".format(out_suffix)
            else:
                xfile_name = "NGSP0000.CSX"
            with open(os.path.join(this_output_dir, xfile_name), "w") as f:
                f.write(xfile)
        # Write the batch file
        if dssat_mode == "B":
            with open(
                    os.path.join(
                        this_output_dir,
                        config["dssat"].get("batchFile", "DSSBATCH.v47")),
                    "w",
            ) as f:
                f.write("$BATCH(PYTHIA)\n")
                f.write(
                    "@FILEX                                                  "
                    "                                      TRTNO     RP     "
                    "SQ     OP     CO\n")
                for out_suffix, treatments in enumerate(
                        split_levels(context["factors"], batch_chunks)):
                    for trtno in range(len(treatments)):
                        filename = "NGSP00{:>02d}.CSX".format(out_suffix)
                        f.write("{:<94s}{:>5d}      1      0      0      0\n".
                                format(filename, trtno + 1))


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
