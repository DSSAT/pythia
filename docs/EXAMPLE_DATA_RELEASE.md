# Preparing the example-data release asset

The source directory is expected to be named `Simulation_Data` and to contain
the three portable configurations under `Sri_Lanka/`. Each configuration must
contain both tokens:

```text
<</path/to/folder>>
<</path/to/dssat/executable>>
```

The packager can also use the `*.json.template` backups created after local
testing, so personal absolute paths are never published.

## 1. Validate and test locally

```console
poetry run pythia --configure-example /path/to/Simulation_Data \
  --dssat-executable /path/to/dscsm048
poetry run pythia --validate-example /path/to/Simulation_Data
poetry run pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Maize.json
poetry run pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Rice.json
poetry run pythia --all /path/to/Simulation_Data/Sri_Lanka/SL_Rice_env.json
```

Review the results, then build the release asset. There is no need to restore
the active JSON files manually: the original portable templates are used.

## 2. Create the ZIP and checksum

```console
poetry run python scripts/prepare_example_release.py \
  /path/to/Simulation_Data \
  /path/to/Pythia-Example-Data-VERSION.zip
```

The command validates required data, inserts `release/Simulation_Data_README.md`,
and creates a SHA-256 file beside the archive. It excludes generated output,
`.history`, macOS metadata, logs, bytecode, and local template backups. The ZIP
always contains a top-level `Simulation_Data/` directory and an empty
`OUTPUT/` directory.

The command rejects an archive at or above GitHub's 2 GiB per-file release
asset limit. If that happens, split stable supporting data into clearly named
archives and document that all parts must be extracted into the same
`Simulation_Data` directory.

## 3. Inspect before upload

```console
unzip -l /path/to/Pythia-Example-Data-VERSION.zip
shasum -a 256 /path/to/Pythia-Example-Data-VERSION.zip
```

Extract into a new temporary directory, configure it using the installed wheel,
and repeat one maize and one rice run. This is the final check that the release
does not depend on the repository or on the maintainer's filesystem.

## 4. Attach to the GitHub release

Upload both files:

- `Pythia-Example-Data-VERSION.zip`
- `Pythia-Example-Data-VERSION.zip.sha256`

The release notes must state that legacy one-band soil rasters remain supported,
that users do not need to convert `ggcmi_soils_2.tif`, and that the new example
package is configured with `pythia --configure-example`.
