Soil raster formats
===================

Pythia supports both the original one-band GHR soil raster and the newer
two-band encoded soil raster. The format is detected automatically; existing
one-band projects do not need to convert their raster or change their JSON
configuration.

Legacy one-band GHR raster
--------------------------

Each raster cell contains a numeric key. Pythia looks that key up in the
``profile_map`` table of ``GHR.db`` to obtain the DSSAT soil profile ID.

The directory configured by ``ghr_root`` must contain:

* ``GHR.db``;
* the country ``.SOL`` files referenced by the database.

For example, a cell value of ``5130973`` in the Sri Lanka data maps through
``GHR.db`` to profile ``LK04202172``. Pythia then reads ``LK.SOL``.

Example configuration::

   {
     "ghr_root": "C:/pythia/Simulation_Data/eGHR",
     "default_setup": {
       "id_soil": "lookup_ghr::raster::C:/pythia/Simulation_Data/raster/ggcmi_soils_2.tif"
     }
   }

Two-band encoded raster
-----------------------

The newer format stores the profile ID directly:

* band 1 contains the encoded two- or four-letter prefix;
* band 2 contains the numeric part of the profile ID;
* ``0`` is the default ``nodata`` value for rasters created by Pythia.

For a two-letter prefix, the numeric part is padded to eight digits. For a
four-letter prefix, it is padded to six digits. For example, band values
``6682`` and ``5142095`` decode to ``BR05142095``.

Create a raster from one or more DSSAT ``.SOL`` files::

   pythia --create-raster --raster-input cli \
     --raster-output data/soils.tif \
     --raster-sol-path data/soils \
     --raster-recursive

Troubleshooting
---------------

``GHR.db was not found``
   A one-band raster was detected, but ``ghr_root`` does not contain the
   legacy database. Correct ``ghr_root`` or restore ``GHR.db``.

``was not found in GHR.db``
   The raster cell contains an ID that is not present in ``profile_map``.
   Ensure that the raster and database came from the same input-data release.

``DSSAT soil file was not found``
   The profile was resolved, but its country ``.SOL`` file is missing from
   ``ghr_root``.

``expected 1 legacy band or 2 encoded bands``
   The selected file is not a supported Pythia soil raster.

Migration guidance
------------------

Existing one-band projects should continue using their raster, ``GHR.db`` and
``.SOL`` files together. Conversion to the two-band format is optional. Never
replace only the raster: the raster, database and soil files must describe the
same profile collection.
