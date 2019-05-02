import calendar
import os
import pprint
import re
from numbers import Number

import pandas as pd
import rasterio

# GLOBALS EWWWW
hooks = [
    "during indexing",
    "during collection",
    "before aggregation",
    "after aggregation",
    "before output",
]


def _drop_row_with_val(df, col, val, inplace=False):
    if not inplace:
        if col in list(df):
            return df[df[col] != val]
        else:
            return df
    else:
        if col in list(df):
            targets = df[df[col] == val].index
            df.drop(targets, inplace=True)


def isDateCol(col):
    return col.endswith("DAT") or col.endswith("DATE")


def colToDate(df, col):
    if df[col][0] < 100000:
        fmt = "%y%j"
        df[col] = (df[col].astype(str)).str.pad(5, fillchar="0")
    elif df[col][0] > 999999:
        fmt = "%Y%j"
    else:
        return
    df[col] = pd.to_datetime(df[col].astype(str), format=fmt, errors="coerce")


def autoDate(df):
    cols = df.keys()
    for col in cols:
        if isDateCol(col):
            df[col] = pd.to_datetime(df[col].astype(str),
                                     format="%Y%j",
                                     errors="coerce")
    df.dropna(inplace=True)


def _readFile(df, idx, items, procs=[], default_filters=True, debug=False):
    lim = df.filter(items=items + [idx])
    applyIndexProcesses(lim, procs, debug)
    if isDateCol(idx):
        colToDate(lim, idx)
    lim.dropna(inplace=True)
    lim.set_index(idx, inplace=True)
    # default filters
    if default_filters:
        lim = _drop_row_with_val(lim, "HWAM", -99)
        lim = _drop_row_with_val(lim, "PDAT", -99)
        lim = _drop_row_with_val(lim, "ADAT", -99)
        lim = _drop_row_with_val(lim, "HDAT", -99)
    return lim


def loadSummary(f, idx, items, procs=[], default_filters=True, debug=False):
    df = pd.read_csv(f, index_col=False)
    return _readFile(df, idx, items, procs, default_filters, debug)


def loadDSSATFile(f,
                  idx,
                  items,
                  procs=[],
                  start=3,
                  default_filters=True,
                  debug=False):
    df = pd.read_table(f, delim_whitespace=True, index_col=False, header=start)
    return _readFile(df, idx, items, procs, default_filters, debug)


def applyScale(df, src, dest, scale, rounded=False):
    df[dest] = df[src] * scale
    if rounded:
        df[dest] = round(df[dest]).astype(int)


def applyAverage(df, src, dest, divisor, rounded=False):
    df.loc[(df[src] != 0) & (divisor != 0), dest] = df[src] / divisor
    if rounded:
        df[dest] = round(df[dest]).astype(int)


def applyOffset(df, src, dest, offset):
    df[dest] = df[src] + offset


def applyScaleProcesses(df, procs, debug=False):
    weighted = ["scale", "avg"]
    for proc in procs:
        rounded = False
        factor = None
        if proc["modifier"] == "rounded":
            rounded = True
        if proc["verb"] in weighted:
            if proc["factor"] == "default":
                factor = df["SCALE"]
            elif isinstance(proc["factor"], Number):
                factor = proc["factor"]
            else:
                if proc["factor"] in list(df):
                    factor = df[proc["factor"]]
                else:
                    print("ERROR: {} is not a valid scale factor".format(
                        proc["factor"]))
                    return
            applyScale(df, proc["src"], proc["dest"], factor, rounded)


def applyAverageProcesses(df, procs, debug=False):
    averages = ["avg", "uavg"]
    for proc in procs:
        if debug:
            print(proc)
        rounded = False
        divisor = None
        if proc["modifier"] == "rounded":
            rounded = True
        if proc["verb"] in averages:
            if proc["factor"] == "default":
                if proc["verb"] == "avg":
                    divisor = df["CUSUM"]
                elif proc["verb"] == "uavg":
                    divisor = df["ZSIZE"]
            elif isinstance(proc["factor"], Number):
                divisor = proc["factor"]
            else:
                if proc["factor"] in list(df):
                    divisor = df[proc["factor"]]
                else:
                    print("ERROR: {} is not a valid divisor".format(
                        proc["factor"]))
                    return
            applyAverage(df, proc["src"], proc["dest"], divisor, rounded)


def applyMiscProcesses(df, procs, debug=False):
    if debug:
        print("Running rename processes")
    for proc in procs:
        if proc["verb"] == "rename":
            if debug:
                print("Renaming {} to {}".format(proc["src"], proc["dest"]))
            df.rename({proc["src"]: proc["dest"]}, axis=1, inplace=True)
        if proc["verb"] == "round":
            df[proc["dest"]] = round(df[proc["src"]]).astype(int)
        if proc["verb"] == "drop0":
            _drop_row_with_val(df, proc["src"], 0, True)


def applyIndexProcesses(df, procs, debug=False):
    valid_procs = ["offset", "scale"]
    for proc in procs:
        src = proc["src"].strip("!")
        dest = proc["dest"].strip("!")
        rounded = False
        if proc["modifier"] == "rounded":
            rounded = True
        if proc["verb"] == "offset":
            offset = None
            if isinstance(proc["factor"], Number):
                offset = proc["factor"]
            else:
                if proc["factor"] in list(df):
                    offset = df[proc["factor"]]
                else:
                    print("ERROR: {} is not a valid offset".format(
                        proc["factor"]))
                    continue
            applyOffset(df, src, dest, offset)
        if proc["verb"] == "scale":
            factor = None
            if isinstance(proc["factor"], Number):
                factor = proc["factor"]
            else:
                if proc["factor"] in list(df):
                    factor = df[proc["factor"]]
                else:
                    print("ERROR: {} is not a valid scale factor".format(
                        proc["factor"]))
                    continue
            applyScale(df, src, dest, factor, rounded)


def accumulate(df, acc=None):
    if acc is None:
        acc = df.copy()
    else:
        acc = pd.concat([acc, df])
    return acc


def init(scale_tiff, workDir="."):
    directories = next(os.walk(workDir))[1]
    scale = loadRaster(scale_tiff)
    scale_factors = [
        scale[c[0]][c[1]]
        for c in [tuple(map(int, d.split("_"))) for d in directories]
    ]
    cumulative = sum(scale_factors)
    return (directories, scale_factors, cumulative)


def collect(
        directories,
        scale_factors,
        cumulative,
        index,
        cols,
        procs=[],
        workDir=".",
        target="summary.csv",
        debug=False,
):
    acc = None
    for idx, d in enumerate(directories):
        summary = loadSummary(
            os.path.join(workDir, d, target),
            index,
            cols,
            procs["during indexing"],
            debug=debug,
        )
        summary["SCALE"] = scale_factors[idx]
        summary["CUSUM"] = cumulative
        applyScaleProcesses(summary, procs["during collection"])
        applyAverageProcesses(summary, procs["during collection"])
        acc = accumulate(summary, acc)
    return acc


def aggregate(df, procs, timestep="Y", index_name=None, debug=False):
    applyScaleProcesses(df, procs["before aggregation"], debug)
    applyAverageProcesses(df, procs["before aggregation"], debug)
    cusum = df.iloc[0].at["CUSUM"]
    if debug:
        print(cusum)
    # CUSUM shouldn't sum
    z = df.resample(timestep, kind="period")
    res = z.sum()
    res["ZSIZE"] = z.size()
    res["CUSUM"] = cusum
    res.dropna(inplace=True)
    res = _drop_row_with_val(res, "ZSIZE", 0)
    res = _drop_row_with_val(res, "SCALE", 0)
    applyScaleProcesses(res, procs["after aggregation"], debug)
    applyAverageProcesses(res, procs["after aggregation"], debug)
    res.index.name = index_name
    return res


def output(df, procs, outputs=None, outfile=None, workDir=".", debug=False):
    applyScaleProcesses(df, procs["before output"], debug)
    applyAverageProcesses(df, procs["before output"], debug)
    applyMiscProcesses(df, procs["before output"], debug)
    if outputs is None:
        res = df
    else:
        res = df.reindex(columns=outputs)
    if outfile is None:
        return res
    else:
        res.to_csv(os.path.join(workDir, outfile))
        return res


def runProfiles(
        profiles,
        storeOutputs=False,
        breakOnFailure=True,
        printOutputs=False,
        miniProgress=False,
        debug=False,
):
    outs = []
    for run, profile in enumerate(profiles):
        if miniProgress:
            progress = "{}/{}".format(run + 1, len(profiles))
            if "name" not in profile or not profile["name"]:
                name = ""
            else:
                name = profile["name"]
            print("Starting run {}: {}".format(progress, name))
        out = runProfile(profile, debug)
        if out is None:
            print("FAILED!!")
            pprint.pprint(profile)
            if breakOnFailure:
                return False
            else:
                continue
        else:
            if storeOutputs:
                outs.append(out)
            if miniProgress:
                print("Done!")
            if printOutputs:
                print(out)

    return True


def runProfile(profile, debug=False):
    _profile = validateProfile(profile, debug)
    if debug:
        pprint.pprint(_profile)
    if not _profile:
        print("There was a problem running this profile: {}".format(profile))
        return None
    if _profile["timeseries"]:
        index_name = next(iter(_profile["timeseries"]))
        index = _profile["timeseries"][index_name]
    else:
        # for now
        index = None
        index_name = ""

    # Probably bad code￿￿￿
    sources = [
        p["src"] for p in _profile["procs"]["during indexing"]
        if not re.match("^!.+!$", p["src"])
    ]
    sources += [p["src"] for p in _profile["procs"]["during collection"]]
    dests = [
        p["dest"] for p in _profile["procs"]["during indexing"]
        if not re.match("^!.+!$", p["dest"])
    ]
    dests += [p["dest"] for p in _profile["procs"]["during collection"]]
    to_collect = list(set(sources).difference(dests))
    if debug:
        pprint.pprint(to_collect)
    if len(to_collect) == 0:
        print("No variables selected from outputs")
        return False

    (d, sf, c) = init(_profile["scale_tiff"], _profile["workDir"])
    collected = collect(
        d,
        sf,
        c,
        index,
        to_collect,
        _profile["procs"],
        _profile["workDir"],
        _profile["target"],
        debug,
    )
    if debug:
        print("== COLLECTED ==")
        pprint.pprint(collected.sort_index())
    agg = aggregate(collected, _profile["procs"], _profile["timestep"],
                    index_name, debug)
    if debug:
        print("== AGGREGATED ==")
        pprint.pprint(agg)
    out = output(
        agg,
        _profile["procs"],
        _profile["output"],
        _profile["outfile"],
        _profile["workDir"],
        debug,
    )
    if debug:
        print("== OUTPUT ==")
        pprint.pprint(out)
    return out


def validateProfile(profile, debug=False):
    default_profile = {
        "workdDir": ".",
        "timestep": "Y",
        "timeseries": None,
        "output": None,
        "outfile": None,
        "target": "summary.csv",
        "name": "",
        "mode": "default",
    }

    default_weather_profile = {
        "start_date": None,
        "end_date": None,
        "forecast_start_year": None,
        "forecast_last_read_date": None,
    }

    _profile = {**default_profile, **profile}
    # check for missing required data
    msg = []
    if not "processing" in _profile:
        msg.append("processing must be defined in the profile")
    if not "scale_tiff" in _profile:
        msg.append("scale_tiff must be defined in the profile")
    # if _profile["mode"] != "default":

    #     if not "start_year" not in _profile and "start_date" not in _profile:
    #         msg.append("start_year or start_date must be defined in the profile")
    #     if not "run_years" not in _profile and "end_date" not in _profile:
    #         msg.append("run_years or end_date must be defined in the profile")
    if _profile["mode"] == "timeseries forecasting":
        if not "forecast_start_year" in _profile:
            msg.append("forecast_start_year must be defined in the profile")
        if not "forecast_last_real_date" in _profile:
            msg.append(
                "forecast_last_real_date must be defined in the profile")
    if len(msg) != 0:
        print("\n".join(["ERROR:"] + msg))
        return None

    if _profile != "default":
        if "start_date" not in _profile and "start_year" in _profile:
            _profile["start_date"] = "{}-01-01".format(_profile["start_year"])
        if "end_date" not in _profile and "run_years" in _profile:
            _profile["end_date"] = "{}-12-31".format(_profile["start_year"] +
                                                     (_profile["run_years"] -
                                                      1))
        if "forecast_start_year" in _profile:
            if not "start_date" in _profile:
                _profile["start_date"] = "{}-01-01".format(
                    _profile["forecast_last_real_date"][:4])
            if "end_date" in _profile:
                _profile["forecast_end_year"] = int(
                    _profile["end_date"].split("-")[0])
            else:
                _profile["forecast_end_year"] = int(
                    int(_profile["forecast_last_real_date"].split("-")[0]))
        # A series of checks needs to be here sd < cd < ed
        _profile = {**default_weather_profile, **_profile}
    (_profile["procs"],
     _profile["visibility"]) = parseProcesses(_profile["processing"], debug)
    if _profile["procs"]:
        return _profile
    else:
        return None


def convertNum(n):
    if re.match("^\-?\d+?\.\d+?$", n) is not None:
        return float(n)
    elif re.match("^\-?\d+$", n) is not None:
        return int(n)
    else:
        return None


def parseProcess(process, debug=False):
    if debug:
        print("[parseProcess] {}".format(process))
    allowed_cmds = [
        "avg",
        "drop0",
        "offset",
        "rename",
        "round",
        "scale",
        "uavg",
        "val",
        "save",
    ]
    allowed_date_cmds = ["avg", "rename", "uavg", "val"]
    short_cmds = ["drop0", "rename", "round", "save"]
    allowed_modifiers = ["rounded"]
    allowed_hooks = [
        "during indexing",
        "during index",
        "during collection",
        "before aggregation",
        "before agg",
        "before resampling",
        "before resample",
        "after aggregation",
        "after agg",
        "after resampling",
        "after resample",
        "before output",
    ]
    p = process.strip().split()
    if len(p) < 5 or len(p) > 6:
        if p[0] not in short_cmds:
            print("Not enough arguments: Dropping process: {}".format(process))
            return None
    verb = p[0]
    hook = ""
    factor = ""
    modifier = ""
    if len(p) >= 3:
        hook = " ".join(p[1:3])
    if len(p) >= 5:
        factor = " ".join(p[3:5])
    if len(p) == 6:
        modifier = p[5]
    if verb not in allowed_cmds:
        print("Invalid verb {}: Dropping process: {}".format(verb, process))
        return None
    if verb in short_cmds:
        hook = "before output"
    if hook not in allowed_hooks:
        print("Invalid hook {}: Dropping process: {}".format(hook, process))
        return None
    if verb not in short_cmds and not factor.startswith("by"):
        print("Invalid factor {}: Dropping process: {}".format(
            factor, process))
        return None
    if verb not in short_cmds:
        factor = factor.split()[1]
        f_num = convertNum(factor)
        if f_num:
            # Need to work on guarding against not default or column names
            factor = f_num
    if modifier and modifier not in allowed_modifiers:
        print("Invalid modifier {}: Dropping process: {}".format(
            modifier, process))
        return None
    # normalize hooks
    if hook == "before agg" or hook == "before resampling" or hook == "before resample":
        hook = "before aggregation"
    if hook == "after agg" or hook == "after resampling" or hook == "after resample":
        hook = "after aggregation"
    if hook == "during index":
        hook = "during indexing"
    return {"verb": verb, "hook": hook, "factor": factor, "modifier": modifier}


def addToHookVisiblity(hv, h, d):
    copy = False
    if re.match("^!.+!$", d):
        return
    for hook, visible in hv.items():
        if hook == h:
            copy = True
        if copy:
            if d not in visible:
                visible.append(d)


def parseProcesses(processes, debug=False):
    procs = {h: [] for h in hooks}
    hook_visible = {h: [] for h in hooks}
    addToHookVisiblity(hook_visible, "during collection", "SCALE")
    addToHookVisiblity(hook_visible, "after aggregation", "COUNT")
    valid_process = False
    for process_dict in processes:
        dest = next(iter(process_dict))
        proc = {"dest": dest}
        process = process_dict[dest]
        if ":" not in process:
            print(
                "Invalid process string: Dropping process {}".format(process))
            continue
        (src, s) = process.split(":", maxsplit=1)
        proc["src"] = src.strip()
        p = parseProcess(s, debug)
        if p:
            valid_process = True
            proc = {**proc, **p}
            procs[p["hook"]].append(proc)
            addToHookVisiblity(hook_visible, p["hook"], src)
            addToHookVisiblity(hook_visible, p["hook"], dest)
    if valid_process:
        return procs, hook_visible
    else:
        return None


def execute(run, peerless, config):
    data = {**run, **peerless}
    pprint.pprint(data)
