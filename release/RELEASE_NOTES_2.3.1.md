# Pythia 2.3.1

This patch release restores compatibility with existing one-band GHR soil
rasters, including the `ggcmi_soils_2.tif` distributed with the Sri Lanka
example. It also retains support for the newer two-band encoded profile format.

## Action required for current users

If Pythia reports that a one-band soil raster “must have 2 bands,” install the
2.3.1 wheel. **Do not convert or add a band to the existing raster.** For a
legacy one-band input, keep these resources together:

- the soil raster referenced by `id_soil`;
- `GHR.db` under the configured `ghr_root`;
- the `.SOL` files referenced by `GHR.db`, also under `ghr_root`.

Existing JSON configurations remain compatible and require no schema change.

## Updated Sri Lanka example

Download `Pythia-Example-Data-2.3.1.zip` from this release, extract it, and run:

```console
pythia --configure-example /path/to/Simulation_Data \
  --dssat-executable /path/to/dscsm048
pythia --validate-example /path/to/Simulation_Data
pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Maize.json
```

The configuration command prepares all three examples: maize, rice, and rice
with environment modifications. It saves the portable originals as
`*.json.template` and can be rerun after moving DSSAT or `Simulation_Data`.

## Additional improvements

- automatic one-band/two-band soil format detection;
- checked raster bounds and coordinate reprojection;
- actionable errors for missing GHR mappings and `.SOL` profiles;
- pixel-level reads for two-band rasters instead of loading full rasters;
- corrected plugin context execution;
- expanded installation, configuration, troubleshooting, and release guides;
- regression tests for both soil formats and the reported Sri Lanka location.

Verify the downloaded example archive against
`Pythia-Example-Data-2.3.1.zip.sha256` before extracting it.
