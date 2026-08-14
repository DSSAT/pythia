# Pythia Sri Lanka example data

This directory accompanies a Pythia release. It contains three configurations:

- `Sri_Lanka/SL_Maize.json`
- `Sri_Lanka/SL_Rice.json`
- `Sri_Lanka/SL_Rice_env.json`

The configurations are portable templates. After installing both Pythia and
DSSAT, configure all three at once:

```console
pythia --configure-example /path/to/Simulation_Data \
  --dssat-executable /path/to/dscsm048
```

On Windows, for example:

```powershell
pythia --configure-example C:\Pythia\Simulation_Data `
  --dssat-executable C:\DSSAT48\DSCSM048.EXE
```

The command replaces `<</path/to/folder>>` and
`<</path/to/dssat/executable>>`, preserves the original files as
`*.json.template`, and checks every referenced input. It is safe to run the
command again if the directory or DSSAT executable changes.

Validate and run an example:

```console
pythia --validate-example /path/to/Simulation_Data
pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Maize.json
```

Results are written below `OUTPUT/Sri_Lanka`. The bundled one-band
`raster/ggcmi_soils_2.tif` is intentional: compatible Pythia releases resolve
its numeric GHR identifiers through `eGHR/GHR.db` and the `.SOL` files.

For installation, detailed commands, Windows notes, and troubleshooting, see
the README on the Pythia release page.
