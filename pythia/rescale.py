import json
import logging
import os

import fiona
import rasterio

import pythia.functions


def get_raster_resolution(file_path):
    with rasterio.open(file_path, 'r') as raster:
        return (raster.profile['transform'][0], raster.profile['transform'][4])


def get_vector_resolution(file_path):
    with fiona.open(file_path, 'r') as src:
        min_x_dist, min_y_dist = None, None
        for i in range(len(src)-1):
            x_dist = abs(src[i]['geometry']['coordinates'][0] - src[i+1]['geometry']['coordinates'][0])
            y_dist = abs(src[i]['geometry']['coordinates'][1] - src[i+1]['geometry']['coordinates'][1])
            if 0 < x_dist:
                if min_x_dist is None or x_dist < min_x_dist:
                    min_x_dist = x_dist
            if 0 < y_dist:
                if min_y_dist is None or y_dist < min_y_dist:
                    min_y_dist = y_dist
        return (min_x_dist, min_y_dist)


def change_raster_resolution(file_path, scale_factor, config, dst_path=None):
    file_name = file_path.split('/')[-1].split('.')[0]

    with rasterio.open(file_path, 'r') as src:
        data = src.read()
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
        new_path = rescale_dir + new_filename if dst_path is None else dst_path

        try:
            os.makedirs(rescale_dir, exist_ok=True)
        except OSError as e:
            logging.error(
                "OSError encountered when attempting to create rescale_dir: " + str(e)
            )
            raise e

        with rasterio.open(new_path, 'w', **profile) as out_file:
            for i in range(1, profile['count'] + 1):
                rasterio.warp.reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(out_file, i),
                    src_transform=profile['transform'],
                    src_crs=profile['crs'],
                    dst_transform=transform,
                    dst_crs=profile['crs'],
                    resampling=resampling_mode
                )


def change_vector_resolution(file_path, scale_factor, config, dst_path=None):
    pass


def execute(config, plugins):
    # print(json.dumps(config, indent=4))
    """
    Keep track of all the resolutions and what they point to.
    To do this, create a template dictionary containing all of the files.
    None values indicate a placeholder.
    """
    print(json.dumps(config, indent=4), "\n\n\n")

    # Create runs sub-dictionary with the same number of runs as the orginal
    resolutions = {"runs": [{key: None for key in run.keys()} for run in config['runs']]}

    # Create a sub-dictionary for fertilizers since an arbitrary number of arguments may be used
    # Only add values if they start in $, this indicates it is an arg (may or may not be file)
    for i in range(len(config['runs'])):
        fertilizer_dict = {arg[1:]: None for arg in config['runs'][i]['fertilizers'].split("::")[1:] if arg[0]=='$'}
        resolutions["runs"][i].update(fertilizer_dict)

    # Find file path of a key
    # sites
    i = 0
    sites_functions = [pythia.functions.xy_from_vector.__name__]
    for run in config['runs']:
        site_path = run['sites'].split("::")[1] if run['sites'].split("::")[0] in sites_functions else None
        print(site_path)
        try:
            resolutions["runs"][i]['sites'] = get_vector_resolution(site_path) if site_path is not None else None
        except fiona.errors.DriverError:
            logging.error(
                "Specified file path for \"sites\" does not point to a vector file. Path: %s",
                site_path
            )
        i += 1

    to_delete = []
    for i in range(len(config['runs'])):
        for key, value in config['runs'][i].items():
            if key == "sites":
                continue
            elif isinstance(value, str):
                try:
                    raster_pos = value.split('::').index('raster')
                    try:
                        resolutions['runs'][i][key] = get_raster_resolution(value.split("::")[raster_pos + 1])
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
                        except fiona.errors.DriverError:
                            logging.error(
                                "Specified file path for \"%s\" does not point to a raster file. Path: %s",
                                key,
                                value.split("::")[vector_pos + 1]
                            )
                    except ValueError:
                        to_delete.append(key)
            else:
                to_delete.append(key)

    # Remove non-file keys from resolutions dict
    for key in to_delete:
        for i in range(len(config['runs'])):
            del resolutions['runs'][i][key]



    print(json.dumps(resolutions, indent=4))
