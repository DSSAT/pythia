import os


def get_run_basedir(run, config):
    return os.path.join(config.get("workDir", "."), run.get("name", ""))


def _generated_run_files(run_path, target_file):
    for root, subdir, files in os.walk(run_path, topdown=False):
        if target_file in files:
            yield root
    pass


def extract_ll(path):
    return tuple(path.split(os.path.sep)[-2:])


def collateOutputs(run, config):
    collected_first_line = False
    work_dir = get_run_basedir(run, config)
    for current_dir in _generated_run_files(work_dir, "summary.csv"):
        lat, lng = extract_ll(current_dir)
        with open(os.path.join(current_dir, "summary.csv")) as source, open(
            os.path.join(work_dir, "pp.csv"), "a"
        ) as dest:
            for i, line in enumerate(source):
                if i == 0:
                    if not collected_first_line:
                        dest.write("LATITUDE,LONGITUDE,{}\n".format(line.strip()))
                        collected_first_line = True
                else:
                    dest.write("{},{},{}\n".format(lat, lng, line.strip()))


def execute(config):
    runs = config.get("runs", [])
    if len(runs) == 0:
        return
    for run in runs:
        collateOutputs(run, config)
