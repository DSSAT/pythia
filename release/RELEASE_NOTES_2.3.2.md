# Pythia 2.3.2

Pythia 2.3.2 delivers the soil compatibility, Sri Lanka example, validation,
documentation, and packaging improvements prepared for 2.3.1, together with a
corrected Docker and GitHub release pipeline.

The Docker build now keeps the DSSAT base image on Debian 12 repositories,
installs current Bookworm package revisions without fragile build-number pins,
and installs Poetry inside an isolated virtual environment. The GitHub Actions
used by the workflow now run on Node.js 24. Release commits and tags are
published only after tests, Python packaging, and the Docker build succeed.

Users of one-band GHR soil rasters should follow the compatibility and example
instructions in the 2.3.1 notes. No soil raster conversion is required.
