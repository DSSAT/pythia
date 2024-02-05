import logging
import multiprocessing as mp
import os
import subprocess
from multiprocessing.pool import Pool

import pythia.plugin

async_error = False


def _run_dssat(details, config, plugins):
    logging.debug("Current WD: {}".format(os.getcwd()))
    run_mode = "A"
    if "run_mode" in config["dssat"]:
        run_mode = config["dssat"]["run_mode"].upper()
    command_string = "cd {} && {} {} {}".format(
        details["dir"], config["dssat"]["executable"], run_mode, details["file"]
    )
    # print(".", end="", flush=True)
    dssat = subprocess.Popen(
        command_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = dssat.communicate()
    # print("+", end="", flush=True)

    error_count = len(out.decode().split("\n")) - 1
    hook = pythia.plugin.PluginHook.post_run_pixel_success
    if error_count > 0:
        hook = pythia.plugin.PluginHook.post_run_pixel_failed

    plugin_transform = pythia.plugin.run_plugin_functions(
        hook,
        plugins,
        input={"details": details, "config": config},
        output={"loc": details["dir"], "xfile": details["file"], "out": out, "err": err, "retcode": dssat.returncode}
    ).get("output", {})

    return plugin_transform.get("loc", details["dir"]), plugin_transform.get("xfile", details["file"]), plugin_transform.get("out", out), plugin_transform.get("err", err), plugin_transform.get("retcode", dssat.returncode)


def _generate_run_list(config):
    runlist = []
    for root, _, files in os.walk(config.get("workDir", "."), topdown=False):
        batch_mode = config["dssat"].get("run_mode", "A") in {
            "B",
            "E",
            "F",
            "L",
            "N",
            "Q",
            "S",
            "T",
            "Y",
        }
        target = None
        if batch_mode:
            target = config["dssat"].get("batch_file", None)
        else:
            target = config["dssat"].get("filex", None)
        for name in files:
            if target is not None:
                if name == target:
                    runlist.append({"dir": root, "file": name})
            else:
                if batch_mode:
                    if name.upper().startswith("DSSBATCH"):
                        runlist.append({"dir": root, "file": name})
                else:
                    if name.upper().endswith("X"):
                        runlist.append({"dir": root, "file": name})
    return runlist


def display_async(details):
    loc, xfile, out, error, retcode = details
    error_count = len(out.decode().split("\n")) - 1
    if error_count > 0:
        logging.warning(
            "Check the DSSAT summary file in %s. %d failures occured\n%s",
            loc,
            error_count,
            out.decode()[:-1],
        )
        print("X", end="", flush=True)
        async_error = True
    else:
        print(".", end="", flush=True)


def silent_async(details):
    loc, xfile, out, error, retcode = details
    error_count = len(out.decode().split("\n")) - 1
    if error_count > 0:
        logging.warning(
            "Check the DSSAT summary file in %s. %d failures occured\n%s",
            loc,
            error_count,
            out.decode()[:-1],
        )
        async_error = True


def execute(config, plugins):
    pool_size = config.get("cores", mp.cpu_count())
    run_list = _generate_run_list(config)
    with Pool(processes=pool_size) as pool:
        for details in run_list:  # _generate_run_list(config):
            if config["silence"]:
                pool.apply_async(_run_dssat, (details, config, plugins), callback=silent_async)
            else:
                pool.apply_async(_run_dssat, (details, config, plugins), callback=display_async)
        pool.close()
        pool.join()

    if async_error:
        print(
            "\nOne or more simulations had failures. Please check the pythia log for more details"
        )

    pythia.plugin.run_plugin_functions(
        pythia.plugin.PluginHook.post_run_all,
        plugins,
        config=config,
        run_list=run_list,
    )
