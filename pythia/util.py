import datetime

import pythia.functions


def to_julian_date(d):
    return d.strftime("%y%j")


def to_iso_date(d):
    return d.strftime("%Y-%m-%d")


def from_julian_date(s):
    return datetime.datetime.strptime(s, "%y%j").date()


def from_iso_date(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


def get_rasters_list(iterator):
    return list(
        set(
            [
                pythia.functions.extract_raster(raster)
                for raster in list(filter(lambda x: "raster::" in str(x), iterator))
            ]
        )
    )


def get_rasters_dict(iterator):
    return {
        k: pythia.functions.extract_raster(v) for (k, v) in iterator.items() if "raster::" in str(v)
    }


def translate_coords_news(lat, lng):
    y = ""
    x = ""
    if lat >= 0:
        y = "{:.3f}N".format(lat).replace(".", "_")
    else:
        y = "{:.3f}S".format(abs(lat)).replace(".", "_")
    if lng >= 0:
        x = "{:.3f}E".format(lng).replace(".", "_")
    else:
        x = "{:.3f}W".format(abs(lng)).replace(".", "_")
    return y, x


def translate_news_coords(news):
    if news.endswith("N") or news.endswith("E"):
        return news.replace("_", ".")[:-1]
    else:
        return "-{}".format(news.replace("_", ".")[:-1])

