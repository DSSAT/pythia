import logging
import os
from pythia.plugin import PluginHook, register_plugin_function
import pythia.util

# Configuration
# "plugins":[
#   { "plugin": "weather_forecast_simple",
#     "params": {
#       "start_date": "2018-01-01",
#       "end_date": "2018-04-31",
#       "wsta": "SSDF"
#     },
#    "order": 1
#   }
# ]


def initialize(config, plugins, full_config):
    logging.info("[SIMPLE WEATHER FORECAST PLUGIN] Initializing plugin")
    config["weatherDir"] = full_config["weatherDir"]
    config["start_date"] = pythia.util.to_julian_date(
        pythia.util.from_iso_date(config["start_date"])
    )
    config["end_date"] = pythia.util.to_julian_date(pythia.util.from_iso_date(config["end_date"]))
    config["start_on"] = config["start_date"][2:5]
    config["end_on"] = config["end_date"][2:5]
    return register_plugin_function(
        PluginHook.post_build_context, construct_pixel_forecast, config, plugins
    )


def construct_pixel_forecast(config={}, context={}):
    """NOTE: This function is NOT side-effect free. It does I/O to create a new file in the
       context["contextWorkDir"]. But this side-effect also is intentional to interrupt the
       creation of the symlinks further along the process."""

    """TODO: Fix the wrap around case for leap years"""

    logging.debug("[SIMPLE WEATHER FORECAST PLUGIN] Running construct_pixel_forecast()")
    source_weather = os.path.join(config["weatherDir"], context["wthFile"])
    dest_weather = os.path.join(context["contextWorkDir"], "{}.WTH".format(config["wsta"]))
    target_lines = []
    with open(source_weather) as source:
        scraping_lines = False
        for line in source:
            if line.startswith(config["start_date"]):
                scraping_lines = True
            if scraping_lines:
                target_lines.append(line[2:].strip())
            if line.startswith(config["end_date"]):
                scraping_lines = False
                break

    with open(source_weather) as source, open(dest_weather, "w") as dest:
        in_target = False
        wrote_target = False
        for line in source:
            yr = line[:2]
            doy = line[2:5]
            if doy == config["start_on"]:
                in_target = True
            if in_target and not wrote_target:
                for target_line in target_lines:
                    dest.write("{}{}\n".format(yr, target_line))
                wrote_target = True
            if not in_target:
                dest.write("{}\n".format(line.strip()))
            if in_target and doy == config["end_on"]:
                in_target = False
                wrote_target = False
    _new_context = {}
    _new_context["wsta"] = config["wsta"]
    return _new_context
