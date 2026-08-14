# Pythia release guide

Pythia uses [semantic versioning](https://semver.org/): increment `MAJOR` for
incompatible changes, `MINOR` for backward-compatible features, and `PATCH` for
backward-compatible fixes.

The failed 2.3.1 workflow already published its version commit and tag before
the Docker step failed. Do not reuse or move that tag. After merging the Docker
release fix, publish 2.3.2 so every artifact is built from the same immutable
source revision.

## Before triggering the release

1. Work in a branch and review `git status` and `git diff`.
2. Update `CHANGELOG.md`, README, and any affected reference documentation.
3. Run:

   ```console
   poetry install
   poetry run pytest
   poetry build
   ```

4. Install the wheel in a clean pipx environment and check:

   ```console
   pipx install --force dist/pythia-VERSION-py3-none-any.whl
   pythia --help
   ```

5. Prepare and test the Sri Lanka archive by following
   [EXAMPLE_DATA_RELEASE.md](EXAMPLE_DATA_RELEASE.md).
6. Commit the reviewed source, documentation, tests, and scripts. Open and merge
   a pull request before creating the release.

Do not delete `poetry.lock`; update it with Poetry when dependency constraints
change.

## GitHub release workflow

Open [Actions → Release](https://github.com/DSSAT/pythia/actions/workflows/release.yml),
choose **Run workflow**, enter a plain semantic version such as `2.3.2`, and
run it from the intended branch. Do not add a `v` prefix.

The workflow validates the version, updates `pyproject.toml`, builds and tests
the package, pushes the version commit and tag, builds the Docker image, creates
the GitHub release, and attaches the Python wheel and source archive.

After the workflow succeeds, manually attach the tested example ZIP and its
`.sha256` file. Confirm that the release page contains all four kinds of
artifact:

- Python wheel;
- Python source distribution;
- example-data ZIP and SHA-256 checksum;
- Docker image with the version and `latest` tags.

Finally, download the public assets rather than using local copies and repeat
the installation, `--validate-example`, maize, and rice smoke tests.
