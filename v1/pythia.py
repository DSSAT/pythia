import argparse
from datetime import datetime
import math
import os
import numpy as np
import pandas as pd
import rasterio

def loadRaster(raster):
    data = {}
    with rasterio.open(raster) as r:
        data['nd_val'] = r.nodata
        data['vals'] = r.read(1)
    return data

def loadSummary(d, idx, items):
    df = pd.read_csv(os.path.join(d, 'summary.csv'), index_col=False)
    lim =  df.filter(items=items, col_index)
    lim.replace(-99, 0, inplace=True)
    lim.fillna(0, inplace=True)
    lim['adj'] = np.where((lim['ADAT'] == 0) | (lim['HDAT'] == 0), 1, 0)
    lim.loc[lim['ADAT'] == 0, 'HDAT'] = 0
    df = None
    return lim

def applyScale(df, scale):
    return df*scale

def applyAverage(df, col, cum):
    return round(df[col]/cum)

def applyDateAverage(df, col, cum):
    return df[col]/(cum - df['adj'])

def accumulate(acc, df):
    if acc is None:
        return df
    else:
        return acc+df

def main(args):
    scale_data = loadRaster(args.scale)
    directories = next(os.walk(args.wd))[1]
#    coord_list = [tuple(map(int, d.split('_'))) for d in directories]
    scale_factors = ([scale_data['vals'][c[0]][c[1]] for c in [tuple(map(int, d.split('_'))) for d in directories]])
    sf_cum = sum(scale_factors)
    if args.debug:
        print(list(zip(directories, scale_factors)))
        print(sf_cum)
    acc = None
    scale_adjust = {}
    for idx, d in enumerate(directories):
        if args.debug:
            print("Running {}".format(d))
        summary = loadSummary(os.path.join(args.wd, d))
        scaled = applyScale(summary, scale_factors[idx])
        acc = accumulate(acc, scaled)
    if args.debug:
        print(acc['adj'])
    acc['HWAM'] = (acc['HWAM'].astype(int))/1000 #hardcoded to Metric Tonnes
    acc['PRCP'] = applyDateAverage(acc, 'PRCP', sf_cum).astype(int)
    acc['AY'] = round(acc['HWAM']/sf_cum).astype(int)
    acc['PDAT'] = pd.to_datetime(applyAverage(acc, 'PDAT', sf_cum).apply(math.floor).apply(str), format="%Y%j", errors='coerce')
    acc['ADAT'] = pd.to_datetime(applyDateAverage(acc, 'ADAT', sf_cum).apply(math.floor).apply(str), format="%Y%j", errors='coerce')
    acc['HDAT'] = pd.to_datetime(applyDateAverage(acc, 'HDAT', sf_cum).apply(math.floor).apply(str), format="%Y%j", errors='coerce')
    acc['YEAR'] = acc.index+1984
    acc['SCALE'] = round((acc['adj']/sf_cum)*100).astype(int)
    acc = acc.reindex(columns=['YEAR', 'HWAM', 'AY', 'PRCP', 'PDAT', 'ADAT', 'HDAT', 'SCALE'])
    acc.columns = ['Year', 'Production (t)', 'Average Yield (kg/ha)', 'Average Rainfall (mm)', 'Average Planting Date', 'Average Anthesis Date', 'Average Harvest Date', 'Percent Failures']
    if args.debug or args.no_output:
        print(acc)
    if not args.no_output:
        acc.to_csv(os.path.join(args.wd, 'overview.csv'), index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The oracle')
    parser.add_argument('wd', help='The working directory')
    parser.add_argument('scale', help='The raster used to scale up the results')
    parser.add_argument('--no-output', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    main(args)
