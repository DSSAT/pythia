import datetime
import logging

import pythia.functions


def to_julian_date(d):
    try:
        return d.strftime("%y%j")
    except ValueError:
        logging.error("Unable to convert %s to a julian date", d)
        return None


def to_iso_date(d):
    try:
        return d.strftime("%Y-%m-%d")
    except ValueError:
        logging.error("Unable to convert %s to an ISO date", d)
        return None


def from_julian_date(s):
    try:
        return datetime.datetime.strptime(s, "%y%j").date()
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(s, "%Y%j").date()
    except ValueError:
        logging.error('"%s" is an invalid julian date format.', s)
        return None


def from_iso_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        logging.error('"%s" is an invalid ISO date format.', s)
        return None


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
        k: pythia.functions.extract_raster(v)
        for (k, v) in iterator.items()
        if "raster::" in str(v)
    }


def translate_coords_news(lat, lng):
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
