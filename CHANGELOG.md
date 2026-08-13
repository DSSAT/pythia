# Changelog

## Unreleased

### Fixed

- Restored backward compatibility with legacy one-band GHR soil rasters.
- Automatically detect one-band legacy and two-band encoded soil rasters.
- Resolve legacy raster IDs through `GHR.db` and provide actionable errors for
  missing database records and DSSAT `.SOL` files.
- Prevent out-of-bounds soil raster access and support coordinate reprojection.
- Read only the requested two-band raster pixel instead of loading both bands
  for every lookup.
- Corrected and documented the Sri Lanka example workflow; its existing
  one-band `ggcmi_soils_2.tif` does not require conversion.
- Fixed plugin hook execution so context is passed once and plugin return values
  are composed correctly.

### Added

- Added `--configure-example` and `--validate-example` commands for the
  downloadable Sri Lanka data.
- Added a reproducible example-data packager that removes local/generated files,
  restores portable JSON templates, enforces the GitHub asset size limit, and
  writes a SHA-256 checksum.
- Expanded installation, conceptual, input configuration, troubleshooting, and
  release documentation.
- Updated the release workflow to test and build wheel/source artifacts before
  publishing them.

### Testing

- Added self-contained regression coverage for both soil raster formats,
  including the Sri Lanka coordinate and profile reported by users.
- Added tests for repeatable example configuration, archive portability, and
  plugin hook execution.
