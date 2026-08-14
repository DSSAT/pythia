Understanding Pythia and DSSAT
==============================

Purpose and scope
-----------------

DSSAT simulates crop growth at a point from weather, soil, crop, and management
inputs. Pythia provides the spatial orchestration around that point model. It
selects geographic locations, resolves the appropriate inputs for each one,
creates DSSAT experiments, executes them, and optionally combines their
outputs.

Pythia does not replace DSSAT and it does not turn DSSAT itself into a raster
model. Each selected cell or feature becomes an independent point simulation.
The quality and meaning of the final spatial product therefore depend on the
resolution, coordinate reference system, coverage, and quality of every input.

From maps to experiments
------------------------

Pythia uses two common kinds of spatial data:

* a **vector** represents locations or boundaries as points, lines, or
  polygons with an attribute table;
* a **raster** is a grid whose cells contain values such as a soil identifier,
  harvest area, or another spatial variable.

A JSON configuration connects those spatial sources to DSSAT inputs. Lookup
expressions such as ``raster::...``, ``xy_from_vector::...``, and
``lookup_ghr::...`` tell Pythia how to derive a value at each simulation
location. The DSSAT experiment template supplies the text structure into which
those values are written.

Operational workflow
--------------------

The workflow has three independently callable stages:

``--setup``
   Select sites, evaluate spatial lookups, and create the DSSAT working
   directories and experiment files.

``--run-dssat``
   Execute the configured DSSAT command for the prepared experiments.

``--analyze``
   Read model results and produce the configured aggregate outputs.

``--all`` runs the three stages in that order. Running stages separately is
useful for inspecting generated inputs, scheduling experiments on a cluster,
or diagnosing failures.

Inputs that must agree
----------------------

Before a large simulation, check the following relationships on a small area:

* site coordinates overlap the weather, soil, and harvest-area data;
* all layers use compatible coordinate reference systems;
* raster cell values use the units and missing-value conventions expected by
  the relevant lookup function;
* soil identifiers resolve to profiles present in the configured ``.SOL``
  files;
* the crop and cultivar identifiers exist in the DSSAT cultivar files;
* years requested in ``runs`` are covered by the weather data;
* the DSSAT executable can run one generated experiment outside Pythia.

Configuration structure
-----------------------

``workDir``, ``templateDir``, ``weatherDir``, and ``ghr_root`` establish the
file layout. ``default_setup`` describes shared experiment values and spatial
lookups. ``runs`` contains one or more scenarios that override or add crop,
management, and time settings. ``dssat.executable`` identifies the DSSAT
command, and ``analytics_setup`` controls post-processing.

For a field-by-field reference, see :doc:`json`. For the supported one- and
two-band soil formats, see :doc:`soil_rasters`. The downloadable Sri Lanka
package provides complete maize and rice configurations that can be configured
without editing paths manually; follow the root project README.

Practical validation strategy
-----------------------------

Start with ``pythia --validate-example`` when using the released example data.
Then run ``--setup`` and inspect a generated experiment before invoking DSSAT.
Run one small scenario, compare its output with a known DSSAT run, and only then
increase the spatial or temporal scope. This separates configuration problems
from DSSAT model errors and from resource limitations.
