import os
import rasterio
import pythia.io
import pythia.util


def get_run_basedir(run, config):
    return os.path.join(config.get("workDir", "."), run.get("name", ""))


def _generated_run_files(run_path, target_file):
    for root, subdir, files in os.walk(run_path, topdown=False):
        if target_file in files:
            yield root
    pass


def extract_ll(path):
    ll = path.split(os.path.sep)[-2:]
    return tuple([pythia.util.translate_news_coords(l) for l in ll])


def collateOutputs(run, config):
    analytics_config = config.get("analytics_setup", {})
    single = analytics_config.get("singleOutput", False)
    if single:
        per_pixel_file_name = "{}.csv".format(analytics_config.get("per_pixel_prefix", "pp"))
    else:
        per_pixel_file_name = "{}_{}.csv".format(
            analytics_config.get("per_pixel_prefix", "pp"), run["name"]
        )
    collected_first_line = analytics_config.get("collectedFirstLine", False)
    work_dir = get_run_basedir(run, config)
    harea_info = run.get("harvestArea", None)
    for current_dir in _generated_run_files(work_dir, "summary.csv"):
        lat, lng = extract_ll(current_dir)
        if single:
            out_dir = config.get("workDir", ".")
        else:
            out_dir = work_dir
        # Remove the original file before appending
        if collected_first_line:
            mode = "a"
        else:
            mode = "w"
        with open(os.path.join(current_dir, "summary.csv")) as source, open(
            os.path.join(out_dir, per_pixel_file_name), mode
        ) as dest:
            # TODO Fix later, this is hacky with little checks in place
            if harea_info:
                harea_tiff = harea_info.split("::")[1]
                with rasterio.open(harea_tiff) as ds:
                    band = ds.read(1)
                    for i, line in enumerate(source):
                        if i == 0:
                            if not collected_first_line:
                                dest.write(
                                    "LATITUDE,LONGITUDE,HARVEST AREA,RUN NAME,{}\n".format(
                                        line.strip()
                                    )
                                )
                                collected_first_line = True
                                if single:
                                    analytics_config["collectedFirstLine"] = True
                        else:
                            harea = pythia.io.get_site_raster_value(
                                ds, band, (float(lng), float(lat))
                            )
                            harea_s = "{:0.2f}".format(harea)
                            dest.write(
                                "{},{},{},{},{}\n".format(
                                    lat, lng, harea_s, run.get("name", ""), line.strip()
                                )
                            )


def execute(config):
    runs = config.get("runs", [])
    if len(runs) == 0:
        return
    for run in runs:
        collateOutputs(run, config)
