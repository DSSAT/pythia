import itertools
import json
import logging
import os

import pythia.functions
import pythia.io


def load_config(config_file, validate=True, merge=True):
    config = {}
    try:
        with open(config_file) as f:
            config = json.load(f)
    except OSError:
        logging.error(
            "Error opening configuration file: {}".format(config_file))
    else:
        if validate:
            if not _validate_config(config):
                return None
        if "runs" in config and merge:
            config["runs"] = _merge_runs(config)
    return config


def _check_raster_profile(raster_file, cached_crs):
    logging.debug("Checking file {}".format(raster_file))
    try:
        current_crs = pythia.io.get_rio_profile(raster_file)['crs'].data
        if cached_crs:
            if cached_crs != current_crs:
                logging.error("CRS mismatch for file {}. {} -> {}. Please reconcile.".format(
                    raster_file, cached_crs['init'], current_crs['init']))
            return cached_crs == current_crs, cached_crs
        else:
            return True, current_crs
    except OSError:
        logging.error("Error opening raster file: {}".format(raster_file))
        return False, cached_crs


def _validate_config(config):
    valid = True
    # Raster check pass 1 - all files are available and of the same projections
    values_iter = itertools.chain.from_iterable(
        [list(config["default_setup"].values())] + [list(r.values()) for r in config["runs"]])
    rasters = list(set([pythia.functions.extract_raster(raster) for raster in
                        list(filter(lambda x: "raster::" in str(x), values_iter))]))
    cached_crs = None
    for r in rasters:
        current_return, cached_crs = _check_raster_profile(r, cached_crs)
        if valid and not current_return:
            valid = False
    # Vector check pass 1 - all files are available and of the same projections
    return valid


def _merge_default(default, run):
    dest = default.copy()
    src = run.copy()
    sections = ["rasters", "vectors"]
    for section in sections:
        if section in dest and section in src:
            dest[section] = {**dest[section], **src[section]}
            del src[section]
    return {**dest, **src}


def _set_run_workdir(run, root, idx):
    run_dir = os.path.join(root, "{}".format(run.get("name", "run_{}".format(idx))))
    return {**run, **{"workDir": run_dir}}


def _merge_runs(config):
    runs = [_merge_default(config["default_setup"], r) for r in config["runs"]]
    runs = [_set_run_workdir(r, config.get("workDir", "."), i) for (i, r) in enumerate(runs)]
    return runs
