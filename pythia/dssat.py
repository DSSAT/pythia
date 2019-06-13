import logging
import multiprocessing as mp
import os
import subprocess
from multiprocessing.pool import Pool


def _run_dssat(details, config):
    logging.debug("Current WD: {}".format(os.getcwd()))
    command_string = "cd {} && {} A {}".format(
        details["dir"], config["dssat"]["executable"], details["file"]
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
        for name in files:
            if name.upper().endswith("X"):
                runlist.append({"dir": root, "file": name})
    return runlist


def display_async(details):
    print(details)


def execute(config):
    pool_size = config.get("cores", mp.cpu_count())
    results = []
    l = _generate_run_list(config)
    with Pool(processes=pool_size) as pool:
        for details in l:  # _generate_run_list(config):
            r = pool.apply_async(_run_dssat, (details, config), callback=display_async)
        pool.close()
        pool.join()
