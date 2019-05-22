import os
import logging

import fiona
import rasterio

import pythia.functions
import pythia.util
"""longitude/latitude"""


def _get_site_raster_value(dataset, band, site):
    x, y = site
    row, col = dataset.index(x, y)
    return band[row, col]


def peer(run, sample_size=None):
    rasters = pythia.util.get_rasters_dict(run)
    sites = pythia.functions.xy_from_vector(run["sites"])
    data = []
    nodata = []
    layers = list(rasters.keys())
    for raster in rasters.values():
        with rasterio.open(raster) as ds:
            if "int" in ds.dtypes[0]:
                nodata.append(int(ds.nodatavals[0]))
            else:
                nodata.append(ds.nodatavals[0])
            band = ds.read(1)
            data.append(
                [_get_site_raster_value(ds, band, site) for site in sites])
    peerless = list(
        filter(lambda x: x is not None, [
            read_layer_by_cell(i, data, nodata, layers, sites)
            for i in range(len(sites))
        ]))
    return peerless[:sample_size]


def read_layer_by_cell(idx, data, nodata, layers, sites):
    x, y = sites[idx]
    cell = {"lat": y, "lng": x}
    for i, c in enumerate(data):
        if c[idx] == nodata[i]:
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


def extract_vector_coords(f):
    points = []
    with fiona.open(f) as source:
        for feature in source:
            if feature["geometry"]["type"] == "MultiPoint":
                points.append(feature["geometry"]["coordinates"][0])
            if feature["geometry"]["type"] == "Point":
                points.append(feature["geometry"]["coordinates"])
    return list(set(points))


def find_vector_coords(f, x, y, a):
    coords = (x, y)
    with fiona.open(f) as source:
        for feature in source:
            if feature["geometry"]["type"] == "MultiPoint":
                if coords in feature["geometry"]["coordinates"]:
                    return feature["properties"][a]
            if feature["geometry"]["type"] == "Point":
                if coords == feature["geometry"]["coordinates"]:
                    return feature["properties"][a]
