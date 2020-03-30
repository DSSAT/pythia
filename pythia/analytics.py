import csv
import logging
import os
import rasterio
import pythia.analytic_functions
import pythia.io
import pythia.util


def get_run_basedir(config, run):
    return os.path.join(config.get("workDir", "."), run.get("name", ""))


def _generated_run_files(run_path, target_file):
    for root, subdir, files in os.walk(run_path, topdown=False):
        if target_file in files:
            yield root
    pass


def extract_ll(path):
    ll = path.split(os.path.sep)[-2:]
    return tuple([pythia.util.translate_news_coords(l) for l in ll])


# Always by default keep the per_pixel_per_management file, but create a place
# for the single output or analytics, should we have a "final outputs"
# directory.
def filter_columns(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    columns = analytics_config.get("columns", [])
    out_files = []
    out_dir = os.path.join(config.get("workDir", "."), "scratch")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for current_file in outputs:
        col_indexes = []
        out_file = os.path.join(out_dir, "filtered_{}".format(os.path.basename(current_file)))
        with open(current_file) as source, open(out_file, "w") as dest:
            dssat_in = csv.reader(source)
            dssat_out = csv.writer(dest)
            for line in dssat_in:
                if dssat_in.line_num == 1:
                    for x, col in enumerate(line):
                        if col in columns:
                            col_indexes.append(x)
                row = [line[idx] for idx in col_indexes]
                dssat_out.writerow(row)
        out_files.append(out_file)
    return out_files


def calculate_columns(config, outputs):
    analytics_config = config.get("analytics_setup", {})
    calculations = analytics_config.get("calculatedColumns", [])
    funs = pythia.analytic_functions.generate_funs(calculations)
    arg_columns = []
    for fun in funs:
        for a in fun["args"]:
            if a.startswith("$"):
                if a.upper() not in arg_columns:
                    arg_columns.append(a[1::].upper())
    out_files = []
    out_dir = os.path.join(config.get("workDir", "."), "scratch")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for current_file in outputs:
        col_indexes = []
        out_file = os.path.join(out_dir, "calculated_{}".format(os.path.basename(current_file)))
        with open(current_file) as source, open(out_file, "w") as dest:
            dssat_in = csv.reader(source)
            dssat_out = csv.writer(dest)
            num_cols = 0
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
                                    line[col_indexes[arg_columns.index(x[1::].upper())]]
                                    for x in fun["args"]
                                ]
                            )
                        )
                    dssat_out.writerow(line)
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
    out_file = os.path.join(work_dir, per_pixel_file_name)
    harea_info = run.get("harvestArea", None)
    collected_first_line = False
    for current_dir in _generated_run_files(work_dir, "summary.csv"):
        lat, lng = extract_ll(current_dir)
        if collected_first_line:
            mode = "a"
        else:
            mode = "w"
        with open(os.path.join(current_dir, "summary.csv")) as source, open(out_file, mode) as dest:
            # TODO Fix later, this is hacky with little checks in place
            if harea_info:
                harea_tiff = harea_info.split("::")[1]
                with rasterio.open(harea_tiff) as ds:
                    band = ds.read(1)
                    for i, line in enumerate(source):
                        if i == 0:
                            if not collected_first_line:
                                dest.write(
                                    "LATITUDE,LONGITUDE,HARVEST_AREA,RUN_NAME,{}\n".format(
                                        line.strip()
                                    )
                                )
                                collected_first_line = True
                        else:
                            harea = pythia.io.get_site_raster_value(
                                ds, band, (float(lng), float(lat))
                            )
                            if harea is None:
                                harea = 0
                                logging.warning("%s, %s is giving an invalid harea, replacing with 0")
                            harea_s = "{:0.2f}".format(harea)
                            dest.write(
                                "{},{},{},{},{}\n".format(
                                    lat, lng, harea_s, run.get("name", ""), line.strip()
                                )
                            )
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
