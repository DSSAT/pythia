import logging
import multiprocessing as mp
import os
import subprocess
from multiprocessing.pool import ThreadPool


def _run_dssat(details, config):
    logging.debug("Current WD: {}".format(os.getcwd()))
    command_string = "cd {} && {} A {}".format(details['dir'], config['dssat']['executable'], details['file'])
    print(".", end="")
    dssat = subprocess.Popen(command_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = dssat.communicate()
    print("+", end="")
    return details['dir'], details['file'], out, err, dssat.returncode


def _generate_run_list(config):
    for root, _, files in os.walk(config.get("workDir", "."), topdown=False):
        for name in files:
            if name.upper().endswith("X"):
                yield {"dir": root, "file": name}


def execute(config):
    pool_size = config.get("threads", mp.cpu_count())
    pool = ThreadPool(pool_size)
    results = []

    for details in _generate_run_list(config):
        results.append(pool.apply_async(_run_dssat, (details, config)))
    pool.close()
    pool.join()
    print()
    for result in results:
        print(result.get())
