JSON Configuration File
=======================

The JSON configuration file consists of different sections. All references to files and directories are considered relative to the executing directory. Absolute file references are allowed.

General
-------
This is the root of the JSON object. All values in this section are considered to be globally available.

name
   :Type: no whitespace string 
   :Required: true
   :Description: The name of this configuration.
   

workDir
   :Type: directory string 
   :Required: true
   :Description: The root output directory of this run. All DSSAT files will generated under this directory.

templateDir
   :Type: directory string
   :Required: true
   :Description: The location of the template files used to generate the DSSAT files.

weatherDir
   :Type: directory string
   :Required: true
   :Descrption: The location of the DSSAT formatted weather files. The files in this directory will be symlinked, not copied, into the DSSAT directories.

cores
   :Type: positive integer
   :Default value: number of logical CPUs available.
   :Description: The number of cores to be used by pythia. Cores are used to execute the model.
   

threads
   :Type: positive integer
   :Default value: number of cores available / 2
   :Description: The number of threads to be used by pythia. This is used for I/O work. 
   
sample
   :Type: positive integer
   :Description: Used to subset the data. Applies the configuration the first *x* number of valid simulations. This may be different between runs.

ghr_root
   :Type: directory string
   :Description: The location of the eGHR (ehanced Global High Resolution) soils data.

Default Setup (default_setup)
-----------------------------

The ``default_setup`` section is used to configure the basic DSSAT run.

Non-DSSAT variables
~~~~~~~~~~~~~~~~~~~
include
  :Type: array of file strings
  :Description: Additional files which need to be included in the DSSAT directory, for example: custom cultivar files.

template
   :Type: file string
   :Required: true
   :Description: The template used in the default run. This file should reside in the ``templateDir``.

sites
   :Type: array of two item arrays **or** the function ``xy_from_vector`` with a point vector file.
   :Required: true
   :Description: The sites to run. Each point in the array or point vector file. The array format is ``[latitude,longitude]``.
   :Assigns: ``xcrd``, ``ycrd``
   :Example: ::

      {"sites": [[29.6340239,-82.3631502]]}

               

startYear
   :Type: 4-digit year
   :Required: true
   :Description: The first year of simulation

Supported DSSAT variables
~~~~~~~~~~~~~~~~~~~~~~~~~
The following are the supported DSSAT variables. To add more variables, please extend ``template.py``.

+-------+---------+-------+-------+
| cname | icbl    | pdate | sno3  |
+-------+---------+-------+-------+
| erain | icren   | pfrst | wsta  |
+-------+---------+-------+-------+
| famn  | icres   | ph2ol | xcrd  |
+-------+---------+-------+-------+
| fdap  | icrt    | plast | ycrd  |
+-------+---------+-------+-------+
| fdate | id_soil | ramt  |       |
+-------+---------+-------+-------+
| fdate | ingeno  | sdate |       |
+-------+---------+-------+-------+
| fhdur | irrig   | sh2o  |       |
+-------+---------+-------+-------+
| flhst | nyers   | snh4  |       |
+-------+---------+-------+-------+

**Note:** All dates are ISO formatted as ``YYYY-MM-DD``

DSSAT Structures
~~~~~~~~~~~~~~~~

ic_layers
   :Type: Array of initial condition layer objects 
   :Shape: ``[{"icbl": <value>, "sh2o": <value>, "shn4": <value>, "sno3": <value>},...]``
   :Helper function: ``generate_ic_layers``

fertilizers
   :Type: Array of fertilizer applications
   :Shape: ``[{"fdap": <value>, "famn": <value>},...]``
   :Helper function: ``split_fert_dap_percent``

Arbitrary Variables
~~~~~~~~~~~~~~~~~~~


Useful Functions
~~~~~~~~~~~~~~~~