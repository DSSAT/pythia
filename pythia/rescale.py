__license__ = "BSD-3-Clause"

import json
import logging
import os

import fiona
import rasterio
from rasterio.warp import reproject

import pythia.functions


def get_raster_resolution(file_path):
    with rasterio.open(file_path, 'r') as raster:
        return [round(raster.profile['transform'][0], 6), round(raster.profile['transform'][4], 6)]


def get_vector_resolution(file_path):
    with fiona.open(file_path, 'r') as src:
        min_x_dist, min_y_dist = None, None
        if src[0]['geometry']['type'] == 'Polygon':
            x_min, y_min, x_max, y_min = None, None
            for coords in src[0]['geometry']['coordinates']:
                if x_min is None or coords[0] < x_min:
                    x_min = coords[0]
                if x_max is None or x_max < coords[0]:
                    x_max = coords[0]
                if y_min is None or coords[1] < y_min:
                    y_min = coords[1]
                if y_max is None or y_max < coords[1]:
                    y_max = coords[1]
            x_dist = x_max - x_min
            y_dist = y_max - y_min
            return (x_dist, y_dist)
        else:
            for i in range(len(src) - 1):
                x_dist = abs(src[i]['geometry']['coordinates'][0] - src[i + 1]['geometry']['coordinates'][0])
                y_dist = abs(src[i]['geometry']['coordinates'][1] - src[i + 1]['geometry']['coordinates'][1])
                if 0 < x_dist:
                    if min_x_dist is None or x_dist < min_x_dist:
                        min_x_dist = x_dist
                if 0 < y_dist:
                    if min_y_dist is None or y_dist < min_y_dist:
                        min_y_dist = y_dist
            return [round(min_x_dist, 6), round(min_y_dist, 6)]


def change_raster_resolution(file_path, scale_factor, config, dst_path=None):
    file_name = file_path.split('/')[-1].split('.')[0]

    with rasterio.open(file_path, 'r') as src:
        profile = src.profile

        # Use resampling method defined
        resampling_mode = rasterio.enums.Resampling.nearest

        # Define the new resolution
        new_width = int(profile['width'] * scale_factor)
        new_height = int(profile['height'] * scale_factor)

        # Compute the new transform
        transform = profile['transform'] * profile['transform'].scale(
            profile['width'] / new_width,
            profile['height'] / new_height
        )

        # Update the profile for the new raster
        profile.update({
            'height': new_height,
            'width': new_width,
            'transform': transform
        })

        rescale_dir = config['workDir']
        rescale_dir += "/rescale/" if rescale_dir[-1] != '/' else 'rescale/'
        new_filename = file_name + '_rescaled.tif'
        dst_path = rescale_dir + new_filename if dst_path is None else dst_path

        try:
            os.makedirs(rescale_dir, exist_ok=True)
        except OSError as e:
            logging.error(
                "OSError encountered when attempting to create rescale_dir: " + str(e)
            )
            raise e

        with rasterio.open(dst_path, 'w', **profile) as dst:
            for i in range(1, profile['count'] + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=profile['transform'],
                    src_crs=profile['crs'],
                    dst_transform=transform,
                    dst_crs=profile['crs'],
                    resampling=resampling_mode
                )
    return dst_path


def change_vector_resolution(file_path, scale_factor, config, current_res, dst_path=None):
    """
    Rescale the original file by a defined factor.

    :param upscaling_factor: Must be an integer >= 2.
    2 will result in a 2x2 grid of points created where 1 used to be.

    :return:
    """
    file_name = file_path.split('/')[-1].split('.')[0]

    with fiona.open(file_path, 'r') as src:
        components = [abs(component_res) for component_res in current_res]
        d = max(components)

        new_features = []
        id = 0

        rescale_dir = config['workDir']
        rescale_dir += "/rescale/" if rescale_dir[-1] != '/' else 'rescale/'
        new_filename = file_name + '_rescaled.shp'
        dst_path = rescale_dir + new_filename if dst_path is None else dst_path

        try:
            os.makedirs(rescale_dir, exist_ok=True)
        except OSError as e:
            logging.error(
                "OSError encountered when attempting to create rescale_dir: " + str(e)
            )
            raise e

        with fiona.open(dst_path, 'w',
                        crs=src.crs,
                        driver="ESRI Shapefile",
                        schema=src.schema) as dst:
            for feature in src:
                if feature['geometry']['type'] == 'Point':
                    x_old = feature['geometry']['coordinates'][0]
                    y_old = feature['geometry']['coordinates'][1]

                    old_properties = feature['properties']

                    for i in range(scale_factor):
                        for j in range(scale_factor):
                            x_new = x_old + d * (2 * i - scale_factor + 1) / (2 * scale_factor)
                            y_new = y_old + d * (2 * j - scale_factor + 1) / (2 * scale_factor)

                            # Because of impending deprecation in fiona, new Geometry, Properties
                            # and Feature objs must be made
                            new_geometry = fiona.Geometry((x_new, y_new), type='Point')

                            # TODO: find out how slimmed down we can get the properties (what is necessary)
                            properties = {
                                'ID': old_properties['ID'],
                                'Latitude': old_properties['Latitude'],
                                'Longitude': old_properties['Longitude'],
                                'nasapid': old_properties['nasapid'],
                                'LatNP': old_properties['LatNP'],
                                'LonNP': old_properties['LonNP'],
                            }

                            new_properties = fiona.Properties.from_dict(properties)

                            dst.write(fiona.Feature(new_geometry, str(id), new_properties))
                            id += 1
    return dst_path


def get_desired_res(run, desired='highest'):
    desired = desired.lower()
    if desired not in ['highest', 'high', 'lowest', 'low']:
        raise ValueError('desired must be one of \"highest, high, lowest, low\"')

    target_res = [None, None]
    if desired in ['highest', "high"]:
        for key, value in run.items():
            if target_res[0] is None or abs(value[0]) < abs(target_res[0]):
                target_res[0] = value[0]
            if target_res[1] is None or abs(value[1]) < abs(target_res[1]):
                target_res[1] = value[1]
    elif desired in ['lowest', "low"]:
        for key, value in run.items():
            if target_res[0] is None or abs(value[0]) > abs(target_res[0]):
                target_res[0] = value[0]
            if target_res[1] is None or abs(value[1]) > abs(target_res[1]):
                target_res[1] = value[1]

    return target_res


def assign_scale_factors(target_res, run):
    for value in run.values():
        value.append(abs(round(value[0] / target_res[0], 1)))
        value.append(abs(round(value[1] / target_res[1], 1)))


def change_resolutions(config, resolutions):
    for run in resolutions['runs']:
        for key, value in run.items():
            if value[4] != 1 or value[5] != 1:
                if value[2] == 'vector':
                    updated_path = change_vector_resolution(value[3], int(value[4]), config, (value[0], value[1]))
                    value[3] = updated_path
                elif value[2] == 'raster':
                    updated_path = change_raster_resolution(value[3], value[4], config)
                    value[3] = updated_path


def alter_config(config, resolutions):
    for i in range(len(resolutions['runs'])):
        for key, value in resolutions['runs'][i].items():
            if key == "wsta" or config['runs'][i][key].split('::')[0] == "lookup_wth":
                config_val = config['runs'][i][key].split('::')
                config_val[-2] = value[3]
                config['runs'][i][key] = '::'.join(config_val)
            else:
                config_val = config['runs'][i][key].split('::')
                config_val[-1] = value[3]
                config['runs'][i][key] = '::'.join(config_val)


def execute(config, plugins):
    """
    Keep track of all the resolutions and what they point to.
    To do this, create a template dictionary containing all of the files.
    None values indicate a placeholder.
    """
    # Create runs sub-dictionary with the same number of runs as the orginal
    resolutions = {"runs": [{key: None for key in run.keys()} for run in config['runs']]}

    # print(json.dumps(resolutions, indent=4))

    # Create a sub-dictionary for fertilizers since an arbitrary number of arguments may be used
    # Only add values if they start in $, this indicates it is an arg (may or may not be file)
    for i in range(len(config['runs'])):
        fertilizer_dict = {arg[1:]: None for arg in config['runs'][i]['fertilizers'].split("::")[1:] if arg[0] == '$'}
        resolutions["runs"][i].update(fertilizer_dict)

    # Find file path of a key
    # sites
    i = 0
    sites_functions = [pythia.functions.xy_from_vector.__name__]
    for run in config['runs']:
        site_path = run['sites'].split("::")[1] if run['sites'].split("::")[0] in sites_functions else None
        try:
            resolutions['runs'][i]['sites'] = get_vector_resolution(site_path) if site_path is not None else None
            resolutions['runs'][i]['sites'].append('vector')
            resolutions['runs'][i]['sites'].append(site_path)
        except fiona.errors.DriverError:
            logging.error(
                "Specified file path for \"sites\" does not point to a vector file. Path: %s",
                site_path
            )
        i += 1

    to_delete = []
    # Iterate through every run in the config file
    for i in range(len(config['runs'])):
        for key, value in config['runs'][i].items():
            if key in ["sites"]:
                continue
            elif isinstance(value, str):
                try:
                    raster_pos = value.split('::').index('raster')
                    try:
                        resolutions['runs'][i][key] = get_raster_resolution(value.split("::")[raster_pos + 1])
                        resolutions['runs'][i][key].append('raster')
                        resolutions['runs'][i][key].append(value.split("::")[raster_pos + 1])
                    except rasterio.errors.RasterioIOError:
                        logging.error(
                            "Specified file path for \"%s\" does not point to a raster file. Path: %s",
                            key, value.split("::")[raster_pos + 1]
                        )
                except ValueError:
                    try:
                        vector_pos = value.split('::').index('vector')
                        try:
                            resolutions['runs'][i][key] = get_vector_resolution(value.split("::")[vector_pos + 1])
                            resolutions['runs'][i][key].append('vector')
                            resolutions['runs'][i][key].append(value.split("::")[vector_pos + 1])
                        except fiona.errors.DriverError:
                            logging.error(
                                "Specified file path for \"%s\" does not point to a raster file. Path: %s",
                                key,
                                value.split("::")[vector_pos + 1]
                            )
                    except ValueError:
                        if key not in to_delete:
                            to_delete.append(key)
            else:
                if key not in to_delete:
                    to_delete.append(key)

    # Remove non-file keys from resolutions dict
    for key in to_delete:
        for i in range(len(config['runs'])):
            del resolutions['runs'][i][key]

    for run in resolutions['runs']:
        assign_scale_factors(get_desired_res(run, "highest"), run)
    change_resolutions(config, resolutions)

    alter_config(config, resolutions)

    print(json.dumps(config, indent=4))
    return config
