#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In the context of Climate Model Intercomparison Projects (CMIP) :

A few functions for processing
  - a CMIP Data request and
  - a set of settings related to a laboratory, and a model
  - a set of settings related to an experiment (i.e. a set of numerical
      simulations),

to generate a set of xml-syntax files used by XIOS (see
https://forge.ipsl.jussieu.fr/ioserver/) for outputing geophysical
variable fields

First version (0.8) : S.Senesi (CNRM) - sept 2016

Changes :
  - oct 2016 - Marie-Pierre Moine (CERFACS) - handle 'home' Data Request in addition
  - dec 2016 - S.Senesi (CNRM) - improve robustness
  - jan 2017 - S.Senesi (CNRM) - handle split_freq; go single-var files; adapt to new DRS...
  - feb 2017 - S.Senesi (CNRM) - handle grids and remapping; put some func in separate module
  - april-may 2017 - M-P Moine (CERFACS) : handle pressure axes...
  - june 2017 - S.Senesi (CNRM)  introduce horizontal remapping
  - july 2017 - S.Senesi -CNRM)  improve efficiency in remapping; allow for
                 sampling before vert. interpolation, for filters on table, reqLink..
                 Adapt filenames to CMIP6 conventions (including date offset).
                 Handle remapping for CFsites

Rather look at git log for identifying further changes and contributors....

"""
####################################
# Pre-requisites
####################################

# 1- CMIP6 Data Request package retrieved using
#    svn co http://proj.badc.rl.ac.uk/svn/exarch/CMIP6dreq/tags/01.00.21
#    (and must include 01.00.21/dreqPy in PYTHONPATH)

# 2- CMIP6 Controled Vocabulary (available from
# https://github.com/WCRP-CMIP/CMIP6_CVs). You will provide its path
# as argument to functions defined here

# 3- XIOS release must be 1442 or above (to be fed with the outputs)
#  see https://forge.ipsl.jussieu.fr/ioserver/wiki

####################################
# End of pre-requisites
####################################

from __future__ import print_function, division, absolute_import, unicode_literals

import sys

import cProfile
import pstats
import io

from collections import OrderedDict

# Utilities
from utils import print_struct

# Logger
from logger import initialize_logger, get_logger, change_log_level

# Global variables and configuration tools
from config import get_config_variable, set_config_variable, python_version, initialize_config_variables

# Interface to settings dictionaries
from settings_interface import initialize_dict, get_variable_from_lset_with_default, \
    get_variable_from_lset_without_default

# Interface to Data Request
from dr_interface import get_DR_version, get_uid, get_request_by_id_by_sect

# Tools to deal with ping files
from pingfiles_interface import read_pingfiles_variables

# Tools to deal with computation of used pressure levels
from plevs_unions import create_xios_axis_and_grids_for_plevs_unions

# Variables tools
from vars_home import multi_plev_suffixes, single_plev_suffixes
from vars_selection import initialize_sn_issues, select_variables_to_be_processed

# XIOS reading and writing tools
from Xparse import init_context
from Xwrite import write_xios_file_def

# Info printing tools
from infos import print_some_stats


print("\n", 50 * "*", "\n*")
print("* %29s" % "dr2xml version: ", get_config_variable("version"))

print("* %29s" % "CMIP6 conventions version: ", get_config_variable("CMIP6_conventions_version"))

# mpmoine_merge_dev2_v0.12: posixpath.dirname ne marche pas chez moi
# TBS# from os import path as os_path
# TBS# prog_path=os_path.abspath(os_path.split(__file__)[0])

print("* %29s" % "CMIP6 Data Request version: ", get_DR_version())
print("\n*\n", 50 * "*")

""" An example/template  of settings for a lab and a model"""
example_lab_and_model_settings = {

    'institution_id': "CNRM-CERFACS",  # institution should be read in CMIP6_CV, if up-to-date

    # We describe the "CMIP6 source type" (i.e. components assembly) which is the default
    # for each model. This value can be changed on a per experiment basis, in experiment_settings file
    # However, using a 'configuration' is finer (see below)
    # CMIP6 component conventions are described at
    #          https://github.com/WCRP-CMIP/CMIP6_CVs/blob/master/CMIP6_source_type.json
    'source_types': {"CNRM-CM6-1": "AOGCM AER", "CNRM-CM6-1-HR": "AOGCM AER",
                     "CNRM-ESM2-1": "AOGCM BGC AER CHEM", "CNRM-ESM2-1-HR": "AOGCM BGC AER"},

    # Optional : 'configurations' are shortcuts for a triplet (model, source_type, unused_contexts)
    'configurations': {
        "AGCM": ("CNRM-CM6-1", "AGCM", ['nemo']),
        "AESM": ("CNRM-ESM2-1", "AGCM BGC AER CHEM", ['nemo']),
        "AOGCM": ("CNRM-CM6-1", "AOGCM", []),
        "AOESM": ("CNRM-ESM2-1", "AOGCM BGC AER CHEM", []),
        "AGCMHR": ("CNRM-CM6-1-HR", "AGCM", ['nemo']),
        "AESMHR": ("CNRM-ESM2-1", "AGCM BGC AER", []),
        "AOGCMHR": ("CNRM-CM6-1-HR", "AOGCM", []),
        "AOESMHR": ("CNRM-ESM2-1", "AOGCM BGC AER", []),
        "LGCM": ("CNRM-CM6-1", "LAND", ['nemo']),
        "LESM": ("CNRM-ESM2-1", "LAND BGC", ['nemo']),
        "OGCM": ("CNRM-CM6-1", "OGCM", ['surfex', 'trip']),
        "OESM": ("CNRM-ESM2-1", "OGCM BGC", ['surfex', 'trip'])},

    # 'source'         : "CNRM-CM6-1", # Useful only if CMIP6_CV is not up to date
    'references': "A character string containing a list of published or web-based " + \
                  "references that describe the data or the methods used to produce it." + \
                  "Typically, the user should provide references describing the model" + \
                  "formulation here",
    'info_url': "http://www.umr-cnrm.fr/cmip6/",
    'contact': 'contact.cmip@meteo.fr',

    # We account for the list of MIPS in which the lab takes part.
    # Note : a MIPs set limited to {'C4MIP'} leads to a number of tables and
    # variables which is manageable for eye inspection
    'mips_for_test': {'C4MIP', 'SIMIP', 'OMIP', 'CFMIP', 'RFMIP'},
    'mips': {
        "LR": {'AerChemMIP', 'C4MIP', 'CFMIP', 'DAMIP', 'FAFMIP', 'GeoMIP', 'GMMIP', 'ISMIP6',
               'LS3MIP', 'LUMIP', 'OMIP', 'PMIP', 'RFMIP', 'ScenarioMIP', 'CORDEX', 'SIMIP', 'CMIP6', 'CMIP'},
        "HR": {'OMIP', 'ScenarioMIP', 'CORDEX', 'CMIP6', 'CMIP'},
    },

    # A character string containing additional information about the models. Will be complemented
    # with the experiment's specific comment string
    "comment": "",

    # Max variable priority level to be output (you may set 3 when creating ping_files while
    # being more restrictive at run time); values in simulation_settings may override the one below
    'max_priority': 1,
    'tierMax': 1,

    # The ping file defines variable names, which are constructed using CMIP6 "MIPvarnames"
    # and a prefix which must be set here, and can be the empty string :
    "ping_variables_prefix": "CMIP6_",

    # We account for a list of variables which the lab does not want to produce ,
    # Names must match DR MIPvarnames (and **NOT** CMOR standard_names)
    # excluded_vars_file="../../cnrm/non_published_variables"
    "excluded_vars": ['pfull', 'phalf', "zfull"],  # because we have a pressure based hydrid coordinate,
    # and no fixed height levels

    # Vars computed with a period which is not the basic timestep must be declared explictly,
    # with that period, in order that 'instant' sampling works correctly
    # (the units for period should be different from the units of any instant ouput frequency
    # for those variables - 'mi' looks fine, 'ts' may work)
    "special_timestep_vars": {
        "60mi": ['parasolRefl', 'clhcalipso', 'cltcalipso', 'cllcalipso', 'clmcalipso', 'cfadLidarsr532', 'clcalipso',
                 'clcalipso2', 'cfadDbze94', 'jpdftaureliqmodis', 'clisccp', 'jpdftaureicemodis', 'clmisr'],
    },

    # You can specifically exclude some pairs (vars,tables), here in lab_settings
    # and also (in addition) in experiment_settings
    "excluded_pairs": [('fbddtalk', 'Omon')],

    # For debugging purpose, if next list has members, this has precedence over
    # 'excluded_vars' and over 'excluded_vars_per_config'
    # "included_vars" : [ 'ccb' ],

    # When atmospheric vertical coordinate implies putting psol in model-level output files, we
    # must avoid creating such file_def entries if the model does not actually send the 3D fields
    # (because this leads to files full of undefined values)
    # We choose to describe such fields as a list of vars dependant on the model configuration
    # because the DR is not in a good enough shape about realms for this purpose
    "excluded_vars_per_config": {
        "AGCM": ["ch4", "co2", "co", "concdust", "ec550aer", "h2o", "hcho", "hcl", "hno3", "mmrbc", "mmrdust", "mmroa",
                 "mmrso4", "mmrss", "n2o", "no2", "no", "o3Clim", "o3loss", "o3prod", "oh", "so2"],
        "AOGCM": ["ch4", "co2", "co", "concdust", "ec550aer", "h2o", "hcho", "hcl", "hno3", "mmrbc", "mmrdust", "mmroa",
                  "mmrso4", "mmrss", "n2o", "no2", "no", "o3Clim", "o3loss", "o3prod", "oh", "so2"],
    },
    #
    "excluded_spshapes": ["XYA-na", "XYG-na",  # GreenLand and Antarctic grids we do not want to produce
                          "na-A",  # RFMIP.OfflineRad : rld, rlu, rsd, rsu in table Efx ?????
                          "Y-P19", "Y-P39", "Y-A", "Y-na"  # Not yet handled by dr2xml
                          ],

    "excluded_tables": ["Oclim", "E1hrClimMon", "ImonAnt", "ImonGre"],  # Clims are not handled by Xios yet

    # For debugging purpose : if next list has members, only those tables will be processed
    # "included_tables"  : ["AMon" ] , # If not empty, has priority over excluded_tables

    "excluded_request_links": [
        "RFMIP-AeroIrf"  # 4 scattered days of historical, heavy output -> please rerun model for one day
        # for each day of this request_link
    ],
    # For debugging purpose : if next list has members, only those requestLinks will be processed
    "included_request_links": [],

    # We account for a default list of variables which the lab wants to produce in most cases
    # This can be changed at the experiment_settings level
    # "listof_home_vars":"../../cnrm/listof_home_vars.txt",

    # If we use extra tables, we can set it here (and supersed it in experiment settings)
    # 'path_extra_tables'=

    # Each XIOS  context does adress a number of realms
    'realms_per_context': {
        'nemo': ['seaIce', 'ocean', 'ocean seaIce', 'ocnBgchem', 'seaIce ocean'],
        'arpsfx': ['atmos', 'atmos atmosChem', 'atmosChem', 'aerosol', 'atmos land', 'land',
                   'landIce land', 'aerosol', 'land landIce', 'landIce', ],
        'trip': [],
    },
    # Some variables, while belonging to a realm, may fall in another XIOS context than the
    # context which hanldes that realm
    'orphan_variables': {
        'trip': ['dgw', 'drivw', 'fCLandToOcean', 'qgwr', 'rivi', 'rivo', 'waterDpth', 'wtd'],
    },
    # A per-variable dict of comments valid for all simulations
    'comments': {
        'rld': 'nothing special about this variable'
    },
    #
    'grid_choice': {"CNRM-CM6-1": "LR", "CNRM-CM6-1-HR": "HR",
                    "CNRM-ESM2-1": "LR", "CNRM-ESM2-1-HR": "HR"},
    # If you want to produce the same variables set for all members, set next parameter to False
    # You can anyway override this parameter in dict simulation_settings
    "filter_on_realization": True,
    # Sizes for atm and oce grids (cf DR doc); Used for computing file split frequency
    "sizes": {"LR": [292 * 362, 75, 128 * 256, 91, 30, 14, 128],
              "HR": [1442 * 1021, 75, 720 * 360, 91, 30, 14, 128]},

    # What is the maximum duration of data period in a single file (integer, in years)
    "max_split_freq": None,

    # What is the maximum size of generated files, in number of float values
    "max_file_size_in_floats": 2000. * 1.e+6,  # 2 Giga octets
    # Required NetCDF compression level
    "compression_level": 0,
    # Estimate of number of bytes per floating value, given the chosen compresssion level
    "bytes_per_float": 2.0,

    # grid_policy among None, DR, native, native+DR, adhoc- see docin grids.py
    "grid_policy": "adhoc",

    # Grids : per model resolution and per context :
    #              - CMIP6 qualifier (i.e. 'gn' or 'gr') for the main grid chosen (because you
    #                 may choose has main production grid a regular one, when the native grid is e.g. unstructured)
    #              - Xios id for the production grid (if it is not the native grid),
    #              - Xios id for the latitude axis used for zonal means (mist match latitudes for grid above)
    #              - resolution of the production grid (using CMIP6 conventions),
    #              - grid description
    "grids": {

        "LR": {
            "surfex": ["gr", "complete", "glat", "250 km",
                       "data regridded to a T127 gaussian grid (128x256 latlon)"
                       "from a native atmosphere T127l reduced gaussian grid"],
            "trip": ["gn", "", "", "50 km", "regular 1/2 deg lat-lon grid"],
            "nemo": ["gn", "", "", "100 km", "native ocean tri-polar grid with 105 k ocean cells"], },

        "HR": {
            "surfex": ["gr", "complete", "glat", "50 km",
                       "data regridded to a 359 gaussian grid (180x360 latlon)"
                       "from a native atmosphere T359l reduced gaussian grid"],
            "trip": ["gn", "", "", "50 km", "regular 1/2 deg lat-lon grid"],
            "nemo": ["gn", "", "", "25 km", "native ocean tri-polar grid with 1.47 M ocean cells"], },
    },
    # "nb_longitudes_in_model": { "surfex" :"ndlon", "nemo": "" },
    #
    # Basic sampling timestep set in your field definition (used to feed metadata 'interval_operation')
    "sampling_timestep": {
        "LR": {"surfex": 900., "nemo": 1800.},
        "HR": {"surfex": 900., "nemo": 1800.},
    },

    # CFMIP has an elaborated requirement for defining subhr frequency; by default, dr2xml uses 1 time step
    "CFsubhr_frequency": "1ts",

    # We create sampled time-variables for controlling the frequency of vertical interpolations
    "vertical_interpolation_sample_freq": "3h",
    "vertical_interpolation_operation": "instant",  # LMD prefers 'average'

    # --- Say if you want to use XIOS union/zoom axis to optimize vertical interpolation requested by the DR
    "use_union_zoom": False,

    # The CMIP6 frequencies that are unreachable for a single model run. Datafiles will
    # be labelled with dates consistent with content (but not with CMIP6 requirements).
    # Allowed values are only 'dec' and 'yr'
    "too_long_periods": ["dec", "yr"],

    # Describe the branching scheme for experiments involved in some 'branchedYears type' tslice
    # (for details, see: http://clipc-services.ceda.ac.uk/dreq/index/Slice.html )
    # Just put the as key the common start year in child and as value the list of start years in parent for all members
    "branching": {
        "CNRM-CM6-1": {"historical": (1850, [1850, 1883, 1941, 1960, 1990, 2045, 2079, 2108, 2214, 2269])},
        "CNRM-ESM2-1": {"historical": (1850, [1850, 1883, 1941])},
    },

    # We can control the max output level set for all output files,
    "output_level": 10,

    # For debug purpose, you may slim down xml files by setting next entry to False
    "print_variables": True,

    # Set that to True if you use a context named 'nemo' and the
    # corresponding model unduly sets a general freq_op AT THE
    # FIELD_DEFINITION GROUP LEVEL. Due to Xios rules for inheritance,
    # that behavior prevents inheriting specific freq_ops by reference
    # from dr2xml generated field_definitions
    "nemo_sources_management_policy_master_of_the_world": False,

    # You may add a series of NetCDF attributes in all files for this simulation
    "non_standard_attributes": {"model_minor_version": "6.1.0"},

    # If some grid is not defined in xml but by API, and is referenced by a
    # field which is considered by the DR as having a singleton dimension, then :
    #  1) it must be a grid which has only a domain
    #  2) the domain name must be extractable from the grid_id using a regexp
    #     and a group number
    # Example : using a pattern that returns full id except for a '_grid' suffix
    # "simple_domain_grid_regexp" : ("(.*)_grid$",1),

    # If your model has some axis which does not have all its attributes
    # as in DR, and you want dr2xml to fix that it, give here
    # the correspondence from model axis id to DR dim/grid id.
    # For label dimensions you should provide the list of labels, ordered
    # as in your model, as second element of a pair
    # Label-type axes will be processed even if not quoted
    # Scalar dimensions are not concerned by this feature
    'non_standard_axes': {
        # Space dimensions - Arpege :
        'klev': 'alevel', 'klev_half': 'alevel',

        # COSP
        'effectRadIc': 'effectRadIc', 'effectRadL': 'effectRadL',
        'sza5': 'sza5',
        'dbze': 'dbze',

        # Land dimensions
        'soilpools': ('soilpools', 'fast medium slow'),
        # 'landUse'      :'landUse' ,
        'vegtype': ('vegtype',
                    'Bare_soil Rock Permanent_snow Temperate_broad-leaved_decidus Boreal_needleaf_evergreen'
                    'Tropical_broad-leaved_evergreen C3_crop C4_crop Irrigated_crop C3_grass C4_grass Wetland'
                    'Tropical_broad-leaved_decidus Temperate_broad-leaved_evergreen Temperate_needleaf_evergreen'
                    'Boreal_broad-leaved_decidus Boreal_needleaf_decidus Tundra_grass Shrub'),

        # Space dimensions - Nemo
        'depthw': 'olevel', 'deptht': 'olevel', 'depthu': 'olevel', 'depthv': 'olevel',
        'j-mean': 'latitude',

        # Ocean transects and basins
        # 'oline'        :'oline' ,
        # 'siline'       :'siline',
        'basin ': ('basin', 'global_ocean atlantic_arctic_ocean indian_pacific_ocean dummy dummy'),

        # toy_cnrmcm, for oce (Note : for atm, there is adhoc code)
        'axis_oce': 'olevel', 'lat_oce': 'latitude', 'transect_axis': 'oline',
        'basin_oce_3': ('basin', 'global_ocean atlantic_arctic_ocean indian_pacific_ocean dummy dummy'),
    },

    # A smart workflow will allow you to extend a simulation during it
    # course and to complement the output files accordingly, by
    # managing the 'end date' part in filenames. You can then set next
    # setting to False (default is True)
    'dr2xml_manages_enddate': True,

    # You may provide some variables already horizontally remapped
    # to some grid (i.e. Xios domain) in external files. The varname in file
    # must match the referenced id in pingfile. Tested only for fixed fields
    'fx_from_file': {
        "areacella": {
            "complete": {
                "LR": "areacella_LR",
                "HR": "areacella_HR",
            }
        }
    },

    # The path of the directory which, at run time, contains the root XML file (iodef.xml)
    'path_to_parse': "./",

    # Should we allow for duplicate vars : two vars with same
    # frequency, shape and realm , which differ only by the table.
    # In DR01.00.21, this actually applies to very few fields (ps-Aermon,
    # tas-ImonAnt, areacellg-IfxAnt). Defaults to True
    'allow_duplicates': True,

    # Should we allow for another type of duplicate vars : two vars
    # with same name in same table (usually with different
    # shapes). This applies to e.g. CMOR vars 'ua' and 'ua7h' in
    # 6hPlevPt. Default to False, because CMIP6 rules does not allow
    # to name output files differently in that case. If set to True,
    # you should also set 'use_cmorvar_label_in_filename' to True to
    # overcome the said rule
    'allow_duplicates_in_same_table': False,

    # CMIP6 rule is that filenames includes the variable label, and
    # that this variable label is not the CMORvar label, but 'MIPvar'
    # label. This may lead to conflicts, e.g. for 'ua' and 'ua7h' in
    # table 6hPlevPt; next setting allows to avoid that, if set to True
    'use_cmorvar_label_in_filename': False,

    # DR01.00.21 does not include Gibraltar strait, which is requested by OMIP
    # Can include it, if model provides it as last value of array. Defaults to false
    'add_Gribraltar': False,

    # In order to identify which xml files generates a problem, you can use this flag
    'debug_parsing': False,

    # DR has sn attributes for MIP variables. They can be real,CF-compliant, standard_names or
    # pseudo_standard_names, i.e. not yet approved labels. Default is to use only CF ones
    'allow_pseudo_standard_names': False,

    # For an extended printout of selected CMOR variables, grouped by variable label
    'print_stats_per_var_label': False,

    # When using select='no', Xios may enter an endless loop, which is solved if next setting is False
    'allow_tos_3hr_1deg': True,

    # Some scenario experiment in DR 01.00.21 do not request tos on 1 degree grid, while other do.
    # If you use grid_policy=adhoc and had not changed the mapping of function
    # grids.lab_adhoc_grid_policy to grids.CNRM_grid_policy, next setting can force any tos request
    # to also produce tos on a 1 degree grid
    "adhoc_policy_do_add_1deg_grid_for_tos": False,

    # The variable mip_era can be defined at simulation and laboratory levels.
    # If it is not defined, it will be taken in the variable.
    # mip_era: "",
}

""" An example/template of settings for a simulation """

example_simulation_settings = {
    # Dictionnary describing the necessary attributes for a given simulation

    # Warning : some lines are commented out in this example but should be
    # un-commented in some cases. See comments

    # DR experiment name to process. See http://clipc-services.ceda.ac.uk/dreq/index/experiment.html
    "experiment_id": "historical",
    # Experiment label to use in file names and attribute, (default is experiment_id)
    # "expid_in_filename"   : "myexpe",
    # Experiment id to use for driving the use of the Data Request (default is experiment_id)
    # 'experiment_for_requests' : "piControl",

    # The variable mip_era can be defined at simulation and laboratory levels.
    # If it is not defined, it will be taken in the variable.
    # mip_era: "",

    # If there is no configuration in lab_settings which matches you case, please rather
    # use next or next two entries : source_id and, if needed, source_type
    'configuration': 'AOGCM',

    # For some experiments (e.g. concentration-driven historical in AESM config), the only way to
    # avoid producing useless fields is to explicitly exclude variables (in addition to those in lab_settings)
    'excluded_vars': [],

    # It is possible to define the list of included vars in simulation settings.
    # If it is done, it replace the list which could be defined in laboratory settings.
    'included_vars': [],

    # It can be handy to exclude some Tables at the experiment level. They are added to the lab-level set
    # "excluded_tables"  : [ ] ,

    # The included_tables can be defined at the simulation simulation.
    # In this case, it replaces the variable that could be defined at laboratory level.
    'included_tables': [],

    # 'source_id'      : "CNRM-CM6-1",
    # 'source_type'    : "OGCM" ,# If the default source-type value for your source (from lab settings)
    # does not fit, you may change it here.
    # "This should describe the model most directly responsible for the
    # output.  Sometimes it is appropriate to list two (or more) model types here, among
    # AER, AGCM, AOGCM, BGC, CHEM, ISM, LAND, OGCM, RAD, SLAB "
    # e.g. amip , run with CNRM-CM6-1, should quote "AGCM AER"
    # Also see note 14 of https://docs.google.com/document/d/1h0r8RZr_f3-8egBMMh7aqLwy3snpD6_MrDz1q8n5XUk/edit

    # "contact"        : "", set it only if it is specific to the simualtion
    # "project"        : "CMIP6",  #CMIP6 is the default

    # 'max_priority' : 1,  # a simulation may be run with a max_priority which overrides the one in lab_settings
    # 'tierMax'      : 1,  # a simulation may be run with a Tiermax overrides the one in lab_settings

    # It is recommended that some description be included to help
    # identify major differences among variants, but care should be
    # taken to record correct information.  dr2xml will add in all cases:
    #  'Information provided by this attribute may in some cases be
    #  flawed. Users can find more comprehensive and up-to-date
    #  documentation via the further_info_url global attribute.'
    "variant_info": "Start date after 300 years of control run",
    #
    "realization_index": 1,  # Value may be omitted if = 1
    "initialization_index": 1,  # Value may be omitted if = 1
    "physics_index": 1,  # Value may be omitted if = 1
    "forcing_index": 3,  # Value may be omitted if = 1
    #
    # If you want to produce the same variables set for all members, set next parameter to False
    # This value does override the value for same parameter in lab_settings
    # "filter_on_realization" : True,
    #
    # All about the branching scheme from parent
    "branch_method": "standard",  # default value='standard' meaning ~ "select a start date"
    # (this is not necessarily the parent start date)
    'parent_time_ref_year': 1850,  # MUST BE CONSISTENT WITH THE TIME UNITS OF YOUR MODEL(S) !!!
    "branch_year_in_parent": 2150,  # if your calendar is Gregorian, you can specify the branch year in parent directly
    # This is an alternative to using "branch_time_in_parent".
    # "branch_month_in_parent": 1,        # You can then also set the month. Default to 1
    # "branch_time_in_parent": "365.0D0", # a double precision value, in days, used if branch_year_in_parent
    #                                     # is not applicable
    # This is an alternative to using "branch_year_in_parent"
    # 'parent_time_units'    : "" #in case it is not the same as child time units

    # In some instances, the experiment start year is not explicit or is doubtful in DR. See
    # file doc/some_experiments_starty_in_DR01.00.21. You should then specifiy it, using next setting
    # in order that requestItems analysis work in all cases

    # In some other cases, DR requestItems which apply to the experiment form its start does not
    # cover its whole duration and have a wrong duration (computed based on a wrong start year);
    # They necessitate to fix the start year
    # 'branch_year_in_child' : 1950,

    # If you want to carry on the experiment beyond the duration set in DR, and that all
    # requestItems that apply to DR end year also apply later on, set 'end_year'
    # You can also set it if you don't know if DR has a wrong value
    # 'end_year' : 2014,

    'child_time_ref_year': 1850,  # MUST BE CONSISTENT WITH THE TIME UNITS OF YOUR MODEL(S) !!!
    # (this is not necessarily the parent start date)
    # the ref_year for a scenario must be the same as for the historical
    # "branch_time_in_child" : "0.0D0",   # a double precision value in child time units (days),
    # This is an alternative to using "branch_year_in_child"

    # 'parent_variant_label' :""  #Default to 'same variant as child'. Other cases should be exceptional
    # "parent_mip_era"       : 'CMIP5'   # only in special cases (as e.g. PMIP warm
    # start from CMIP5/PMIP3 experiment)
    # 'parent_source_id'     : 'CNRM-CM5.1' # only in special cases, where parent model
    # is not the same model
    #
    "sub_experiment_id": "None",  # Optional, default is 'none'; example : s1960.
    "sub_experiment": "None",  # Optional, default in 'none'
    "history": "None",  # Used when a simulation is re-run, an output file is modified ...

    # A character string containing additional information about this simulation
    "comment": "",

    # You can specifically exclude some pairs (vars,tables), here in experiment settings
    # They wil be added to the lab-settings list of excluded pairs
    # "excluded_pairs" : [ ('fbddtalk','Omon') ]

    # A per-variable dict of comments which are specific to this simulation. It will replace
    # the all-simulation comment
    'comments': {
        'tas': 'this is a dummy comment, placeholder for describing a special, '
               'simulation dependent, scheme for a given variable',
    },
    # We can supersede the default list of variables of lab_settings, which tells
    # which additionnal variables/frequecny are to produce
    # "listof_home_vars":"../../cnrm/home_vars_historical.txt",

    # If we use extra tables, we can here supersede the value set it in lab settings
    # 'path_extra_tables'=

    # If the CMIP6 Controlled Vocabulary doesn't allow all the components you activate, you can set
    # next toggle to True
    'bypass_CV_components': False,

    # What is the maximum duration of data period in a single file, for this experiment (integer, in years)
    "max_split_freq": None,

    'unused_contexts': [],  # If you havn't set a 'configuration', you may fine tune here
    # perso_sdims_description variable should be a dictionnary which described each element of the
    # custom sdim shape
    'perso_sdims_description': {},
}


def generate_file_defs(lset, sset, year, enddate, context, cvs_path, pingfiles=None,
                       dummies='include', printout=False, dirname="./", prefix="", attributes=list(),
                       select="on_expt_and_year"):
    """
    A wrapper for profiling top-level function : generate_file_defs_inner
    """
    debug = False
    if debug:
        default_level = "debug"
    elif printout:
        default_level = "info"
    else:
        default_level = "warning"
    initialize_logger(default=True, level=default_level)
    # pr = cProfile.Profile()
    # pr.enable()
    # Initialize lset and sset variables for all functions
    initialize_config_variables()
    initialize_dict(lset, sset)
    generate_file_defs_inner(lset, sset, year, enddate, context, cvs_path, pingfiles=pingfiles,
                             dummies=dummies, dirname=dirname,
                             prefix=prefix, attributes=attributes, select=select)
    # pr.disable()
    # if python_version == "python2":
    #     s = io.BytesIO()
    # else:
    #     s = io.StringIO()
    # sortby = 'cumulative'
    # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    # ps.print_stats()
    # Just un-comment next line to get the profile on stdout
    # print s.getvalue()


def generate_file_defs_inner(lset, sset, year, enddate, context, cvs_path, pingfiles=None,
                             dummies='include', dirname="./", prefix="",
                             attributes=list(), select="on_expt_and_year"):
    """
    Using the DR module, a dict of lab settings ``lset``, and a dict
    of simulation settings ``sset``, generate an XIOS file_defs 'file' for a
    given XIOS ``context``, which content matches
    the DR for the experiment quoted in simu setting dict and a ``year``.

    Structure of the two dicts is documented elsewhere. It includes the
    correspondance between a context and a few realms

    :param dict lset: dictionary of laboratory settings
    :param dict sset: dictionary of simulation settings
    :param int year: year considered for the launch
    :param six.string_types enddate: enddate of the simulation
    :param six.string_types context: XIOS context considered for the launch
    :param six.string_types cvs_path: path to controlled vocabulary to be used
    :param six.string_types pingfiles: files which are analysed to find variables with a different name between model
                                       and Data Request
    :param six.string_types dummies: specify how to treat dummy variables among:

        - "include": include dummy refs in file_def (useful for demonstration run)
        - "skip": don't write field with a ref to a dummy (useful until ping_file is fully completed)
        - "forbid": stop if any dummy (useful for production run)

    :param bool printout: print infos
    :param six.string_types dirname: directory in which outputs will be created
    :param six.string_types prefix: prefix used for each file definition
    :param list attributes: list of (name,value) pairs which are to be inserted as
                            additional file-level attributes. They are complemented with entry
                            "non_standard__attributes" of dict sset
    :param six.string_types select: make variable selection according to a criteria:

        - "on_expt_and_year" or "": select output variables according to the year simulated and the experiment done
        - "on_expt": select output variables according to the experiment done only
        - "no": no selection of output variables

    :return: An output file named dirname/filedefs_context.xml. It has a CMIP6 compliant name, with prepended prefix.

    """
    logger = get_logger()
    #
    cmvk = "CMIP6_CV_version"
    if cmvk in attributes:
        logger.info("* %s: %s" % (cmvk, attributes[cmvk]))
    # --------------------------------------------------------------------
    # Parse XIOS settings file for the context
    # --------------------------------------------------------------------
    print()
    print(50 * "*")
    print()
    print("Processing context ", context)
    print()
    print(50 * "*")
    print()
    default_log_level = logger.level
    if get_variable_from_lset_with_default("debug_parsing", False):
        change_log_level("debug")
    set_config_variable("context_index",
                        init_context(context, get_variable_from_lset_with_default("path_to_parse", "./")))
    if get_variable_from_lset_with_default("debug_parsing", False):
        change_log_level(default_log_level)
    if get_config_variable("context_index") is None:
        logger.error("Variable 'context_index' is not set.")
        sys.exit(1)
    set_config_variable("cell_method_warnings", list())
    warnings_for_optimisation = list()
    initialize_sn_issues(OrderedDict())
    #
    # --------------------------------------------------------------------
    # Select variables that should be processed
    # --------------------------------------------------------------------
    skipped_vars_per_table = OrderedDict()
    actually_written_vars = list()
    svars_per_table = select_variables_to_be_processed(year, context, select)
    #
    # --------------------------------------------------------------------
    # Read ping_file defined variables
    # --------------------------------------------------------------------
    pingvars, all_ping_refs = read_pingfiles_variables(pingfiles, dummies)
    #
    field_defs = OrderedDict()
    axis_defs = OrderedDict()
    grid_defs = OrderedDict()
    file_defs = OrderedDict()
    scalar_defs = OrderedDict()
    #
    # --------------------------------------------------------------------
    # Build all plev union axis and grids
    # --------------------------------------------------------------------
    if get_variable_from_lset_with_default('use_union_zoom', False):
        svars_full_list = list()
        for svl in svars_per_table.values():
            svars_full_list.extend(svl)
        create_xios_axis_and_grids_for_plevs_unions(svars_full_list, multi_plev_suffixes.union(single_plev_suffixes),
                                                    dummies, axis_defs, grid_defs, field_defs, all_ping_refs)
    #
    # --------------------------------------------------------------------
    # Write XIOS file_def
    # --------------------------------------------------------------------
    # filename=dirname+"filedefs_%s.xml"%context
    filename = dirname + "dr2xml_%s.xml" % context
    write_xios_file_def(filename, svars_per_table, year, lset, sset, cvs_path, field_defs, axis_defs, grid_defs,
                        scalar_defs, file_defs, dummies, skipped_vars_per_table, actually_written_vars, prefix, context,
                        pingvars, enddate, attributes)
    logger.info("\nfile_def written as %s" % filename)

    #
    # --------------------------------------------------------------------
    # Print infos about the run
    # --------------------------------------------------------------------
    # mpmoine_petitplus:generate_file_defs: pour sortir des stats sur ce que l'on sort reelement
    # SS - non : gros plus
    print_some_stats(context, svars_per_table, skipped_vars_per_table,
                     actually_written_vars, get_variable_from_lset_with_default("print_stats_per_var_label", False))

    warn = OrderedDict()
    for warning, label, table in get_config_variable("cell_method_warnings"):
        if warning not in warn:
            warn[warning] = set()
        warn[warning].add(label)
    if len(warn) > 0:
        logger.warning("\nWarnings about cell methods (with var list)")
        for w in warn:
            logger.warning("\t", w, " for vars : ", print_struct(warn[w]))
    if len(warnings_for_optimisation) > 0:
        logger.warning("Warning for fields which cannot be optimised (i.e. average before remap) because of an expr with @\n\t",)
        for w in warnings_for_optimisation:
            logger.warning(w.replace(get_variable_from_lset_without_default('ping_variables_prefix'), ""),)
        print()


def request_item_include(ri, var_label, freq):
    """
    test if a variable is requested by a requestItem at a given freq
    """
    var_group = get_uid(get_uid(ri.rlid).refid)
    req_vars = get_request_by_id_by_sect(var_group.uid, 'requestVar')
    cm_vars = [get_uid(get_uid(reqvar).vid) for reqvar in req_vars]
    return any([cmv.label == var_label and cmv.frequency == freq for cmv in cm_vars])


def realm_is_processed(realm, source_type):
    """
    Tells if a realm is definitely not processed by a source type

    list of source-types : AGCM BGC AER CHEM LAND OGCM AOGCM
    list of known realms : 'seaIce', '', 'land', 'atmos atmosChem', 'landIce', 'ocean seaIce',
                           'landIce land', 'ocean', 'atmosChem', 'seaIce ocean', 'atmos',
                           'aerosol', 'atmos land', 'land landIce', 'ocnBgChem'
    """
    components = source_type.split(" ")
    rep = True
    #
    if realm == "atmosChem" and 'CHEM' not in components:
        return False
    if realm == "aerosol" and 'AER' not in components:
        return False
    if realm == "ocnBgChem" and 'BGC' not in components:
        return False
    #
    with_ocean = ('OGCM' in components or 'AOGCM' in components)
    if 'seaIce' in realm and not with_ocean:
        return False
    if 'ocean' in realm and not with_ocean:
        return False
    #
    with_atmos = ('AGCM' in components or 'AOGCM' in components)
    if 'atmos' in realm and not with_atmos:
        return False
    if 'atmosChem' in realm and not with_atmos:
        return False
    if realm == '' and not with_atmos:  # In DR 01.00.15 : some atmos variables have realm=''
        return False
    #
    with_land = with_atmos or ('LAND' in components)
    if 'land' in realm and not with_land:
        return False
    #
    return rep


