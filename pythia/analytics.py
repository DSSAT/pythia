import csv
import logging
import os
import shutil
from typing import Optional
import rasterio
from rasterio.io import DatasetReader
import pythia.analytic_functions
import pythia.io
import pythia.util
from contextlib import _GeneratorContextManager


def get_run_basedir(config, run):
    return os.path.join(config.get("workDir", "."), run.get("name", ""))


def _generated_run_files(run_path, target_file):
    for root, subdir, files in os.walk(run_path, topdown=False):
        if target_file in files:
            yield root
    pass


def extract_ll(path):
    ll = path.split(os.path.sep)[-2:]
    return tuple([pythia.util.translate_news_coords(coords) for coords in ll])


# Always by default keep the per_pixel_per_management file, but create a place
# for the single output or analytics, should we have a "final outputs"
# directory.
def final_outputs(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    out_dir = os.path.join(config.get("workDir", "."))
    file_prefix = "{}_".format(analytics_config.get("per_pixel_prefix", "pp"))
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for current_file in outputs:
        bn = os.path.basename(current_file)
        out_file = os.path.join(out_dir, bn[bn.find(file_prefix) :])
        shutil.copyfile(current_file, out_file)


def filter_columns(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    columns = analytics_config.get("columns", [])
    out_files = []
    out_dir = os.path.join(config.get("workDir", "."), "scratch")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for current_file in outputs:
        col_indexes = []
        out_file = os.path.join(
            out_dir, "filtered_{}".format(os.path.basename(current_file))
        )
        with open(current_file) as source, open(out_file, "w") as dest:
            dssat_in = csv.reader(source)
            dssat_out = csv.writer(dest)
            try:
                for line in dssat_in:
                    if dssat_in.line_num == 1:
                        for x, col in enumerate(line):
                            if col in columns:
                                col_indexes.append(x)
                    row = [line[idx] for idx in col_indexes]
                    dssat_out.writerow(row)
            except csv.Error as e:
                logging.error(
                    "CSV error in %s on line %d: %s", current_file, dssat_in.line_num, e
                )
        out_files.append(out_file)
    return out_files


def calculate_columns(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    calculations = analytics_config.get("calculatedColumns", [])

    out_files = []
    out_dir = os.path.join(config.get("workDir", "."), "scratch")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for current_file in outputs:
        funs = pythia.analytic_functions.generate_funs(calculations)
        arg_columns = []
        for fun in funs:
            for a in fun["args"]:
                if a.upper() not in arg_columns:
                    arg_columns.append(a[1::].upper())

        col_indexes = []
        out_file = os.path.join(
            out_dir, "calculated_{}".format(os.path.basename(current_file))
        )
        with open(current_file) as source, open(out_file, "w") as dest:
            dssat_in = csv.reader(source)
            dssat_out = csv.writer(dest)
            num_cols = 0
            try:
                for line in dssat_in:
                    if dssat_in.line_num != 1:
                        if num_cols == 0:
                            print("we have a problem")
                        else:
                            line = line[0:num_cols]
                    if dssat_in.line_num == 1:
                        num_cols = len(line)
                        col_indexes = [line.index(x) for x in arg_columns]
                        for fun in funs:
                            line.append(fun["key"])
                        dssat_out.writerow(line)
                    else:
                        for fun in funs:
                            line.append(
                                fun["fun"](
                                    [
                                        line[
                                            col_indexes[
                                                arg_columns.index(x[1::].upper())
                                            ]
                                        ]
                                        for x in fun["args"]
                                    ]
                                )
                            )
                        dssat_out.writerow(line)
            except csv.Error as e:
                logging.error(
                    "CSV error in %s on line %d: %s", current_file, dssat_in.line_num, e
                )
            out_files.append(out_file)
    return out_files


def combine_outputs(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    combined_file_name = "{}.csv".format(analytics_config.get("per_pixel_prefix", "pp"))
    out_dir = config.get("workDir", ".")
    collected_first_line = False
    for current_file in outputs:
        if os.path.exists(current_file):
            if collected_first_line:
                mode = "a"
            else:
                mode = "w"
            with open(current_file) as source, open(
                os.path.join(out_dir, combined_file_name), mode
            ) as dest:
                for i, line in enumerate(source):
                    if i == 0:
                        if not collected_first_line:
                            dest.write(line)
                            collected_first_line = True
                    else:
                        dest.write(line)


def collate_outputs(config, run):
    analytics_config = config.get("analytics_setup", {})
    per_pixel_file_name = "{}_{}.csv".format(
        analytics_config.get("per_pixel_prefix", "pp"), run["name"]
    )
    work_dir = get_run_basedir(config, run)
    out_dir = os.path.join(config.get("workDir", "."), "scratch")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_file = os.path.join(out_dir, per_pixel_file_name)
    harea_info = run.get("harvestArea", None)
    pop_info = run.get("population", None)
    season_info = run.get("season", None)
    mgmt_info = run.get("management", None)
    late_season_flag = run.get("lateSeason", False)
    collected_first_line = False
    for current_dir in _generated_run_files(work_dir, "summary.csv"):
        lat, lng = extract_ll(current_dir)
        if collected_first_line:
            mode = "a"
        else:
            mode = "w"
        with open(os.path.join(current_dir, "summary.csv")) as source, open(
            out_file, mode
        ) as dest:
            additional_headers = "LATITUDE,LONGITUDE,RUN_NAME"
            ds_harea: Optional[_GeneratorContextManager[DatasetReader]] = None
            ds_pop: Optional[_GeneratorContextManager[DatasetReader]] = None
            band_harea = None
            band_pop = None
            if season_info:
                additional_headers = f"{additional_headers},SEASON,LATE_SEASON"
            if mgmt_info:
                additional_headers = f"{additional_headers},MGMT"
            if harea_info:
                additional_headers = f"{additional_headers},HARVEST_AREA"
                harea_tiff = harea_info.split("::")[1]
                ds_harea = rasterio.open(harea_tiff)
                band_harea = ds_harea.read(1)
            if pop_info:
                additional_headers = f"{additional_headers},POPULATION"
                pop_tiff = pop_info.split("::")[1]
                ds_pop = rasterio.open(pop_tiff)
                band_pop = ds_pop.read(1)                
            for i, line in enumerate(source):
                if i == 0:
                    if not collected_first_line:
                        dest.write("{},{}\n".format(additional_headers, line.strip()))
                        collected_first_line = True
                else:
                    to_write = (lat, lng, run.get("name", ""))
                    if season_info is not None:
                        to_write = to_write + (season_info,)
                        if late_season_flag:
                            to_write = to_write + (str(True),)
                        else:
                            to_write = to_write + (str(False),)
                    if mgmt_info is not None:
                        to_write = to_write + (mgmt_info,)
                    if ds_harea is not None and not ds_harea.closed:
                        harea = pythia.io.get_site_raster_value(
                            ds_harea, band_harea, (float(lng), float(lat))
                        )
                        if harea is None:
                            harea = 0
                            logging.warning(
                                "%s, %s is giving an invalid harea, replacing with 0"
                            )
                        harea_s = "{:0.2f}".format(harea)
                        to_write = to_write + (harea_s,)
                    if ds_pop is not None and not ds_pop.closed:
                        pop = pythia.io.get_site_raster_value(
                            ds_pop, band_pop, (float(lng), float(lat))
                        )
                        if pop is None:
                            pop = 0
                            logging.warning(
                                "%s, %s is giving an invalid population, replacing with 0"
                            )
                        pop_s = "{:0.2f}".format(pop)
                        to_write = to_write + (pop_s,)
                    to_write = to_write + (line.strip() + "\n",)
                    dest.write(",".join(to_write))
            if ds_harea is not None:
                ds_harea.close()
            if ds_pop is not None:
                ds_pop.close()
    return out_file


def execute(config, plugins):
    runs = config.get("runs", [])
    analytics_config = config.get("analytics_setup", None)
    run_outputs = []
    calculated = None
    filtered = None
    if not analytics_config:
        return
    if len(runs) == 0:
        return
    for run in runs:
        run_outputs.append(collate_outputs(config, run))
    # Apply all the filters first
    if analytics_config.get("calculatedColumns", None):
        calculated = calculate_columns(config, run_outputs)
    if calculated is None:
        calculated = run_outputs
    if analytics_config.get("columns", None):
        filtered = filter_columns(config, calculated)
    if filtered is None:
        filtered = calculated
    if analytics_config.get("singleOutput", False):
        combine_outputs(config, filtered)
    else:
        final_outputs(config, filtered)
