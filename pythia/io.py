import os
import sys

import fiona
import numpy.ma as ma
import rasterio
from pythia.gis import euclidean_distance

import pythia.functions
import pythia.util


"""rasterio reads x/y which is longitude/latitude"""


def get_site_raster_value(dataset, band, site):
    lng, lat = site
    row, col = dataset.index(lng, lat)
    data = []
    try:
        data = band[row, col]
        if data is ma.masked:
            data = None
    except IndexError:
        data = None
    return data


def peer(run, sample_size=None):
    rasters = pythia.util.get_rasters_dict(run)
    sites = []
    if isinstance(run["sites"], list):
        sites = pythia.functions.xy_from_list(run["sites"])
    else:
        sites = pythia.functions.xy_from_vector(run["sites"])
    data = []
    layers = list(rasters.keys())
    for raster in rasters.values():
        with rasterio.open(raster) as ds:
            band = ds.read(1, masked=True)
            data.append([get_site_raster_value(ds, band, site) for site in sites])
    peerless = list(
        filter(
            lambda x: x is not None,
            [read_layer_by_cell(i, data, layers, sites) for i in range(len(sites))],
        )
    )
    return peerless[:sample_size]


def read_layer_by_cell(idx, data, layers, sites):
    if data is None:
        return None
    lng, lat = sites[idx]
    cell = {"lat": lat, "lng": lng, "xcrd": lng, "ycrd": lat}
    for i, c in enumerate(data):
        if c[idx] is None:
            return None
        if layers[i] == "harvestArea" and c[idx] == 0:
            return None
        else:
            cell[layers[i]] = c[idx]
    return cell


def make_run_directory(rd):
    os.makedirs(rd, exist_ok=True)


def get_rio_profile(f):
    with rasterio.open(f) as source:
        profile = source.profile
    return profile


def get_shp_profile(f):
    pass


def extract_vector_coords(f):
    points = []
    with fiona.open(f, "r") as source:
        for feature in source:
            if feature["geometry"]["type"] == "MultiPoint":
                points.append(feature["geometry"]["coordinates"][0])
            if feature["geometry"]["type"] == "Point":
                points.append(feature["geometry"]["coordinates"])
    return points


def find_vector_coords(f, lng, lat, a):
    coords = (lng, lat)
    with fiona.open(f, "r") as source:
        for feature in source:
            if feature["geometry"]["type"] == "MultiPoint":
                if coords in feature["geometry"]["coordinates"]:
                    return feature["properties"][a]
            if feature["geometry"]["type"] == "Point":
                if coords == feature["geometry"]["coordinates"]:
                    return feature["properties"][a]


def find_closest_vector_coords(f, lng, lat, a):
    closest_id = None
    with fiona.open(f, "r") as source:
        closest_distance = sys.float_info.max
        for feature in source:
            if feature["geometry"]["type"] == "MultiPoint":
                for coords in feature["geometry"]["coordinates"]:
                    res = euclidean_distance(coords[1], coords[0], lat, lng)
                    if res < closest_distance:
                        closest_distance = res
                        closest_id = feature["properties"][a]
                    if res == 0:
                        break
            if feature["geometry"]["type"] == "Point":
                coords = feature["geometry"]["coordinates"]
                res = euclidean_distance(coords[1], coords[0], lat, lng)
                if res < closest_distance:
                    closest_distance = res
                    closest_id = feature["properties"][a]
                if res == 0:
                    return feature["properties"][a]
    return closest_id
