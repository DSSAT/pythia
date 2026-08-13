# Pythia

Pythia is an extensible framework for running point-based crop models over
spatial data. It turns raster and vector inputs into DSSAT experiments, runs
DSSAT, and can aggregate the resulting outputs.

The usual workflow is:

1. read a JSON configuration;
2. select locations from a vector or raster data set;
3. resolve weather, soil, cultivar, and management inputs for each location;
4. create DSSAT experiment directories;
5. run DSSAT and optionally aggregate results.

## Requirements

- Python 3.8 or newer (the automated tests cover Python 3.8 and 3.12);
- a working [DSSAT installation](https://get.dssat.net/);
- Git and [Poetry](https://python-poetry.org/docs/#installation) only when
  building Pythia from source.

R and RStudio are optional and are needed only for separate post-processing
scripts. They are not required to install or run Pythia.

On Windows, enable **Developer Mode** (or run with privileges that permit
symbolic links). Pythia uses links while preparing DSSAT work directories.

## Install a released build

Download the Pythia `.whl` file for your operating environment from the
[GitHub release](https://github.com/DSSAT/pythia/releases/latest). For an
isolated command that is available outside the source directory, `pipx` is the
recommended installation method:

```console
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install /path/to/pythia-VERSION-py3-none-any.whl
```

Open a new terminal, then verify exactly which command is being used:

```console
command -v pythia
pythia --help
pipx list
```

On Windows PowerShell, use `py` instead of `python3` and
`Get-Command pythia` instead of `command -v pythia`.

To replace an older pipx installation with a new local wheel:

```console
pipx install --force /path/to/pythia-VERSION-py3-none-any.whl
```

Do not install into a Homebrew- or system-managed Python with
`--break-system-packages`. A virtual environment or pipx avoids modifying that
Python installation.

## Build and install from source

```console
git clone https://github.com/DSSAT/pythia.git
cd pythia
python3 -m pip install --user poetry
poetry install
poetry run pytest
poetry build
pipx install --force dist/pythia-VERSION-py3-none-any.whl
```

Keep the committed `poetry.lock`; it makes dependency resolution repeatable.
During development, commands can also be run without a global installation:

```console
poetry run pythia --help
```

## Download and configure the Sri Lanka example

Download `Pythia-Example-Data-VERSION.zip` from the same GitHub release as the
Pythia wheel and extract it. The resulting layout includes:

```text
Simulation_Data/
├── eGHR/
│   ├── GHR.db
│   └── LK.SOL
├── raster/
│   └── ggcmi_soils_2.tif
├── Sri_Lanka/
│   ├── SL_Maize.json
│   ├── SL_Rice.json
│   └── SL_Rice_env.json
├── weather_data/Sri_Lanka/
└── OUTPUT/
```

The three JSON files intentionally contain portable placeholders. Replace them
and validate all referenced files with one command:

```console
pythia --configure-example /path/to/Simulation_Data \
  --dssat-executable /path/to/dscsm048
```

Windows PowerShell example:

```powershell
pythia --configure-example C:\Pythia\Simulation_Data `
  --dssat-executable C:\DSSAT48\DSCSM048.EXE
```

This command:

- replaces `<</path/to/folder>>` with the extracted directory;
- replaces `<</path/to/dssat/executable>>` with the DSSAT executable;
- keeps each portable source as `*.json.template`;
- checks the example structure and every referenced input path.

It is safe to run the command again after moving the data or DSSAT. Confirm the
current configuration at any time:

```console
pythia --validate-example /path/to/Simulation_Data
```

## Run the examples

Run the complete setup, simulation, and analysis sequence:

```console
pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Maize.json
pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Rice.json
pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Rice_env.json
```

For troubleshooting or HPC workflows, the stages can be run separately:

```console
pythia --setup CONFIG.json
pythia --run-dssat CONFIG.json
pythia --analyze CONFIG.json
```

Use `--clean-work-dir` only when an existing work directory should be removed
before a new run. Results are written to the `workDir` defined in each JSON,
below `Simulation_Data/OUTPUT/Sri_Lanka` in the bundled examples.

## Configuration overview

The main JSON fields are:

| Field | Purpose |
| --- | --- |
| `workDir` | Generated DSSAT experiments and outputs |
| `templateDir` | DSSAT experiment templates |
| `weatherDir` | Weather files used by the experiments |
| `ghr_root` | `GHR.db` and DSSAT `.SOL` files |
| `default_setup` | Values and spatial lookup functions shared by runs |
| `dssat.executable` | DSSAT command-line executable |
| `runs` | Crop, management, year, and harvest-area scenarios |
| `analytics_setup` | Output aggregation options |

See the [configuration reference](docs/json.rst) and the
[conceptual and operational guide](docs/understanding_pythia.rst) for details.

## Soil raster compatibility

Pythia automatically supports both soil raster formats:

| Format | Raster bands | Supporting data |
| --- | ---: | --- |
| Legacy GHR | 1 | `GHR.db` plus the referenced `.SOL` files |
| Encoded profile | 2 | Referenced `.SOL` files under `ghr_root` |

The Sri Lanka example intentionally uses the legacy one-band
`ggcmi_soils_2.tif`. Do not add a second band. Pythia reads the numeric cell
identifier, resolves it through `eGHR/GHR.db`, and loads the matching profile
from the `.SOL` files. See the [soil raster guide](docs/soil_rasters.rst) for
format detection, diagnostics, and migration guidance.

## Troubleshooting

- **`pythia: command not found`** — reopen the terminal after `pipx ensurepath`,
  then inspect `pipx list` and `command -v pythia`.
- **More than one executable is found** — remove the obsolete installation and
  keep the pipx path first in `PATH`.
- **Placeholders remain in JSON** — rerun `--configure-example` with absolute
  paths.
- **A referenced file is missing** — run `--validate-example`; it reports the
  exact configuration and path.
- **A one-band raster is rejected as requiring two bands** — an older/regressed
  Pythia build is being executed. Install the release containing the legacy GHR
  compatibility fix and confirm the executable path again.
- **Windows reports a symbolic-link error** — enable Developer Mode and open a
  new terminal.

## Developer and release documentation

- [Release procedure](docs/RELEASING.md)
- [Example-data packaging instructions](docs/EXAMPLE_DATA_RELEASE.md)
- [Change log](CHANGELOG.md)

Pythia is distributed under the BSD 3-Clause license.
