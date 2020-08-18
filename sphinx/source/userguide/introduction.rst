Introduction
============

One of the big challenges in CMIP6 is to produce the ensemble of diagnostics requested by the
CMIP6 Data Request (DR). Configuring the model outputs so that they comply with the Data Request
is nearly unachievable by hand, given thousands of variables, hundreds of experiments to handle for
groups participating to numbers of MIPs. Those models that use XIOS to handle their I/O can benefit
from dr2xml to help writing XIOS configuration XML files so that output data files meet the
CMIP6/CMOR format and metadata requirements. Dr2xml exploits the CMIP6 Data Request API to
automate the generation of XIOS XML configuration files.
To meet the CMIP6/CMOR data requirements, dr2xml relies on essential XIOS functionalities:

- flexibility in the file naming and structure (multi or mono-variable files, mono-variable format
  being the CMIP standard)
- flexibility in the time splitting length (useful to generate manageable file size)
- possibility to glue any global attributes to the file (useful to include the set of mandatory
  CMOR global attributes)
- ability to perform "on the fly" temporal and spatial operations, used to conform to CMIP6
  "cell_methods" and "spatial_shapes"

Dr2xml fully exploits the Data Request content and scoping tools offered by the Data Request Python
API (https://earthsystemcog.org/projects/wip/CMIP6DataRequest) . Given some settings provided by
the user, e.g. defining the MIP(s) the lab is involved in, the current experiment/simulation to be run,
maximum priority for the outputs (see section 2 for the complete list of settings) dr2xml
automatically:

- identifies the list of requested CMOR variables that applies;
- collects CMIP6 metadata associated to experiment(s) and CMOR variables (e.g.:
  experiment_id, variable_id, standard_name, long_name);
- gets temporal shape (e.g.: ‘time mean over sea ice’) and spatial shape (e.g.: ‘global field 7
  pressure levels’; ‘ocean basin meridional section’) of each required CMOR variable.
