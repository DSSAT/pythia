import logging
import multiprocessing as mp
import os
import subprocess
from multiprocessing.pool import Pool


def _run_dssat(details, config):
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
    return details["dir"], details["file"], out, err, dssat.returncode


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
    else:
        print(".", end="", flush=True)


def execute(config, plugins):
    pool_size = config.get("cores", mp.cpu_count())
    run_list = _generate_run_list(config)
    with Pool(processes=pool_size) as pool:
        for details in run_list:  # _generate_run_list(config):
            pool.apply_async(_run_dssat, (details, config), callback=display_async)
        pool.close()
        pool.join()
    print("\nIf you see an X above, please check the pythia.log for more details")
