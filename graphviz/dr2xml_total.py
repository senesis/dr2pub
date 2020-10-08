#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
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

First version (0.8) : S.Sénési (CNRM) - sept 2016

Changes :
  oct 2016 - Marie-Pierre Moine (CERFACS) - handle 'home' Data Request
                               in addition
  dec 2016 - S.Sénési (CNRM) - improve robustness
  jan 2017 - S.Sénési (CNRM) - handle split_freq; go single-var files;
                               adapt to new DRS ...
  feb 2017 - S.Sénési (CNRM) - handle grids and remapping;
                               put some func in separate module

"""
####################################
# Pre-requisites
####################################

# 1- CMIP6 Data Request package retrieved using
#    svn co http://proj.badc.rl.ac.uk/svn/exarch/CMIP6dreq/tags/01.00.01
#    (and must include 01.00.01/dreqPy in PYTHONPATH)
from scope import dreqQuery
import dreq

# 2- CMIP6 Controled Vocabulary (available from
# https://github.com/WCRP-CMIP/CMIP6_CVs). You will provide its path
# as argument to functions defined here

# 3- XIOS release must be 1047 or above (to be fed with the outputs)
#  see https://forge.ipsl.jussieu.fr/ioserver/wiki

####################################
# End of pre-requisites
####################################
version = "mpmoine-dev3 = mpmoine-dev2 merged with senesi-dev-v0.12 + updates untill 05/05/2017"
print "* dr2xml version:", version

from datetime import datetime
import re
import json
import collections
import sys, os
import xml.etree.ElementTree as ET

# mpmoine_merge_dev2_v0.12: posixpath.dirname ne marche pas chez moi
# TBS# from os import path as os_path
# TBS# prog_path=os_path.abspath(os_path.split(__file__)[0])

# Local packages
# mpmoine_zoom_modif: import simple_Dim
# GRAPHVIZ#from vars import simple_CMORvar, simple_Dim, process_home_vars, complement_svar_using_cmorvar, \
# GRAPHVIZ#                multi_plev_suffixes, single_plev_suffixes
# GRAPHVIZ#from grids import decide_for_grids, grid2resol, grid2desc, field_size,\
# GRAPHVIZ#    split_frequency_for_variable, timesteps_per_freq_and_duration
# GRAPHVIZ#from Xparse import init_context, id2grid

# A local auxilliary table
# mpmoine_last_modif: dr2xml.py: ajout import de cmipFreq2xiosFreq
# GRAPHVIZ#from table2freq import table2freq, table2splitfreq, cmipFreq2xiosFreq

# GRAPHVIZ#from dr2cmip6_expname import dr2cmip6_expname

print_DR_errors = True

dq = dreq.loadDreq()
print "* CMIP6 Data Request version: ", dq.version

context_index = None

""" An example/template  of settings for a lab and a model"""
example_lab_and_model_settings = {
    'institution_id': "CNRM-CERFACS",  # institution should be read in CMIP6_CV, if up-to-date
    'source_id': "CNRM-CM6-1",
    # The description of lab models, in CMIP6 CV wording
    'source_types': {"CNRM-CM6-1": "AOGCM", "CNRM-CM6-1-HR": "AOGCM",
                     "CNRM-ESM2-1": "ESM", "CNRM-ESM2-1-HR": "ESM"},
    'source': "CNRM-CM6-1",  # Useful only if CMIP6_CV is not up to date
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
    'mips': {'AerChemMIP', 'C4MIP', 'CFMIP', 'DAMIP', 'FAFMIP', 'GeoMIP', 'GMMIP', 'ISMIP6', \
             'LS3MIP', 'LUMIP', 'OMIP', 'PMIP', 'RFMIP', 'ScenarioMIP', 'CORDEX', 'SIMIP'},
    # Max variable priority level to be output
    'max_priority': 1,
    'tierMax': 1,

    # The ping file defines variable names, which are constructed using CMIP6 "MIPvarnames"
    # and a prefix which must be set here, and can be the empty string :
    "ping_variables_prefix": "CMIP6_",

    # We account for a list of variables which the lab does not want to produce ,
    # Names must match DR MIPvarnames (and **NOT** CF standard_names)
    # excluded_vars_file="../../cnrm/non_published_variables"
    "excluded_vars": [],

    # We account for a list of variables which the lab wants to produce in some cases
    "listof_home_vars": "../../cnrm/listof_home_vars.txt",

    # Each XIOS  context does adress a number of realms
    'realms_per_context': {
        'nemo': ['seaIce', 'ocean', 'ocean seaIce', 'ocnBgchem', 'seaIce ocean'],
        'arpsfx': ['atmos', 'atmos atmosChem', 'aerosol', 'atmos land', 'land',
                   'landIce land', 'aerosol land', 'land landIce', 'landIce', ],
    },
    # Some variables, while belonging to a realm, may fall in another XIOS context than the
    # context which hanldes that realm
    'orphan_variables': {'nemo': ['dummy_variable_for_illustration_purpose'],
                         ' arpsfx': [],
                         },
    'vars_OK': dict(),
    # A per-variable dict of comments valid for all simulations
    'comments': {
        'tas': 'nothing special about tas'
    },
    # Sizes for atm and oce grids (cf DR doc)
    "sizes": [259200, 60, 64800, 40, 20, 5, 100],
    # What is the maximum size of generated files, in number of float values
    "max_file_size_in_floats": 500. * 1.e+6,
    # grid_policy among None, DR, native, native+DR, adhoc- see docin grids.py
    "grid_policy": "adhoc",
    # Grids : CMIP6 name, name_of_target_domain, CMIP6-std resolution, and description
    "grids": {
        "LR": {
            "arpsfx": ["gr", "complete", "250 km",
                       "data regridded to a T127 gaussian grid (128x256 latlon) from a native atmosphere T127l reduced gaussian grid"],
            "nemo": ["gn", "", "100km", "native ocean tri-polar grid with 105 k ocean cells"], },
        "HR": {
            "arpsfx": ["gr", "completeHR", "50 km",
                       "data regridded to a 359 gaussian grid (180x360 latlon) from a native atmosphere T359l reduced gaussian grid"],
            "nemo": ["gn", "", "25km", "native ocean tri-polar grid with 1.47 M ocean cells"], },
    },
    'grid_choice': {"CNRM-CM6-1": "LR", "CNRM-CM6-1-HR": "HR",
                    "CNRM-ESM2-1": "LR", "CNRM-ESM2-1-HR": "HR"},

}

""" An example/template of settings for a simulation """

example_simulation_settings = {
    # Dictionnary describing the necessary attributes for a given simulation

    # Warning : some lines are commented out in this example but should be
    # un-commented in some cases. See comments

    "experiment_id": "historical",
    # "contact"        : "", set it only if it is specific to the simualtion
    # "project"        : "CMIP6",  #CMIP6 is the default

    # 'source_type'    : "ESM" # If source_type deduced from model name is not relevant for this
    # experiment (e.g. : AMIP), you may tell that here

    # MIPs specifying the experiment. For historical, it is CMIP
    # itself In a few cases it may be appropriate to include multiple
    # activities in the activity_id (separated by single spaces).
    # An example of this is 'LUMIP AerChemMIP' for one of the land-use change experiments.
    "activity_id": "CMIP",  # examples : "PMIP", 'LS3MIP LUMIP'; defaults to "CMIP"

    # It is recommended that some description be included to help
    # identify major differences among variants, but care should be
    # taken to record correct information.  Prudence dictates that
    # this attribute includes a warning along the following lines:
    # 'Information provided by this attribute may in some cases be
    # flawed.# Users can find more comprehensive and up-to-date
    # documentation via the further_info_url global attribute.'
    "variant_info": "Start date chosen so that variant r1i1p1f1 has " + \
                    "the better fit with Krakatoa impact on tos",
    #
    "realization_index": 1,  # Value may be omitted if = 1
    "initialization_index": 1,  # Value may be omitted if = 1
    "physics_index": 1,  # Value may be omitted if = 1
    "forcing_index": 1,  # Value may be omitted if = 1
    #
    # All about the parent experiment and branching scheme
    "parent_experiment_id": "piControl",  # omit or set to 'no parent' if not applicable
    # (remaining parent attributes will be disregarded)
    "branch_method": "standard",  # default value='standard' meaning ~ "select a start date"
    "branch_time_in_child": "0.0D0",  # a double precision value in child time units (days), used if applicable
    "branch_time_in_parent": "365.0D0",  # a double precision value, in days, used if applicable
    'parent_time_ref_year': 1850,  # default=1850.
    # 'parent_variant_label' :""  #Default to 'same as child'. Other cases should be exceptional
    # "parent_mip_era"       : 'CMIP5'   # only in special cases (as e.g. PMIP warm
    # start from CMIP5/PMIP3 experiment)
    # 'parent_activity_id'   : 'CMIP'    # only in special cases, defaults to CMIP
    # 'parent_source_id'     : 'CNRM-CM5.1' # only in special cases, where parent model
    # is not the same model
    #
    "sub_experiment_id": "None",  # Optional, default is 'none'; example : s1960.
    "sub_experiment": "None",  # Optional, default in 'none'
    "history": "None",  # Used when a simulation is re-run, an output file is modified ...
    # A per-variable dict of comments which are specific to this simulation. It will replace
    # the all-simulation comment
    'comments': {
        'tas': 'tas diagnostic uses a special scheme in this simulation : .....',
    }
}


# def hasCMORVarName(hmvar):
#    for cmvar in dq.coll['CMORvar'].items:
#        if (cmvar.label==hmvar.label): return True

def RequestItem_applies_for_exp_and_year(ri, experiment, year, debug=False):
    """
    Returns True if requestItem 'ri' in data request 'dq' (global) is relevant
    for a given 'experiment' and 'year'. Toggle 'debug' allow some printouts
    """
    # Acces experiment or experiment group for the RequestItem
    if (debug): print "Checking ", "% 15s" % ri.label,
    item_exp = dq.inx.uid[ri.esid]
    relevant = False
    exps = dq.coll['experiment'].items
    # esid can link to an experiment or an experiment group
    if item_exp._h.label == 'experiment':
        if (debug): print "%20s" % "Simple Expt case", item_exp.label,
        if item_exp.label == experiment:
            if (debug): print " OK",
            relevant = True
    elif item_exp._h.label == 'exptgroup':
        if (debug): print "%20s" % "Expt Group case ", item_exp.label,
        group_id = ri.esid
        for e in exps:
            if 'egid' in dir(e) and e.egid == group_id and \
                    e.label == experiment:
                if (debug):  print " OK for experiment based on group" + \
                                   group_id.label,
                relevant = True
    elif item_exp._h.label == 'mip':
        mip_id = ri.esid
        if (debug): print "%20s" % "Mip case ", dq.inx.uid[mip_id].label,
        for e in exps:
            if 'mip' in dir(e) and e.mip == mip_id:
                if (debug):  print e.label, ",",
                if e.label == experiment:
                    if (debug):  print " OK for experiment based on mip" + \
                                       mip_id.label,
                    relevant = True
    else:
        if (debug):
            print "%20s" % 'Error %s for %s' % (item_exp._h.label, `ri`)
        # raise(dr2xml_error("%20s"%'Other case , label=%s|'%item_exp._h.label))
    if relevant:
        if 'tslice' in ri.__dict__:
            if ri.tslice == '__unset__':
                print "tslice is unset for reqlink %s " % ri.title
                relevant = True
            else:
                timeslice = dq.inx.uid[ri.tslice]
                if (debug): print "OK for the year"
                try:
                    relevant = year >= timeslice.start and year <= timeslice.end
                except:
                    relevant = True
                    print "tslice not well set for " + timeslice.label + " " + \
                          timeslice.uid + \
                          ". Assuming it applies for RequestItem " + ri.title
        else:
            if (debug): print "tslice not set -> OK for the year"
            # print "No tslice for %s"%ri.title
            relevant = True
    return relevant


def select_CMORvars_for_lab(lset, experiment_id=None, year=None, printout=False):
    """
    A function to list CMOR variables relevant for a lab (and also,
    optionnally for an experiment and a year)

    Args:
      lset (dict): laboratory settings; used to provide the list of MIPS,
                   the max Tier, and a list of excluded variable names
      experiment_id (string,optional): if willing to filter on a given
                   experiment - not used if year is None
      year (int,optional) : simulation year - used to filter the request
                   for an experiment and a year

    Returns:
      A list of 'simplified CMOR variables'

    """
    #
    # From MIPS set to Request links
    global sc
    sc = dreqQuery(dq=dq, tierMax=lset['tierMax'])

    # Set sizes for lab settings, if available (or use CNRM-CM6-1 defaults)
    mcfg = collections.namedtuple('mcfg', \
                                  ['nho', 'nlo', 'nha', 'nla', 'nlas', 'nls', 'nh1'])
    sizes = lset.get("sizes", [259200, 60, 64800, 40, 20, 5, 100])
    sc.mcfg = mcfg._make(sizes)._asdict()
    #
    rls_for_mips = sc.getRequestLinkByMip(lset['mips'])
    if printout:
        print "Number of Request Links which apply to MIPS",
        print lset['mips'], " is: ", len(rls_for_mips)
    #
    if (year):
        filtered_rls = []
        for rl in rls_for_mips:
            # Access all requesItems ids which refer to this RequestLink
            ri_ids = dq.inx.iref_by_sect[rl.uid].a['requestItem']
            for ri_id in ri_ids:
                ri = dq.inx.uid[ri_id]
                # print "Checking requestItem ",ri.label
                if RequestItem_applies_for_exp_and_year(ri,
                                                        experiment_id, year, False):
                    # print "% 25s"%ri.label," applies "
                    filtered_rls.append(rl)
        rls = filtered_rls
        if printout:
            print "Number of Request Links which apply to experiment ", \
                experiment_id, "and MIPs", lset['mips'], " is: ", len(rls)
    else:
        rls = rls_for_mips

    # From Request links to CMOR vars + grid
    # miprl_ids=[ rl.uid for rl in rls ]
    # miprl_vars=sc.varsByRql(miprl_ids, pmax=lset['max_priority'])
    miprl_vars_grids = []
    for rl in rls:
        rl_vars = sc.varsByRql([rl.uid], pmax=lset['max_priority'])
        for v in rl_vars:
            if (v, rl.grid) not in miprl_vars_grids:
                miprl_vars_grids.append((v, rl.grid))
    if printout:
        print 'Number of (CMOR variable, grid) pairs for these requestLinks is :%s' % len(miprl_vars_grids)
    #
    filtered_vars = []
    for (v, g) in miprl_vars_grids:
        cmvar = dq.inx.uid[v]
        mipvar = dq.inx.uid[cmvar.vid]
        if mipvar.label not in lset['excluded_vars']:
            filtered_vars.append((v, g))
    if printout:
        print 'Number once filtered by excluded vars is : %s' % len(filtered_vars)

    # Filter the list of grids requested for each variable based on lab policy
    d = dict()
    for (v, g) in filtered_vars:
        if v not in d: d[v] = set()
        d[v].add(g)
    if printout:
        print 'Number of distinct CMOR variables (whatever the grid) : %d' % len(d)
    for v in d:
        d[v] = decide_for_grids(v, d[v], lset, dq)
        if False and printout and len(d[v]) > 1:
            print "\tVariable %s will be processed with multiple grids : %s" % (dq.inx.uid[v].label, `d[v]`)
    #
    # Print a count of distinct var labels
    if printout:
        varlabels = set()
        for v in d: varlabels.add(dq.inx.uid[v].label)
        print 'Number of distinct var labels is :', len(varlabels)

    # Translate CMORvars to a list of simplified CMORvar objects
    simplified_vars = []
    for v in d:
        svar = simple_CMORvar()
        cmvar = dq.inx.uid[v]
        complement_svar_using_cmorvar(svar, cmvar, dq)
        svar.Priority = analyze_priority(cmvar, lset['mips'])
        svar.grids = d[v]
        simplified_vars.append(svar)
    print '\nNumber of simplified vars is :', len(simplified_vars)
    return simplified_vars


def analyze_priority(cmvar, lmips):
    """
    Returns the max priority of the CMOR variable, for a set of mips
    """
    prio = cmvar.defaultPriority
    rv_ids = dq.inx.iref_by_sect[cmvar.uid].a['requestVar']
    for rv_id in rv_ids:
        rv = dq.inx.uid[rv_id]
        vg = dq.inx.uid[rv.vgid]
        if vg.mip in lmips:
            if rv.priority < prio: prio = rv.priority
    return prio


# mpmoine_last_modif:wr: ajout de l'argument num_type
# mpmoine_zoom_modif:wr: ajout de l'argument out (car fonction remontee d un niveau)
def wr(out, key, dic_or_val=None, num_type="string", default=None):
    """
    Short cut for a repetitive pattern : writing in 'out'
    a string variable name and value
    If dic_or_val is not None
      if  dic_or_val is a dict,
        if key is in value is dic_or_val[key],
        otherwise use default as value , except if default is False
      otherwise, use arg dic_or_val as value if not None nor False,
    otherwise use value of local variable 'key'
    """
    val = None
    if type(dic_or_val) == type({}):
        if key in dic_or_val:
            val = dic_or_val[key]
        else:
            if default is not None:
                if default is not False: val = default
            else:
                print 'error : %s not in dic and default is None' % key
    else:
        if dic_or_val is not None:
            val = dic_or_val
        else:
            print 'error in wr,  no value provided for %s' % key
    if val:
        out.write('  <variable name="%s"  type="%s" > %s ' % (key, num_type, val))
        out.write('  </variable>\n')


# mpmoine_WIP_update: WIP doc v6.2.3 - Apr. 2017: <time_range> format is frequency-dependant => new function 'freq2datefmt'
def freq2datefmt(freq):
    datefmt = False
    if freq in ["yr", "decadal"]:
        datefmt = "%y"
    elif freq in ["mon", "monClim"]:
        datefmt = "%y%mo"
    elif freq == "day":
        datefmt = "%y%mo%d"
    # mpmoine_TBD: supprimer "hr" selon reponse de D. Nadeau a l'issue https://github.com/PCMDI/cmip6-cmor-tables/issues/59
    elif freq in ["6hr", "3hr", "3hrClim", "1hr", "hr", "1hrClimMon"]:
        datefmt = "%y%mo%d%h%mi"
    elif freq == "subhr":
        datefmt = "%y%mo%d%h%mi%s"
    elif freq == "fx":
        pass  ## WIP doc v6.2.3 - Apr. 2017: if frequency="fx", [_<time_range>] is ommitted
    return datefmt


def write_xios_file_def(cmv, table, lset, sset, out, cvspath,
                        field_defs, axis_defs, grid_defs, domain_defs,
                        dummies, skipped_vars_per_table,
                        prefix, context, grid, pingvars=None):
    """
    Generate an XIOS file_def entry in out for :
      - a dict for laboratory settings
      - a dict of simulation settings
      - a 'simplifed CMORvar' cmv
      - which all belong to given table
      - a path 'cvs' for Controlled Vocabulary

    Lenghty code, but not longer than the corresponding specification document

    After a prologue, attributes valid for all variables are
    written as file-level metadata, in the same order than in
    WIP document; last, field-level metadate are written
    """
    #
    global sc

    # mpmoine_amelioration:write_xios_file_def_for_svar: gestion ici des attributs pour lesquels on a recupere des chaines vides (" " est Faux mais est ecrit " "")
    # --------------------------------------------------------------------
    # Set to NOT-SET field attributes that can be empty strings
    # --------------------------------------------------------------------
    if not cmv.stdname: cmv.stdname = "DR-ISSUE"
    if not cmv.long_name: cmv.long_name = "DR-ISSUE"
    if not cmv.cell_methods: cmv.cell_methods = "DR-ISSUE"
    if not cmv.cell_measures: cmv.cell_measures = "DR-ISSUE"
    if not cmv.stdunits: cmv.stdunits = "DR-ISSUE"

    # --------------------------------------------------------------------
    # Define alias for field_ref in file-def file
    # - may be replaced by alias1 later
    # - this is not necessarily the alias used in ping file because of
    #   intermediate field id(s) due to union/zoom
    # --------------------------------------------------------------------
    # We use a simple convention for variable names in ping files :
    if cmv.type == 'perso':
        alias = cmv.label
    else:
        # mpmoine_correction:write_xios_file_def_for_svar: si on a defini un label non ambigu alors on l'untilise comme alias (i.e. le field_ref)
        # mpmoine_correction:write_xios_file_def_for_svar: et pour l'alias seulement (le nom de variable dans le nom de fichier restant svar.label)
        if cmv.label_non_ambiguous:
            alias = lset["ping_variables_prefix"] + cmv.label_non_ambiguous
        else:
            alias = lset["ping_variables_prefix"] + cmv.label
        # mpmoine_correction:write_xios_file_def_for_svar: suppression des terminaisons en "Clim" pour l'alias (i.e. le field_ref) le cas echeant
        split_alias = alias.split("Clim")
        alias = split_alias[0]
        if pingvars is not None:
            # mpmoine_zoom_modif:write_xios_file_def_for_svar: dans le pingfile, on attend plus les alias complets  des variables (CMIP6_<label>) mais les alias reduits (CMIP6_<lwps>)
            # mpmoine_zoom_modif:write_xios_file_def_for_svar: => creation de alias_ping
            # mpmoine_correction:write_xios_file_def_for_svar: si on a defini un label non ambigu alors on l'untilise comme ping_alias (i.e. le field_ref)
            if cmv.label_non_ambiguous:
                alias_ping = lset[
                                 "ping_variables_prefix"] + cmv.label_non_ambiguous  # e.g. 'CMIP6_tsn_land' and not 'CMIP6_tsn'
            else:
                alias_ping = lset[
                                 "ping_variables_prefix"] + cmv.label_without_psuffix  # e.g. 'CMIP6_hus' and not 'CMIP6_hus7h'
            if not alias_ping in pingvars:
                # mpmoine_skipped_modif: write_xios_file_def_for_svar: on classe les skipped_vars par table => skipped_vars_per_table (pour avoir plus d'info au print)
                if skipped_vars_per_table.has_key(cmv.mipTable) and skipped_vars_per_table[cmv.mipTable]:
                    list_of_skipped = skipped_vars_per_table[cmv.mipTable]
                    list_of_skipped.append(cmv.label + "(" + str(cmv.Priority) + ")")
                else:
                    list_of_skipped = [cmv.label]
                skipped_vars_per_table.update({cmv.mipTable: list_of_skipped})
                return
    #
    # --------------------------------------------------------------------
    # Set global CMOR file attributes
    # --------------------------------------------------------------------
    #
    project = sset.get('project', "CMIP6")
    source_id = lset['source_id']
    experiment_id = sset['experiment_id']
    institution_id = lset['institution_id']
    #
    contact = sset.get('contact', lset.get('contact', None))
    conventions = "CF-1.7 CMIP-6.0"
    #
    # Variant matters
    realization_index = sset.get('realization_index', 1)
    initialization_index = sset.get('initialization_index', 1)
    physics_index = sset.get('physics_index', 1)
    forcing_index = sset.get('forcing_index', 1)
    variant_label = "r%di%dp%df%d" % (realization_index, initialization_index, \
                                      physics_index, forcing_index)
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: cf recommendation in note 16 for 'variant_info'
    variant_info_warning = ". Information provided by this attribute may in some cases be flawed. " + \
                           "Users can find more comprehensive and up-to-date documentation via the further_info_url global attribute."
    #
    # WIP Draft 14 july 2016
    activity_id = sset.get('activity_id', 'CMIP')
    # mpmoine_last_modif:write_xios_file_def_for_svar: mip_era n'est plus toujours 'CMIP6' (par ex. 'PRIMAVERA')
    mip_era = cmv.mip_era
    #
    # WIP doc v 6.2.0 - dec 2016
    # <variable_id>_<table_id>_<source_id>_<experiment_id >_<member_id>_<grid_label>[_<time_range>].nc
    member_id = variant_label
    # mpmoine_cmor_update:write_xios_file_def_for_svar: CMOR3.2.2 impose 'None' (et non 'none') comme default value de sub_experiment_id
    # mpmoine_cmor_update:write_xios_file_def_for_svar: CMOR3.2.3 impose 'none'(et non 'None' !) comme default value de sub_experiment_id
    sub_experiment_id = sset.get('sub_experiment_id', 'none')
    if sub_experiment_id != 'none': member_id = sub_experiment_id + "-" + member_id
    #
    # --------------------------------------------------------------------
    # Set grid info
    # --------------------------------------------------------------------
    if grid == "":
        # either native or close-to-native
        grid_choice = lset['grid_choice'][source_id]
        grid_label, remap_domain, grid_resolution, grid_description = \
            lset['grids'][grid_choice][context]
    else:
        # DR requested type of grid
        grid_label = grid
        remap_domain = lset["ping_variables_prefix"] + grid
        grid_description = grid2desc(grid)
        grid_resolution = grid2resol(grid)
    if table in ['AERMonZ', ' EmonZ', 'EdayZ']: grid_label += "z"
    if "Ant" in table: grid_label += "a"
    if "Gre" in table: grid_label += "g"
    # mpmoine_TBD : change grid_label depending on shape (sites, transects)
    #
    # --------------------------------------------------------------------
    # Set NetCDF output file name according to the DRS
    # --------------------------------------------------------------------
    #
    # mpmoine_expname:write_xios_file_def_for_svar: es noms d'expe dans la DR ne sont pas les meme que dans le CV CMIP6
    with open(cvspath + project + "_experiment_id.json", "r") as json_fp:
        CMIP6_experiments = json.loads(json_fp.read())['experiment_id']
        if CMIP6_experiments.has_key(sset['experiment_id']):
            expname = sset['experiment_id']
        else:
            # mpmoine_last_modif:write_xios_file_def_for_svar: provisoire, laisser passer cette erreur tant que le
            # mpmoine_last_modif:write_xios_file_def_for_svar: CV_CMIP6 et celui de la DR ne sont pas concordants
            dr2xml_error(
                "Issue getting experiment description in CMIP6 CV for %20s => Search for experiment name correspondance from DR to CMIP6 CV." \
                % sset['experiment_id'])
            expname = dr2cmip6_expname[sset['experiment_id']]
        exp_entry = CMIP6_experiments[expname]
        experiment = exp_entry['experiment']
        description = exp_entry['description']
    #
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: <time_range>="N1-N2" (instead of "N1_N2")
    date_range = "%start_date%-%end_date%"  # XIOS syntax
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: <time_range> format is frequency dependant
    date_format = freq2datefmt(cmv.frequency)
    #
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: [_<time_range>] omitted if frequency is "fx"; a suffix "-clim" is added if climatology
    if cmv.frequency == "fx":
        filename = "%s%s_%s_%s_%s_%s_%s" % \
                   (prefix, cmv.label, table, source_id, expname,
                    member_id, grid_label)
    elif "Clim" in cmv.frequency:
        filename = "%s%s_%s_%s_%s_%s_%s_%s-clim" % \
                   (prefix, cmv.label, table, source_id, expname,
                    member_id, grid_label, date_range)
    else:
        filename = "%s%s_%s_%s_%s_%s_%s_%s" % \
                   (prefix, cmv.label, table, source_id, expname,
                    member_id, grid_label, date_range)
    #
    further_info_url = "http://furtherinfo.es-doc.org/%s.%s.%s.%s.%s.%s" % (
        mip_era, institution_id, source_id, expname,
        sub_experiment_id, variant_label)
    #
    # --------------------------------------------------------------------
    # Compute XIOS split frequency
    # --------------------------------------------------------------------
    # mpmoine_last_modif:write_xios_file_def_for_svar: Maintenant, dans le cas type='perso', table='NONE'. On ne doit donc pas compter sur le table2freq pour recuperer
    # mpmoine_last_modif:write_xios_file_def_for_svar: la frequence en convention xios => fonction cmipFreq2xiosFreq
    # mpmoine_next_modif: write_xios_file_def_for_svar: passage de 'context' en argument de split_frequency_for_variable pour recuperer le model_timestep
    split_freq = split_frequency_for_variable(cmv, lset, sc.mcfg, context)
    #
    # --------------------------------------------------------------------
    # Write XIOS file node:
    # including global CMOR file attributes
    # --------------------------------------------------------------------
    # mpmoine_amelioration:write_xios_file_def_for_svar: ajout de 'ts_prefix' et de time_series="only" => finalement non, et ts_prefix dans le 'name' car on gere nous-meme les time-series
    ts_prefix = lset['output_path']
    if ts_prefix:
        # TBS#out.write(' <file ts_prefix="%s" name="%s" timeseries="only" '%(ts_prefix,filename))
        out.write(' <file name="%s" ' % (ts_prefix + filename))
    else:
        # TBS#out.write(' <file name="%s" timeseries="only" '%filename)
        out.write(' <file name="%s" ' % filename)
    out.write(' output_freq="%s" ' % cmipFreq2xiosFreq[cmv.frequency])
    out.write(' append="true" split_freq="%s" ' % split_freq)
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ajout de 'split_freq_format' pour se coformer a CMOR3.0.3
    out.write(' split_freq_format="%s" ' % date_format)
    # out.write('timeseries="exclusive" >\n')
    out.write(' time_units="days" time_counter_name="time"')
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ajout de time_counter="exclusive"
    out.write(' time_counter="exclusive"')
    out.write(' time_stamp_name="creation_date" ')
    out.write(' time_stamp_format="%Y-%m-%dT%H:%M:%SZ"')
    out.write(' uuid_name="tracking_id" uuid_format="hdl:21.14100/%uuid%"')
    out.write(' >\n')
    #
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: suppression de 'project_id' pas requis pour CMIP6 (remplace par 'activity_id' et 'mip_era')
    # TBS#wr(out,'project_id', sset.get('project',"CMIP6")+"/"+activity_id)
    wr(out, 'activity_id', activity_id)
    #
    if contact and contact is not "": wr(out, 'contact', contact)
    wr(out, 'Conventions', conventions)
    # TBC : assume data_specs_version == dq.version
    wr(out, 'data_specs_version', dq.version)
    #
    wr(out, 'description', description)
    wr(out, 'experiment', experiment)
    wr(out, 'experiment_id', expname)
    #
    # TBD: check external_variables
    # Let us yet hope that all tables but those with an 'O'
    # as first letter require areacella, and the others require areacello
    external_variables = "areacella"
    if table[0] == 'O' or table[0:1] == 'SI': external_variables = "areacello"
    if 'fx' in table: external_variables = ""
    wr(out, 'external_variables', external_variables)
    #
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ecriture de forcing_index en integer requis par la version CMOR3.2.3
    wr(out, 'forcing_index', forcing_index, num_type="int")
    # mpmoine_last_modif: Maintenant, dans le cas type='perso', table='NONE'. On ne doit donc pas compter sur table2freq pour recuperer la frequence
    wr(out, 'frequency', cmv.frequency)
    #
    # URL
    wr(out, 'further_info_url', further_info_url)
    #
    wr(out, 'grid', grid_description);
    wr(out, 'grid_label', grid_label);
    wr(out, 'nominal_resolution', grid_resolution)
    wr(out, 'history', sset, default='none')
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ecriture de  initialization_index en integer requis par la version CMOR3.2.3
    wr(out, "initialization_index", initialization_index, num_type="int")
    wr(out, "institution_id", institution_id)
    if "institution" in lset:
        inst = lset['institution']
    else:
        with open(cvspath + project + "_institution_id.json", "r") as json_fp:
            try:
                inst = json.loads(json_fp.read())['institution_id'][institution_id]
            except:
                raise (dr2xml_error("Fatal: Institution_id for %s not found " + \
                                    "in CMIP6_CV at %s" % (institution, cvspath)))
    wr(out, "institution", inst)
    #
    with open(cvspath + project + "_license.json", "r") as json_fp:
        license = json.loads(json_fp.read())['license'][0]
    # mpmoine_cmor_update: 'licence' est trop long... passe pas le CMIP6-Checker => 'institution_id' au lieu de inst='institution'
    license = license.replace("<Your Centre Name>", institution_id)
    license = license.replace("[NonCommercial-]", "NonCommercial-")
    license = license.replace("[ and at <some URL maintained by modeling group>]",
                              " and at " + lset["info_url"])
    wr(out, "license", license)
    wr(out, 'mip_era', mip_era)
    #
    # mpmoine_cmor_update:write_xios_file_def_for_svar: changement des defaults values pour les parent_<XXX>: default en dur remplace par la valeur pour <XXX>
    # mpmoine_cmor_update:write_xios_file_def_for_svar: et utilisation de l'attribut optionnel 'default' de la fonction 'wr' plutot que sset.get avec une default
    parent_experiment_id = sset.get('parent_experiment_id', False)
    if parent_experiment_id and parent_experiment_id != 'no parent':
        wr(out, 'parent_experiment_id', parent_experiment_id)
        wr(out, 'parent_mip_era', sset, default=mip_era)
        wr(out, 'parent_activity_id', sset, default=activity_id)
        wr(out, 'parent_source_id', sset, default=source_id)
        # TBX : syntaxe XIOS pour designer le time units de la simu courante
        parent_time_ref_year = sset.get('parent_time_ref_year', "1850")
        parent_time_units = "days since %s-01-01 00:00:00" % parent_time_ref_year
        wr(out, 'parent_time_units', sset, default=parent_time_units)
        wr(out, 'parent_variant_label', sset, default=variant_label)
        wr(out, 'branch_method', sset, default='standard')
        wr(out, 'branch_time_in_child', sset)
        wr(out, 'branch_time_in_parent', sset)
        #
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ecriture de physics_index en integer requis par la version CMOR3.2.3
    wr(out, "physics_index", physics_index, num_type="int")
    # mpmoine_cmor_update:write_xios_file_def_for_svar: changement des valeurs de 'product' requis par la version CMOR3.2.3
    wr(out, 'product', 'model-output')
    # mpmoine_cmor_update:write_xios_file_def_for_svar: ecriture de realization_index en integer requis par la version CMOR3.2.3
    wr(out, "realization_index", realization_index, num_type="int")
    wr(out, 'realm', cmv.modeling_realm)
    wr(out, 'references', lset, default=False)
    #
    try:
        with open(cvspath + project + "_source_id.json", "r") as json_fp:
            sources = json.loads(json_fp.read())['source_id']
            source = make_source_string(sources, source_id)
    except:
        if "source" in lset:
            source = lset['source']
        else:
            raise (dr2xml_error("Fatal: source for %s not found in CMIP6_CV at" + \
                                "%s, nor in lset" % (source_id, cvspath)))
    wr(out, 'source', source)
    wr(out, 'source_id', source_id)
    if 'source_type' in sset:
        source_type = sset['source_type']
    else:
        if 'source_type' in lset:
            source_type = lset['source_type']
        else:
            if 'source_types' in lset:
                source_type = lset['source_types'][source_id]
            else:
                raise dr2xml_error("Fatal: No source-type found - Check inputs")
    if type(source_type) == type([]):
        source_type = reduce(lambda x, y: x + " " + y, source_type)
    wr(out, 'source_type', source_type)
    #
    wr(out, 'sub_experiment_id', sub_experiment_id)
    # mpmoine_cmor_update:write_xios_file_def_for_svar: CMOR3.2.2 impose 'None' (et non 'none') pour sub_experiment
    # mpmoine_cmor_update:write_xios_file_def_for_svar: CMOR3.2.3 impose 'none' (et non 'None' !)pour sub_experiment
    wr(out, 'sub_experiment', sset, default='none')
    #
    wr(out, "table_id", table)
    #
    wr(out, "title", "%s model output prepared for %s / %s %s" % ( \
        source_id, project, activity_id, experiment_id))
    #
    wr(out, "variable_id", cmv.label)
    #
    # mpmoine_WIP_update:write_xios_file_def_for_svar: WIP doc v6.2.3 - Apr. 2017: cf recommendation in note 16 for 'variant_info'
    variant_info = sset.get('variant_info', "none")
    if variant_info != "none": variant_info += variant_info_warning
    wr(out, "variant_info", variant_info)
    wr(out, "variant_label", variant_label)
    #
    # --------------------------------------------------------------------
    # Build all XIOS auxilliary elements (end_file_defs, field_defs, domain_defs, grid_defs, axis_defs)
    # ---
    # Write XIOS field_group node (containing field elements, stored in end_field_defs)
    # including CF field attributes
    # --------------------------------------------------------------------
    # mpmoine_zoom_modif:write_xios_file_def_for_svar: appel a create_xios_aux_elmts_defs (anc. create_xios_field_ref) descendu ici
    end_field_defs = dict()
    create_xios_aux_elmts_defs(cmv, alias, table, lset, sset, end_field_defs,
                               field_defs, axis_defs, grid_defs, domain_defs, dummies, context, remap_domain, pingvars)
    if len(end_field_defs.keys()) == 0:
        raise dr2xml_error("No end field ref for %s in %s" % (cmv.label, table))
        return
    #
    # Create a field group for each shape
    for shape in end_field_defs:
        # mpmoine_correction:write_xios_file_def_for_svar: suppression du niveau 'field_group'
        # TBS# dom="" ;
        # TBS# if shape : dom='grid_ref="%s"'%shape
        # TBS# out.write('<field_group %s expr="@this" >\n'%dom)
        for entry in end_field_defs[shape]: out.write(entry)
        # TBS# out.write('</field_group >\n')
    out.write('</file>\n\n')


# mpmoine_last_modif:wrv: ajout de l'argument num_type

def wrv(name, value, num_type="string"):
    # Format a 'variable' entry
    return '     <variable name="%s" type="%s" > %s ' % (name, num_type, value) + \
           '</variable>\n'


# mpmoine_zoom_modif: renommage de la fonction 'create_xios_field_ref' en 'create_xios_aux_elmts_defs'
# mpmoine_zoom_modif: renommage de la fonction 'create_xios_field_ref' en 'create_xios_aux_elmts_defs'
def create_xios_aux_elmts_defs(sv, alias, table, lset, sset, end_field_defs,
                               field_defs, axis_defs, grid_defs, domain_defs, dummies, context, remap_domain, pingvars):
    """
    Create a field_ref for a simplified variable object sv (with
    lab prefix for the variable name) and store it in end_field_defs
    under a key=grid

    Add field definitions for intermediate variables in dic field_defs
    Add axis  definitions for interpolations in dic axis_defs
    Use pingvars as the list of variables actually defined in ping file

    """
    # By convention, field references are built as prefix_<MIP_variable_name>
    # Such references must be fulfilled using a dedicated filed_def
    # section implementing the match between legacy model field names
    # and such names, called 'ping section'
    #
    # Identify which 'ping' variable ultimatley matches the requested
    # CMOR variable, based on shapes. This may involve building
    # intermediate variables, in order to  apply corresponding operations

    # The preferred order of operation is : vertical interp (which
    # is time-dependant), time-averaging, horizontal operations (using
    # expr=@this)

    # nextvar is the field name provided as output of the last
    # operation currently defined
    # mpmoine_zoom_modif:create_xios_aux_elmts_defs: on supprime l'usage de netxvar
    #
    # --------------------------------------------------------------------
    # Build XIOS axis elements (stored in axis_defs)
    # Proceed with vertical interpolation if needed
    # ---
    # Build XIOS auxilliary field elements (stored in field_defs)
    # --------------------------------------------------------------------
    alias1 = False
    ssh = sv.spatial_shp
    prefix = lset["ping_variables_prefix"]
    # mpmoine_zoom_modif:create_xios_aux_elmts_defs: recup de lwps
    lwps = sv.label_without_psuffix
    # TBD Should handle singletons here => mpmoine_note: la mecanique des zoom/union couvre aussi les dim verticale singleton
    # TBD Should ensure that various additionnal dims are duly documented by model or pingfile (e.g. tau)
    # mpmoine_zoom_modif:create_xios_aux_elmts_defs: ajout du cas 'XY-na' pour capturer les dimensions singleton
    if ssh[0:4] in ['XY-H', 'XY-P'] or ssh[0:3] == 'Y-P' or ssh[0:5] == 'XY-na':
        # mpmoine_last_modif:create_xios_aux_elmts_defs: on recupere maintenant 'dimids' depuis svar
        # mpmoine_future_modif:create_xios_aux_elmts_defs: on utilise maintenant sv.sdims pour analyser les dimension
        # mpmoine_question: je ne comprend pas l'usage de nextvar... A priori on ne peut pas avoir plus d'une dimension verticale ?
        for sd in sv.sdims.values():
            if isVertDim(sd):
                # mpmoine_zoom_modif:create_xios_aux_elmts_defs: on supprime l'usage de netxvar
                # mpmoine_zoom_modif:create_xios_aux_elmts_defs: passage par 2 niveaux de field id auxiliaires rebond (alias et alias2)
                if sd.is_zoom_of:
                    # mpmoine_note: cas d'une variable definie grace a 2 axis (zoom+union)
                    alias1 = alias + "_" + sd.label  # e.g. 'CMIP6_hus7h_plev7h'
                    alias2 = prefix + lwps + "_union"  # e.g. 'CMIP6_hus_union'
                    cible = prefix + lwps  # e.g. 'CMIP6_hus'
                    axis_key = sd.zoom_label  # e.g. 'zoom_plev7h_hus'
                else:
                    # mpmoine_note: cas d'une variable definie grace a seul axis (non zoom)
                    alias1 = alias + "_" + sd.label  # e.g. 'CMIP6_hus7h_plev7h'
                    alias2 = False
                    cible = prefix + lwps  # e.g. 'CMIP6_hus'
                    axis_key = sd.label  # e.g. 'plev7h'
                if not cible in pingvars:  # e.g. alias_ping='CMIP6_hus'
                    print "Warning: field id", cible, "expected in pingfile but not found."
                if not alias1 in pingvars:  # mpmoine_note: maintenant on est toujours dans ce cas (e.g. 'CMPI6_hus7h_plev7h' plus jamais ecrit dans le ping)
                    #
                    # Construct an axis for interpolating to this dimension
                    # mpmoine_future_modif:create_xios_aux_elmts_defs: suppression de l'argument 'field_defs' de create_axis_def qui n'est pas utilise
                    # Here, only zoom or normal axis attached to svar, axis for unions of plevs are managed elsewhere
                    axis_defs[axis_key] = create_axis_def(sd, lset["ping_variables_prefix"])
                    #
                    # Construct a grid using variable's grid and new axis
                    # mpmoine_merge_dev2_v0.12:create_xios_aux_elmts_defs: j'ai change nextvar en alias
                    # mpmoine_merge_dev2_v0.12:create_xios_aux_elmts_defs: nouvelle une fonction 'create_grid_def' car utilisee aussi par 'create_xios_grids_for_plev_unions'

                    # TBS# if not sd.is_zoom_of: # create a (target) grid for re-mapping only if vert axis is not a zoom (i.e. if normal or union)
                    # mpmoine_correction:create_xios_aux_elmts_defs: il faut creer un grid aussi autour des zoom axis
                    # mpmoine_correction:create_xios_aux_elmts_defs: alias_ping au lieu de alias en arg de create_grid_def
                    alias_ping = lset[
                                     "ping_variables_prefix"] + lwps  # e.g. 'CMIP6_hus' and not 'CMIP6_hus7h'; 'CMIP6_co2' and not 'CMIP6_co2Clim'
                    # TBS# grid_def=create_grid_def(sd,alias,context_index)
                    grid_def = create_grid_def(sd, alias_ping, context_index)
                    grid_id = grid_def[0]
                    grid_defs[grid_id] = grid_def[1]
                    #
                    # Construct a field def for the re-mapped variable
                    # mpmoine_correction:create_xios_aux_elmts_defs: passage par grid_ref aussi pour les varaibles definies sur des zoom
                    if sd.is_zoom_of:  # mpmoine_note: cas variable definie grace a 2 axis_def (union+zoom)
                        field_defs[alias1] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                             % (alias1 + '"', alias2 + '"', "grid_" + sd.zoom_label + '"')
                        # mpmoine_merge_dev2_v0.12:create_xios_aux_elmts_defs: remplacement axis_ref=sd.is_zoom_of -> grid_ref="grid_"+sd.is_zoom_of
                        field_defs[alias2] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                             % (alias2 + '"', cible + '"', "grid_" + sd.is_zoom_of + '"')
                    else:  # mpmoine_note: cas variable definie grace a seul axis_def (non union+zoom)
                        # mpmoine_merge_dev2_v0.12:create_xios_aux_elmts_defs: remplacement axis_ref=sd.label -> grid_ref=grid_id
                        # mpmoine_correction:create_xios_aux_elmts_defs: alias1  au lieu de alias pour l'ecriture de field_defs
                        field_defs[alias1] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                             % (alias1 + '"', cible + '"', grid_id + '"')
                        # mpmoine_note: voir en desactivant les zooms si c'est ok
                # TBD what to do for singleton dimension ?
    #
    # --------------------------------------------------------------------
    # Retrieve XIOS temporal operation to perform
    # by analyzing the time part of cell_methods
    # --------------------------------------------------------------------
    # Analyze 'outermost' time cell_methods and translate to 'operation'
    operation, detect_missing = analyze_cell_time_method(sv.cell_methods, sv.label, table)
    # mpmoine_alelioration:create_xios_aux_elmts_defs: lever une erreur quand on ne trouve pas une operation temporelle xios correcte
    if not operation:
        raise dr2xml_error(
            "Fatal: bad xios 'operation' for %s in table %s: %s (%s)" % (sv.label, table, operation, sv.cell_methods))
    if not type(detect_missing) == type(bool()):
        raise dr2xml_error("Fatal: bad xios 'detect_missing_value' for %s in table %s: %s (%s)" % (
            sv.label, table, detect_missing, sv.cell_methods))
    #
    # --------------------------------------------------------------------
    # Build XIOS grid elements (stored in grid_defs)
    # by analyzing the spatial shape
    # Including horizontal operations. Can include horiz re-gridding specification
    # --------------------------------------------------------------------
    # Compute domain name, define it if needed
    grid_ref = None
    if ssh[0:2] == 'Y-':  # zonal mean and atm zonal mean on pressure levels
        # TBD should remap before zonal mean # STOPICI_REVUE_TBD_09-05-2017
        grid_ref = "zonal_mean"
        grid_defs[grid_ref] = '<grid id="%s"/>' % grid_ref
    elif ssh[0:2] == 'S-':  # COSP sites; cas S-na, S-A, S-AH
        grid_ref = "COSP_sites_grid"
        # Assume that grid COSP_sites is defined in ping_file
        # grid_defs[grid_ref]='<grid id="%s"/>'%grid_ref
    elif ssh[0:2] == 'L-':
        grid_ref = "COSP_curtain_grid"
        grid_defs[grid_ref] = '<grid id="%s"/>' % grid_ref
    elif ssh == 'TR-na' or ssh == 'TRS-na':  # transects,   oce or SI
        pass
    elif ssh[0:3] == 'XY-':  # includes 'XY-AH' : model half-levels
        if remap_domain: grid_ref = remap_domain
    elif ssh[0:3] == 'YB-':  # basin zonal mean or section
        pass
    elif ssh == 'na-na':  # global means or constants
        pass
    else:
        raise (dr2xml_error("Fatal: Issue with un-managed spatial shape %s" % ssh))
    #
    # --------------------------------------------------------------------
    # Build XIOS field elements (stored in end_field_defs)
    # including their CMOR attributes
    # --------------------------------------------------------------------
    # mpmoine_correction:create_xios_aux_elmts_defs: alias1  au lieu de alias pour l'ecriture de end_field_defs
    # TBS# if any (sd.is_zoom_of for sd in sv.sdims.values()):
    # mpmoine_cmor_update:create_xios_aux_elmts_defs: les tables CMOR demandent les champs en 'float' ou 'real' => ajout de prec="4"
    # TBI: idealement if faudrait recuperer le type attendu de la DR ou des tables CMOR
    if alias1:
        rep = '  <field field_ref="%s" name="%s" ts_enabled="true"' % \
              (alias1, sv.label)
    else:
        rep = '  <field field_ref="%s" name="%s" ts_enabled="true"' % \
              (alias, sv.label)
    rep += ' operation="%s" detect_missing_value="%s" default_value="1.e+20" prec="4"' % \
           (operation, detect_missing)
    rep += ' cell_methods="%s" cell_methods_mode="overwrite"' % sv.cell_methods
    rep += '>\n'
    #
    comment = None
    # Process experiment-specific comment for the variable
    if sv.label in sset['comments'].keys():
        comment = sset['comments'][sv.label]
    else:  # Process lab-specific comment for the variable
        if sv.label in lset['comments'].keys():
            comment = sset['comments'][sv.label]
    if comment: rep += wrv('comment', comment)  # TBI
    #
    rep += wrv("standard_name", sv.stdname)
    #
    desc = sv.description
    if desc: desc = desc.replace(">", "").replace("<", "")
    rep += wrv("description", desc)
    #
    rep += wrv("long_name", sv.long_name)
    if sv.positive != "None" and sv.positive != "":
        rep += wrv("positive", sv.positive)
    rep += wrv('history', 'none')
    rep += wrv('units', sv.stdunits)
    # mpmoine_last_modif:create_xios_aux_elmts_defs: ajout de missing_value pour satisfaire le standard attendu par CMOR
    # mpmoine_last_modif:create_xios_aux_elmts_defs:  missing_valueS pour l'instant pour que ça passe le CMORchecker (issue)
    rep += wrv('cell_methods', sv.cell_methods)
    rep += wrv('cell_measures', sv.cell_measures)
    # mpmoine_note: 'missing_value(s)' normalement plus necessaire, a verifier
    # TBS# rep+=wrv('missing_values',sv.missing,num_type="double")
    rep += '     </field>\n'
    #
    if grid_ref not in end_field_defs: end_field_defs[grid_ref] = []
    end_field_defs[grid_ref].append(rep)


# mpmoine_last_modif:gather_all_simple_vars: nouvelle fonction qui rassemble les operations select_cmor_vars_for_lab et read_home_vars_list.
# mpmoine_last_modif:gather_all_simple_vars: Necessaire pour create_ping_file qui doit tenir compte des extra_Vars
def gather_AllSimpleVars(lset, expid=False, year=False, printout=False):
    mip_vars_list = select_CMORvars_for_lab(lset, expid, year, printout=printout)
    if lset['listof_home_vars']:
        process_homeVars(lset, mip_vars_list, dq, expid, printout)

    else:
        print "Info: No HOMEvars list provided."
    return mip_vars_list


def generate_file_defs(lset, sset, year, context, cvs_path, pingfile=None,
                       dummies='include', printout=False, dirname="./", prefix=""):
    """
    Using global DR object dq, a dict of lab settings LSET, and a dict
    of simulation settings SSET, generate an XIOS file_defs file for a
    given XIOS 'context', which content matches
    the DR for the experiment quoted in simu setting dict and a YEAR.
    Makes use of CMIP6 controlled vocabulary files found in CVS_PATH
    Reads PINGFILE for analyzing dummy field_refs,
    DUMMIES='include' : include dummy refs in file_def (useful
                              demonstration run)
    DUMMIES='skip'  : don't write field with a ref to a dummy
                          (useful until ping_file is fully completed)
    DUMMIES='forbid': stop if any dummy (useful for production run)
    Output file is named <DIRNAME>filedefs_<CONTEXT>.xml
    Filedefs have a CMIP6 compliant name, with prepended PREFIX

    Structure of the two dicts is documented elsewhere. It includes the
    correspondance between a context and a few realms
    """
    #
    # --------------------------------------------------------------------
    # Parse XIOS setting files for the context
    # --------------------------------------------------------------------
    global context_index
    # mpmoine_amelioration:generate_file_defs: ajout de l'argument 'path_parse' a la fonction init_context
    context_index = init_context(context, lset["path_to_parse"], printout=False)
    #
    # --------------------------------------------------------------------
    # Extract CMOR variables for the experiment and year and lab settings
    # --------------------------------------------------------------------
    # mpmoine_skipped_modif:generate_file_defs: skipped_vars (liste) change en skipped_vars_per_table (dictionnaire)
    skipped_vars_per_table = {}
    mip_vars_list = gather_AllSimpleVars(lset, sset['experiment_id'], year, printout)
    # Group CMOR vars per realm
    svars_per_realm = dict()
    for svar in mip_vars_list:
        if svar.modeling_realm not in svars_per_realm.keys():
            svars_per_realm[svar.modeling_realm] = []
        if svar not in svars_per_realm[svar.modeling_realm]:
            svars_per_realm[svar.modeling_realm].append(svar)
        else:
            old = svars_per_realm[svar.modeling_realm][0]
            print "Duplicate svar %s %s %s %s" % (old.label, old.grid, svar.label, svar.grid)
            pass
    if printout:
        print "\nRealms for these CMORvars :", svars_per_realm.keys()
    #
    # --------------------------------------------------------------------
    # Select on context realms, grouping by table
    # Excluding 'excluded_vars' and 'excluded_spshapes' lists
    # --------------------------------------------------------------------
    svars_per_table = dict()
    context_realms = lset['realms_per_context'][context]
    for realm in context_realms:
        if realm in svars_per_realm.keys():
            for svar in svars_per_realm[realm]:
                # mpmoine_last_modif:generate_file_defs: patch provisoire pour retirer les  svars qui n'ont pas de spatial_shape
                # mpmoine_last_modif:generate_file_defs: (cas par exemple de 'hus' dans table '6hrPlev' => spid='__struct_not_found_001__')
                # mpmoine_next_modif: generate_file_defs: exclusion de certaines spatial shapes (ex. Polar Stereograpic Antarctic/Groenland)
                if svar.label not in lset['excluded_vars'] and svar.spatial_shp and svar.spatial_shp not in lset[
                    "excluded_spshapes"]:
                    if svar.mipTable not in svars_per_table:
                        svars_per_table[svar.mipTable] = []
                    svars_per_table[svar.mipTable].append(svar)
                else:
                    # mpmoine_future_modif:generate_file_defs: juste un peu plus de printout...
                    if printout:
                        print "Warning: ", svar.label, " in table ", svar.mipTable, " has been excluded for one or several of the following reason(s):"
                        if svar.label in lset['excluded_vars']: print "   * is in excluded list"
                        if not svar.spatial_shp: print "   * has no spatial shape"
                        if svar.spatial_shp in lset[
                            "excluded_spshapes"]: print "   * has an excluded spatial shape:", svar.spatial_shp
    #
    # --------------------------------------------------------------------
    # Add svars belonging to the orphan list
    # --------------------------------------------------------------------
    orphans = lset['orphan_variables'][context]
    for svar in mip_vars_list:
        if svar.label in orphans:
            # mpmoine_last_modif:generate_file_defs: patch provisoire pour retirer les  svars qui n'ont pas de spatial_shape
            # mpmoine_last_modif:generate_file_defs: (cas par exemple de 'hus' dans table '6hrPlev' => spid='__struct_not_found_001__')
            # mpmoine_next_modif: generate_file_defs: exclusion de certaines spatial shapes (ex. Polar Stereograpic Antarctic/Groenland)
            if svar.label not in lset['excluded_vars'] and svar.spatial_shp and svar.spatial_shp not in lset[
                "excluded_spshapes"]:
                if svar.mipTable not in svars_per_table:
                    svars_per_table[svar.mipTable] = []
                svars_per_table[svar.mipTable].append(svar)
    #
    #
    # mpmoine_zoom_modif:generate_file_defs: build axis defs of plevs unions
    # --------------------------------------------------------------------
    # Build all plev union axis and grids
    # --------------------------------------------------------------------
    if lset['use_union_zoom']:
        svars_full_list = []
        for svl in svars_per_table.values(): svars_full_list.extend(svl)
        # mpmoine_merge_dev2_v0.12:generate_file_defs: on recupere maintenant non seulement les union_axis_defs mais aussi les union_grid_defs
        (union_axis_defs, union_grid_defs) = create_xios_axis_and_grids_for_plevs_unions(svars_full_list,
                                                                                         multi_plev_suffixes.union(
                                                                                             single_plev_suffixes),
                                                                                         lset["ping_variables_prefix"])
    #
    # --------------------------------------------------------------------
    # Read ping_file defined variables
    # --------------------------------------------------------------------
    pingvars = []
    if pingfile:
        ping_refs = read_xml_elmt_or_attrib(pingfile, tag='field', attrib='field_ref')
        if ping_refs is None:
            print "Error: issue accessing pingfile " + pingfile
            return
        if dummies == "include":
            pingvars = ping_refs.keys()
        else:
            pingvars = [v for v in ping_refs if 'dummy' not in ping_refs[v]]
            if dummies == "forbid":
                if len(pingvars) != len(ping_refs):
                    print "They are dummies in %s :" % pingfile,
                    for v in ping_refs:
                        if v not in pingvars: print v,
                    print
                    return
                else:
                    pingvars = ping_ref
            elif dummies == "skip":
                pass
            else:
                print "Forbidden option for dummies : " + dummies
                return
    #
    # --------------------------------------------------------------------
    # Start writing XIOS file_def file:
    # file_definition node, including field child-nodes
    # --------------------------------------------------------------------
    # filename=dirname+"filedefs_%s.xml"%context
    filename = dirname + "dr2xml_%s.xml" % context
    with open(filename, "w") as out:
        out.write('<context id="%s"> \n' % context)
        field_defs = dict()
        axis_defs = dict()
        # mpmoine_merge_dev2_v0.12:generate_file_defs: initialisation de grid_defs
        grid_defs = dict()
        domain_defs = dict()
        # for table in ['day'] :
        out.write('\n<file_definition type="one_file" enabled="true" > \n')
        for table in svars_per_table:
            count = dict()
            for svar in svars_per_table[table]:
                if svar.label not in count:
                    count[svar.label] = svar
                    for grid in svar.grids:
                        write_xios_file_def(svar, table, lset, sset, out, cvs_path,
                                            field_defs, axis_defs, grid_defs, domain_defs, dummies,
                                            skipped_vars_per_table, prefix, context, grid, pingvars)
                else:
                    pass
                    print "Duplicate var in %s : %s %s %s" % (
                        table, svar.label, `svar.temporal_shp`, \
                        `count[svar.label].temporal_shp`)
        out.write('\n</file_definition> \n')
        #
        # --------------------------------------------------------------------
        # End writing XIOS file_def file:
        # field_definition, axis_definition, grid_definition
        # and domain_definition auxilliary nodes
        # --------------------------------------------------------------------
        # Write all domain, axis, field defs needed for these file_defs
        out.write('<field_definition> \n')
        for obj in field_defs: out.write("\t" + field_defs[obj] + "\n")
        out.write('\n</field_definition> \n')
        out.write('\n<axis_definition> \n')
        for obj in axis_defs.keys(): out.write("\t" + axis_defs[obj] + "\n")
        # mpmoine_zoom_modif:generate_file_defs: on ecrit maintenant les axis defs pour les unions
        # mpmoine_zoom_amelioration:generate_file_defs: usage de 'use_union_zoom'
        if lset['use_union_zoom']:
            for obj in union_axis_defs.keys(): out.write("\t" + union_axis_defs[obj] + "\n")
        out.write('</axis_definition> \n')
        out.write('\n<domain_definition> \n')
        for obj in domain_defs.keys(): out.write("\t" + domain_defs[obj] + "\n")
        out.write('</domain_definition> \n')
        # mpmoine_merge_dev2_v0.12:generate_file_defs: ecriture des grid_defs
        out.write('\n<grid_definition> \n')
        for obj in grid_defs.keys(): out.write("\t" + grid_defs[obj] + "\n")
        # mpmoine_merge_dev2_v0.12:generate_file_defs: on ecrit maintenant les grid defs pour les unions
        # mpmoine_zoom_amelioration:generate_file_defs: usage de 'use_union_zoom'
        if lset['use_union_zoom']:
            for obj in union_grid_defs.keys(): out.write("\t" + union_grid_defs[obj] + "\n")
        out.write('</grid_definition> \n')
        out.write('</context> \n')
    if printout:
        print "\nfile_def written as %s" % filename

    # mpmoine_petitplus:generate_file_defs: pour sortir des stats sur ce que l'on sort reelement
    if printout: print_SomeStats(context, svars_per_table, skipped_vars_per_table)


# mpmoine_petitplus: nouvelle fonction print_some_stats (plus d'info sur les skipped_vars, nbre de vars / (shape,freq) )
def print_SomeStats(context, svars_per_table, skipped_vars_per_table):
    # --------------------------------------------------------------------
    # Print Summary: list of  considered variables per table
    # (i.e. not excuded_vars and not excluded_shapes)
    # --------------------------------------------------------------------
    print "\nTables concerned by context %s : " % context, svars_per_table.keys()
    print "\nVariables per table :"
    for table in svars_per_table.keys():
        print ">>> DBG >>> TABLE"
        print "%15s %02d ---->" % (table, len(svars_per_table[table])),
        for svar in svars_per_table[table]:
            print svar.label + "(" + str(svar.Priority) + ")",

        # --------------------------------------------------------------------
        # Print Summary: list of skipped variables per table
        # (i.e. not in the ping_file)
        # --------------------------------------------------------------------
        if skipped_vars_per_table:
            print "\nSkipped variables (i.e. whose alias is not present in the pingfile):"
        for table, skipvars in skipped_vars_per_table.items():
            print "\n%15s %02d/%02d ---->" % (table, len(skipvars), len(svars_per_table[table])),
            # TBS# print "\n\t",table ," ",len(skipvars),"--->",
            for skv in skipvars:
                print skv,  # already contains priority info

        # --------------------------------------------------------------------
        # Print Summary: list of variables really written in the file_def
        # (i.e. not excluded and not skipped)
        # --------------------------------------------------------------------
        stats_out = {}
    for table in svars_per_table.keys():
        for sv in svars_per_table[table]:
            dic_freq = {}
            dic_shp = {}
            if (table not in skipped_vars_per_table.keys()) or \
                    (table in skipped_vars_per_table.keys() and sv not in skipped_vars_per_table[table]):
                freq = sv.frequency
                shp = sv.spatial_shp
                prio = sv.Priority
                var = sv.label
                if stats_out.has_key(freq):
                    dic_freq = stats_out[freq]
                    if dic_freq.has_key(shp):
                        dic_shp = dic_freq[shp]
                dic_shp.update({var: table + "-P" + str(prio)})
                dic_freq.update({shp: dic_shp})
                stats_out.update({freq: dic_freq})

    print "\n\nSome Statistics..."
    for k1, v1 in stats_out.items():
        for k2, v2 in v1.items():
            nb = len(v2.values())
            print "\n\n* %d variables output at %s frequency with shape %s ---> " % (nb, k1, k2)
            for k3, v3 in v2.items(): print k3, "(", v3, "),",


# mpmoine_future_modif:create_axis_def: suppression de l'argument 'field_defs' qui n'est pas utilise
# mpmoine_future_modif:create_axis_def: suppression de l'argument 'field_defs' qui n'est pas utilise
def create_axis_def(sdim, prefix):
    """
    From a  simplified Dim object, returns an Xios axis definition
    """
    # mpmoine_future_modif:create_axis_def: plusieurs modifs car on passe maintenant sdim en argument et non dim_name_or_obj
    if sdim is None:
        print "Warning: cannot create an axis_def from " + sdim
        return None

    # mpmoine_zoom_modif:create_axis_def: nbre de valeurs de l'axe determine aussi si on est en dim singleton
    if sdim.requested:
        # mpmoine_future_modif: je vire le separateur " ", pour regler le pb des " " successifs
        glo_list = sdim.requested.strip(" ").split()
    else:
        glo_list = sdim.value.strip(" ").split()
    glo_list_num = [float(v) for v in glo_list]
    n_glo = len(glo_list)

    # mpmoine_zoom_modif:create_axis_def: traitement du cas non zoom (classique, comme avant)
    if not sdim.is_zoom_of:
        # Axis is not a zoom of another, write axis_def normally (with value, interpolate_axis,etc.)
        rep = '<axis id="%s" ' % sdim.label
        if not sdim.positive in [None, ""]:
            rep += 'positive="%s" ' % sdim.positive
        if n_glo > 1:
            # Case of a non-degenerated vertical dimension (not a singleton)
            rep += 'n_glo="%g" ' % n_glo
            # mpmoine_future_modif:create_axis_def: je supprime le -1 pour n_glo car regle avec rstrip/split()
            # mpmoine_correction:create_axis_def: n_glo->(n_glo-1)
            rep += 'value="(0,%g) [%s]"' % (n_glo - 1, sdim.requested)
        else:
            if n_glo != 1:
                print "Warning: axis is sigleton but has", n_glo, "values"
                return None
            # Singleton case (degenerated vertical dimension)
            rep += 'n_glo="%g" ' % n_glo
            rep += 'value="(0,0)[%s]"' % sdim.value
        rep += ' name="%s"' % sdim.out_name
        rep += ' standard_name="%s"' % sdim.stdname
        rep += ' long_name="%s"' % sdim.long_name
        rep += ' unit="%s"' % sdim.units
        rep += '>'
        if sdim.stdname == "air_pressure": coordname = prefix + "pfull"
        if sdim.stdname == "altitude": coordname = prefix + "zg"
        rep += '\n\t<interpolate_axis type="polynomial" order="1"'
        rep += ' coordinate="%s"/>\n\t</axis>' % coordname
        return rep
    # mpmoine_zoom_modif:create_axis_def: traitement du cas zoom
    else:
        # Axis is subset of another, write it as a zoom_axis
        rep = '<axis id="%s"' % sdim.zoom_label
        rep += ' axis_ref="%s">\n' % sdim.is_zoom_of
        # mpmoine_correction:create_axis_def:  correction syntaxe begin du zoom
        rep += '\t<zoom_axis begin="%g" n="%g"/>\n' % (0, n_glo)
        rep += '\t</axis>'
        return rep


# mpmoine_merge_dev2_v0.12: nouvelle fonction create_grid_def
def create_grid_def(sd, alias=None, context_index=None):
    # mpmoine_correction:create_grid_def:  si, il faut generer une grille autour des axes de zoom aussi
    if not sd.is_zoom_of and not sd.is_union_for:  # a grid_def to build in classical case (a vertical axis without using union)
        if alias and context_index:
            src_grid = id2grid(alias, context_index, printout=True)
            src_grid_id = src_grid.attrib['id']
            src_grid_string = ET.tostring(src_grid)
            target_grid_id = src_grid_id + "_" + sd.label
            target_grid_string = re.sub('axis_ref= *.([\w_])*.', 'axis_ref="%s"' % sd.label, src_grid_string)
            target_grid_string = re.sub('grid id= *.([\w_])*.', 'grid id="%s"' % target_grid_id, target_grid_string)
            return (target_grid_id, target_grid_string)
        else:
            raise dr2xml_error("Fatal: ask for creating a grid_def from a native grid " + \
                               "but variable alias and/or context_index not provided (alias:%s, context_index:%s)" % (
                               alias, context_index))
            return False
    elif sd.is_union_for:  # a grid_def to build in union case
        grid_id = "grid_" + sd.label
        grid_string = '<grid id="%s">' % grid_id
        grid_string += '\n\t<domain domain_ref="%s"/>' % "domain_atm"  # mpmoine_note: attention, en dur !
        grid_string += '\n\t<axis axis_ref="%s"/>' % sd.label
        grid_string += '\n\t</grid>'
        return (grid_id, grid_string)
    elif sd.is_zoom_of:  # a grid_def to build in zoom case
        grid_id = "grid_" + sd.zoom_label
        grid_string = '<grid id="%s">' % grid_id
        grid_string += '\n\t<domain domain_ref="%s"/>' % "domain_atm"  # mpmoine_note: attention, en dur !
        grid_string += '\n\t<axis axis_ref="%s"/>' % sd.zoom_label
        grid_string += '\n\t</grid>'
        return (grid_id, grid_string)
    else:
        print "Warning: calling create_grid_def for a vertical axis which nothing among classical/union/zoom... Humm, don't know what this axis is..."
        return False


# mpmoine_zoom_modif: nouvelle fonction 'create_xios_axis_for_plevs_unions'
# mpmoine_merge_dev2_v0.12: 'create_xios_axis_for_plevs_unions' renomee en 'create_xios_axis_and_grids_for_plevs_unions'
def create_xios_axis_and_grids_for_plevs_unions(svars, plev_sfxs, prefix, printout=False):
    """
    Objective of this function is to optimize Xios vertical interpolation requested in pressure levels.
    Process in 2 steps:
    * First, search pressure levels unions for each simple variable label without psuffix and build a dictionnary :
        dict_plevs is a 3-level intelaced dictionnary containing for each var (key=svar label_without_psuffix),
        the list of svar (key=svar label,value=svar object) per pressure levels set (key=sdim label):
        { "varX":
              { "plevA": {"svar1":svar1,"svar2":svar2,"svar3":svar3},
                "plevB": {"svar4":svar4,"svar5":svar5},
                "plevC": {"svar6":svar6} },
          "varY":
             { "plevA": {"svar7":svar7},
               "plevD": {"svar8":svar8,"svar9":svar9} }
        }
    * Second, create create all of the Xios union axis (axis id: union_plevs_<label_without_psuffix>)
    """
    #
    # First, search plev unions for each label_without_psuffix and build dict_plevs
    dict_plevs = {}
    for sv in svars:
        if not sv.modeling_realm: print "Warning: no modeling_realm associated to:", \
            sv.label, sv.mipTable, sv.mip_era
        for sd in sv.sdims.values():
            # mpmoine_note: couvre les dimensions verticales de type 'plev7h' ou 'p850'
            if sd.label.startswith("p") and any(sd.label.endswith(s) for s in plev_sfxs):
                lwps = sv.label_without_psuffix
                if lwps:
                    sv.sdims[sd.label].is_zoom_of = "union_plevs_" + lwps
                    if not dict_plevs.has_key(lwps):
                        dict_plevs[lwps] = {sd.label: {sv.label: sv}}
                    else:
                        if not dict_plevs[lwps].has_key(sd.label):
                            dict_plevs[lwps].update({sd.label: {sv.label: sv}})
                        else:
                            if sv.label not in dict_plevs[lwps][sd.label].keys():
                                dict_plevs[lwps][sd.label].update({sv.label: sv})
                            else:
                                # TBS# print sv.label,"in table",sv.mipTable,"already listed for",sd.label
                                pass
                    # svar will be expected on a zoom axis of the union. Corresponding vertical dim must
                    # have a zoom_label named plevXX_<lwps> (multiple pressure levels) or pXX_<lwps> (single pressure level)
                    sv.sdims[sd.label].zoom_label = 'zoom_' + sd.label + "_" + lwps
                else:
                    print "Warning: dim is pressure but label_without_psuffix=", lwps, \
                        "for", sv.label, sv.mipTable, sv.mip_era
    #
    # Second, create xios axis for union of plevs
    union_axis_defs = {}
    union_grid_defs = {}
    for lwps in dict_plevs.keys():
        sdim_union = simple_Dim()
        plevs_union_xios = ""
        plevs_union = set()
        for plev in dict_plevs[lwps].keys():
            plev_values = []
            for sv in dict_plevs[lwps][plev].values():
                if not plev_values:
                    # svar is the first one with this plev => get its level values
                    # mpmoine_note: on reecrase les attributs de sdim_union à chaque nouveau plev. Pas utile mais
                    # mpmoine_note: c'est la facon la plus simple de faire
                    sdsv = sv.sdims[plev]
                    if sdsv.stdname:   sdim_union.stdname = sdsv.stdname
                    if sdsv.long_name: sdim_union.long_name = sdsv.long_name
                    if sdsv.positive:  sdim_union.positive = sdsv.positive
                    if sdsv.out_name:  sdim_union.out_name = sdsv.out_name
                    if sdsv.units:     sdim_union.units = sdsv.units
                    if sdsv.requested:
                        # case of multi pressure levels
                        plev_values = set(sdsv.requested.split())
                        sdim_union.is_union_for.append(sv.label + "_" + sd.label)
                    elif sdsv.value:
                        # case of single pressure level
                        plev_values = set(sdsv.value.split())
                        sdim_union.is_union_for.append(sv.label + "_" + sd.label)
                    else:
                        print "Warning: No requested nor value found for", svar.label, "with vertical dimesion", plev
                    plevs_union = plevs_union.union(plev_values)
                    if printout: print "    -- on", plev, ":", plev_values
                if printout: print "       *", svar.label, "(", svar.mipTable, ")"
        list_plevs_union = list(plevs_union)
        # mpmoine_further_zoom_modif:create_xios_axis_for_plevs_unions: correction du tri des niveaux de pression sur les axes d'union
        list_plevs_union_num = [float(lev) for lev in list_plevs_union]
        list_plevs_union_num.sort(reverse=True)
        list_plevs_union = [str(lev) for lev in list_plevs_union_num]
        for lev in list_plevs_union: plevs_union_xios += " " + lev
        if printout: print ">>> XIOS plevs union:", plevs_union_xios
        sdim_union.label = "union_plevs_" + lwps
        if len(list_plevs_union) > 1: sdim_union.requested = plevs_union_xios
        if len(list_plevs_union) == 1: sdim_union.value = plevs_union_xios
        axis_def = create_axis_def(sdim_union, prefix)
        union_axis_defs.update({sdim_union.label: axis_def})
        # mpmoine_merge_dev2_v0.12: maintenant on doit non seulement creer les axes d'union mais aussi les grid les englobant
        grid_def = create_grid_def(sdim_union)
        grid_id = grid_def[0]
        union_grid_defs[grid_id] = grid_def[1]
    #
    return (union_axis_defs, union_grid_defs)


def isVertDim(sdim):
    """
    Returns True if dim represents a dimension for which we want
    an Xios interpolation.
    For now, a very simple logics for interpolated vertical
    dimension identification:
    """
    # mpmoine_future_modif: is_vert_dim: on utilise maintenant sv.sdims pour analyser les dimensions
    test = (sdim.stdname == 'air_pressure' or sdim.stdname == 'altitude')
    return test


def analyze_cell_time_method(cm, label, table):
    """
    Depending on cell method string CM, tells which time operation
    should be done, and if missing value detection should be set
    We rely on the missing value detection to match the requirements like
    "where sea-ice", "where cloud" since we suppose fields required in this way
    are physically undefined oustide of "where something".
    """
    operation = None
    detect_missing = False
    #
    if cm is None:
        if print_DR_errors:
            print "DR Error: cell_time_method is None for %15s in table %s, averaging" % (label, table)
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean (with samples weighted by snow mass)" in cm:
        # [amnla-tmnsn]: Snow Mass Weighted (LImon : agesnow, tsnLi)
        print "TBD: Cannot yet handle time: mean (with samples weighted by snow mass) for " + \
              "%15s in table %s -> averaging" % (label, table)
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean where cloud" in cm:
        # [amncl-twm]: Weighted Time Mean on Cloud (2 variables ISSCP
        # albisccp et pctisccp, en emDay et emMon)
        print "Note : assuming that 'time: mean where cloud' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean where sea_ice" in cm:
        # [amnsi-twm]: Weighted Time Mean on Sea-ice (presque que des
        # variables en SImon, sauf sispeed et sithick en SIday)
        # mpmoine_correction:analyze_cell_time_method: ajout de operation="average" pour "time: mean where sea_ice"
        print "Note : assuming that 'time: mean where sea_ice' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean where sea" in cm:  # [amnesi-tmn]:
        # Area Mean of Ext. Prop. on Sea Ice : pas utilisee
        print "time: mean where sea is not supposed to be used (%s,%s)" % (label, table)
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where floating_ice_shelf"
    elif "time: mean where floating_ice_shelf" in cm:
        # [amnfi-twmn]: Weighted Time Mean on Floating Ice Shelf (presque que des
        # variables en Imon, Iyr, sauf sftflt en LImon !?)
        print "Note : assuming that 'time: mean where floating_ice_shelf' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where grounded_ice_sheet"
    elif "time: mean where grounded_ice_sheet" in cm:
        # [amngi-twm]: Weighted Time Mean on Grounded Ice Shelf (uniquement des
        # variables en Imon, Iyr)
        print "Note : assuming that 'time: mean where grounded_ice_sheet' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where ice_sheet"
    elif "time: mean where ice_sheet" in cm:
        # [amnni-twmn]: Weighted Time Mean on Ice Shelf (uniquement des
        # variables en Imon, Iyr)
        print "Note : assuming that 'time: mean where ice_sheet' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where sea_ice_melt_pound"
    elif "time: mean where sea_ice_melt_pound" in cm:
        # [amnnsimp-twmm]: Weighted Time Mean in Sea-ice Melt Pounds (uniquement des
        # variables en SImon)
        print "Note : assuming that 'time: mean where sea_ice_melt_pound' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where landuse"
    elif "time: mean where landuse" in cm:
        # [amlu-twm]: Weighted Time Mean on Land Use Tiles (uniquement des
        # variables suffixees en 'Lut')
        print "Note : assuming that 'time: mean where landuse' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where crops"
    elif "time: mean where crops" in cm:
        # [amc-twm]: Weighted Time Mean on Crops (uniquement des
        # variables suffixees en 'Crop')
        print "Note : assuming that 'time: mean where crops' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where natural_grasses"
    elif "time: mean where natural_grasses" in cm:
        # [amng-twm]: Weighted Time Mean on Natural Grasses (uniquement des
        # variables suffixees en 'Grass')
        print "Note : assuming that 'time: mean where natural_grasses' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where shrubs"
    elif "time: mean where shrubs" in cm:
        # [ams-twm]: Weighted Time Mean on Shrubs (uniquement des
        # variables suffixees en 'Shrub')
        print "Note : assuming that 'time: mean where shrubs' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where trees"
    elif "time: mean where trees" in cm:
        # [amtr-twm]: Weighted Time Mean on Bare Ground (uniquement des
        # variables suffixees en 'Tree')
        print "Note : assuming that 'time: mean where trees' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas "time: mean where vegetation"
    elif "time: mean where vegetation" in cm:
        # [amv-twm]: Weighted Time Mean on Vegetation (pas de varibles concernees)
        print "Note : assuming that 'time: mean where vegetation' " + \
              " for %15s in table %s is well handled by 'detect_missing'" \
              % (label, table)
        operation = "average"
        detect_missing = True
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: minimum" in cm:
        # [tmin]: Temporal Minimum : utilisee seulement dans table daily
        operation = "minimum"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: maximum" in cm:
        # [tmax]: Time Maximum  : utilisee seulement dans table daily
        operation = "maximum"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: maximum within days time: mean over days" in cm:
        # [dmax]: Daily Maximum : tasmax Amon seulement
        if label != 'tasmax':
            print "Error: issue with variable %s in table %s " % (label, table) + \
                  "and cell method time: maximum within days time: mean over days"
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: minimum within days time: mean over days" in cm:
        # [dmin]: Daily Minimum : tasmin Amon seulement
        if label != 'tasmin':
            print "Error: issue with variable %s in table %s  " % (label, table) + \
                  "and cell method time: minimum within days time: mean over days"
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean within years time: mean over years" in cm:
        # [aclim]: Annual Climatology
        print "TBD: Cannot yet compute annual climatology for " + \
              "%15s in table %s -> averaging" % (label, table)
        # Could transform in monthly fields to be post-processed
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean within days time: mean over days" in cm:
        # [amn-tdnl]: Mean Diurnal Cycle
        print "TBD: Cannot yet compute diurnal cycle for " + \
              " %15s in table %s -> averaging" % (label, table)
    # ----------------------------------------------------------------------------------------------------------------
    # mpmoine_correction:analyze_cell_time_method: ajout du cas 'Maximum Hourly Rate'
    elif "time: mean within hours time: maximum over hours" in cm:
        # [amn-tdnl]: Mean Diurnal Cycle
        print "TBD: Cannot yet compute maximum hourly rate for " + \
              " %15s in table %s -> averaging" % (label, table)
        # Could output a time average of 24 hourly fields at 01 UTC, 2UTC ...
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: sum" in cm:
        # [tsum]: Temporal Sum  : pas utilisee !
        # mpmoine_correction: on utilise 'accumulate' quand un "time: sum" est demande
        operation = "accumulate"
        # TBS# print "Error: time: sum is not supposed to be used"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: mean" in cm:  # [tmean]: Time Mean
        operation = "average"
    # ----------------------------------------------------------------------------------------------------------------
    elif "time: point" in cm:
        operation = "instant"
    #
    # mpmoine_correction:analyze_cell_time_method: ajout du cas sans operation temporelle (champs fixes)
    elif not "time:" in cm:
        operation = "once"
    # ----------------------------------------------------------------------------------------------------------------
    else:
        print "Error: issue when analyzing cell_time_method " + \
              "%s for %15s in table %s, averaging" % (cm, label, table)
    # ----------------------------------------------------------------------------------------------------------------
    return (operation, detect_missing)


#
# mpmoine_amelioration: ajout argument 'path_special' a la fonction ping_file_for_realms_list
def pingFileForRealmsList(context, lrealms, svars, path_special, dummy="field_atm",
                          dummy_with_shape=False, exact=False,
                          comments=False, prefix="CV_", filename=None):
    """Based on a list of realms LREALMS and a list of simplified vars
    SVARS, create the ping file which name is ~
    ping_<realms_list>.xml, which defines fields for all vars in
    SVARS, with a field_ref which is either 'dummy' or '?<varname>'
    (depending on logical DUMMY)

    If EXACT is True, the match between variable realm string and one
    of the realm string in the list must be exact. Otherwise, the
    variable realm must be included in (or include) one of the realm list
    strings

    COMMENTS, if not False nor "", will drive the writing of variable
    description and units as an xml comment. If it is a string, it
    will be printed before this comment string (and this allows for a
    line break)

    DUMMY, if not false, should be either 'True', for a standard dummy
    label or a string used as the name of all field_refs. If False,
    the field_refs look like ?<variable name>.

    If DUMMY is True and DUMMY_WITH_SHAPE is True, dummy labels wiill
    include the highest rank shape requested by the DR, for
    information

    Field ids do include the provided PREFIX

    The ping file includes a <field_definition> construct

    For those MIP varnames which have a corresponding field_definition
    in a file named like ./inputs/DX_field_defs_<realm>.xml (path being
    relative to source code location), this latter field_def is
    inserted in the ping file (rather than a default one). This brings
    a set of 'standard' definitions fo variables which can be derived
    from DR-standard ones

    """
    name = "";
    for r in lrealms: name += "_" + r.replace(" ", "%")
    lvars = []
    for v in svars:
        if exact:
            if any([v.modeling_realm == r for r in lrealms]):
                lvars.append(v)
        else:
            if any([v.modeling_realm in r or r in v.modeling_realm
                    for r in lrealms]):
                lvars.append(v)
    # if lset["use_area_suffix"] :
    #    lvars.sort(key=lambda x:x.label_with_area)
    # else:
    # mpmoine_future_modif:ping_file_for_realms_list: on s'appuie sur le mipVar label (label_without_area) et non plus le cmorVar label
    # mpmoine_zoom_modif:ping_file_for_realms_list: on s'appuie sur le label_without_psuffix et non plus le label_without_area
    lvars.sort(key=lambda x: x.label_without_psuffix)
    # Remove duplicates
    uniques = [];
    last_label = ""
    for v in lvars:
        # mpmoine_future_modif:ping_file_for_realms_list: on s'appuie sur le mipVar label (label_without_area) et non plus le cmorVar label
        # mpmoine_zoom_modif:ping_file_for_realms_list: on s'appuie sur le label_without_psuffix et non plus le label_without_area
        if v.label_without_psuffix != last_label:
            uniques.append(v)
            # mpmoine_future_modif:ping_file_for_realms_list: on s'appuie sur le mipVar label (label_without_area) et non plus le cmorVar label
            # mpmoine_zoom_modif:ping_file_for_realms_list: on s'appuie sur le label_without_psuffix et non plus le label_without_area
            last_label = v.label_without_psuffix
    lvars = uniques
    #
    if filename is None: filename = "ping" + name + ".xml"
    # mpmoine_future_modif:ping_file_for_realms_list: typo 'filneme' -> 'filename'
    if filename[-4:] != ".xml": filename += ".xml"
    #
    # mpmoine_amelioration:ping_file_for_realms_list:: ajout argument 'path_special' a la fonction read_special_fields_defs + protection si path_special existe
    if path_special:
        specials = read_special_fields_defs(lrealms, path_special)
    else:
        specials = False
    with open(filename, "w") as fp:
        fp.write('<!-- Ping files generated by dr2xml %s using Data Request %s -->\n' % (version, dq.version))
        fp.write('<!-- lrealms= %s -->\n' % `lrealms`)
        fp.write('<!-- exact= %s -->\n' % `exact`)
        fp.write('<context id="%s">\n' % context)
        fp.write("<field_definition>\n")
        if exact:
            fp.write("<!-- for variables which realm intersects any of " \
                     + name + "-->\n")
        else:
            fp.write("<!-- for variables which realm equals one of " \
                     + name + "-->\n")
        for v in lvars:
            # mpmoine_future_modif:ping_file_for_realms_list: pour le field_id du pingfile on s'appuie sur le 'label_without_psuffix' et non plus le label complet
            # mpmoine_correction:ping_file_for_realms_list: pour le field_id du pingfile on prend le label non ambigu s'il existe
            if v.label_non_ambiguous:
                label = v.label_non_ambiguous
            else:
                label = v.label_without_psuffix
            # mpmoine_amelioration:ping_file_for_realms_list: protection si specials existe
            if specials and label in specials:
                line = ET.tostring(specials[label]).replace("DX_", prefix)
                line = line.replace("\n", "").replace("\t", "")
                fp.write('   ');
                fp.write(line)
            else:
                fp.write('   <field id="%-20s' % (prefix + label + '"') + \
                         ' field_ref="')
                if dummy:
                    # mpmoine_last_modif: svar en argument de highest_rank et non pas seulement son label_without_area
                    # mpmoine_zoom_modif:ping_file_for_realms_list: on s'appuie sur le label_without_psuffix et non plus le label_without_area
                    shape = highest_rank(v)
                    # Bugfix for DR 1.0.1 content :
                    # mpmoine_future_modif:ping_file_for_realms_list: on s'appuie sur le mipVar label (label_without_area) et non plus le cmorVar label
                    # mpmoine_zoom_modif:ping_file_for_realms_list: on s'appuie sur le label_without_psuffix et non plus le label_without_area
                    if v.label_without_psuffix == 'clcalipso': shape = 'XYA'
                    if dummy is True:
                        dummys = "dummy"
                        if dummy_with_shape: dummys += "_" + shape
                    else:
                        dummys = dummy
                    fp.write('%-18s/>' % (dummys + '"'))
                else:
                    fp.write('?%-16s' % (label + '"') + ' />')
            if comments:
                # Add units, stdname and long_name as a comment string
                if type(comments) == type(""): fp.write(comments)
                fp.write("<!-- P%d (%s) %s : %s -->" \
                         % (v.Priority, v.stdunits, v.stdname, v.description))
            fp.write("\n")
        fp.write("</field_definition>\n")
        #
        print "%3d variables written for %s" % (len(lvars), filename)
        #
        # Write axis_defs, domain_defs, ... read from relevant input/DX_ files
        # mpmoine_amelioration:ping_file_for_realms_list: protection si path_special existe
        if path_special:
            for obj in ["axis", "domain", "grid"]:
                # print "for obj "+obj
                # mpmoine_amelioration:ping_file_for_realms_list: ajout argument 'path_special' a la fonction copy_obj_from_DX_file
                copy_obj_from_DX_file(fp, obj, prefix, lrealms, path_special)
        fp.write('</context>\n')


# mpmoine_amelioration: ajout argument 'path_special' a la fonction copy_obj_from_DX_file
def copy_obj_from_DX_file(fp, obj, prefix, lrealms, path_special):
    # Insert content of DX_<obj>_defs files (changing prefix)
    # print "copying %s defs :"%obj,
    subrealms_seen = []
    for realm in lrealms:
        for subrealm in realm.split():
            if subrealm in subrealms_seen: continue
            subrealms_seen.append(subrealm)
            # print "\tand realm %s"%subrealm,
            # mpmoine_amelioration:opy_obj_from_DX_file: ajout argument 'path_special' a la fonction DX_defs_filename
            defs = DX_defs_filename(obj, subrealm, path_special)
            if os.path.exists(defs):
                with open(defs, "r") as fields:
                    # print "from %s"%defs
                    fp.write("\n<%s_definition>\n" % obj)
                    lines = fields.readlines()
                    for line in lines:
                        if not obj + "_definition" in line:
                            fp.write(line.replace("DX_", prefix))
                    fp.write("</%s_definition>\n" % obj)
            else:
                pass
                print " no file :%s " % defs


# mpmoine_amelioration: ajout argument 'path_special' a la fonction DX_defs_filename
def DX_defs_filename(obj, realm, path_special):
    # TBS# return prog_path+"/inputs/DX_%s_defs_%s.xml"%(obj,realm)
    return path_special + "/DX_%s_defs_%s.xml" % (obj, realm)


# mpmoine_future_modif: renommage de la fonction 'field_defs' en 'get_xml_childs'
def get_xml_childs(elt, tag='field', groups=['context', 'field_group',
                                             'field_definition', 'axis_definition', 'axis', 'domain_definition',
                                             'domain', 'grid_definition', 'grid', 'interpolate_axis']):
    """
        Returns a list of elements in tree ELT
        which have tag TAG, by digging in sub-elements
        named as in GROUPS
        """
    if elt.tag in groups:
        rep = []
        for child in elt: rep.extend(get_xml_childs(child, tag))
        return rep
    elif elt.tag == tag:
        return [elt]
    else:
        # print 'Syntax error : tag %s not allowed'%elt.tag
        # Case of an unkown tag : don't dig in
        return []


# mpmoine_future_modif: renommage de la fonction 'read_defs' en 'read_xml_elmt_or_attrib'
def read_xml_elmt_or_attrib(filename, tag='field', attrib=None, printout=False):
    """
    Returns a dict of objects tagged TAG in FILENAME, which
    - keys are ids
    - values are corresponding ET elements if
      attrib is None, otherwise elt attribute ATTRIB
    Returns None if filename does not exist
    """
    #
    rep = dict()
    if printout: print "processing file %s :" % filename,
    if os.path.exists(filename):
        if printout: print "OK", filename
        root = ET.parse(filename).getroot()
        defs = get_xml_childs(root, tag)
        if defs:
            for field in defs:
                if printout: print ".",
                if attrib is None:
                    rep[field.attrib['id']] = field
                else:
                    rep[field.attrib['id']] = field.attrib[attrib]
            if printout: print
            return rep
    else:
        if printout: print "No file "
        return None


# mpmoine_amelioration: ajout de l'argument 'path_special' a la fonction read_special_field_defs
def read_special_fields_defs(realms, path_special, printout=False):
    special = dict()
    subrealms_seen = []
    for realm in realms:
        for subrealm in realm.split():
            if subrealm in subrealms_seen: continue
            subrealms_seen.append(subrealm)
            # mpmoine_amelioration:read_special_fields_defs: ajout de l'argument 'path_special' a la fonction DX_defs_filename
            d = read_xml_elmt_or_attrib(DX_defs_filename("field", subrealm, path_special), \
                                        tag='field', printout=printout)
            if d: special.update(d)
    rep = dict()
    # Use raw label as key
    for r in special: rep[r.replace("DX_", "")] = special[r]
    return rep


# mpmoine_last_modif:highest_rank: svar en argument et non pas seulement son label_without_area
def highest_rank(svar):
    """Returns the shape with the highest needed rank among the CMORvars
    referencing a MIPvar with this label
    This, assuming dr2xml would handle all needed shape reductions
    """
    # mpmoine_last_modif:highest_rank: pour recuperer le label_without_area
    mipvarlabel = svar.label_without_area
    shapes = []
    for cvar in dq.coll['CMORvar'].items:
        v = dq.inx.uid[cvar.vid]
        if v.label == mipvarlabel:
            try:
                st = dq.inx.uid[cvar.stid]
                try:
                    sp = dq.inx.uid[st.spid]
                    shape = sp.label
                except:
                    if print_DR_errors:
                        # mpmoine_last_modif:highest_rank:  pour corriger l'erreur "TypeError: cannot concatenate 'str' and 'dreqItem_CoreAttributes' objects"
                        print "DR Error: issue with stid or spid for " + \
                              st.label + " " + v.label + string(cvar.mipTable)
                    # One known case in DR 1.0.2: hus in 6hPlev
                    shape = "XY"
            except:
                # mpmoine_last_modif:highest_rank:  pour corriger l'erreur "TypeError: cannot concatenate 'str' and 'dreqItem_CoreAttributes' objects"
                print "DR Error: issue with stid for " + v.label + string(cvar.mipTableSection)
                shape = "?st"
        else:
            # mpmoine_last_modif:highest_rank: Pour recuperer le spatial_shp pour le cas de variables qui n'ont pas un label CMORvar de la DR (ex. HOMEvar ou EXTRAvar)
            shape = svar.spatial_shp
        # mpmoine_future_modif:highest_rank: test shape =/ None, sinon on se retrouve avec shapes=liste de None et 1 liste de None n'est pas Faux
        if shape: shapes.append(shape)
    # if not shapes : shape="??"
    if not shapes:
        shape = "XY"
    elif any(["XY-A" in s for s in shapes]):
        shape = "XYA"
    elif any(["XY-O" in s for s in shapes]):
        shape = "XYO"
    elif any(["XY-AH" in s for s in shapes]):
        shape = "XYAh"  # Zhalf
    elif any(["XY-SN" in s for s in shapes]):
        shape = "XYSn"  # snow levels
    elif any(["XY-S" in s for s in shapes]):
        shape = "XYSo"  # soil levels
    elif any(["XY-P" in s for s in shapes]):
        shape = "XYA"
    elif any(["XY-H" in s for s in shapes]):
        shape = "XYA"
    #
    elif any(["XY-na" in s for s in shapes]):
        shape = "XY"  # analyser realm, pb possible sur ambiguite singleton
    #
    elif any(["YB-na" in s for s in shapes]):
        shape = "basin_zonal_mean"
    elif any(["YB-O" in s for s in shapes]):
        shape = "basin_merid_section"
    elif any(["YB-R" in s for s in shapes]):
        shape = "basin_merid_section_density"
    elif any(["S-A" in s for s in shapes]):
        shape = "COSP-A"
    elif any(["S-AH" in s for s in shapes]):
        shape = "COSP-AH"
    elif any(["na-A" in s for s in shapes]):
        shape = "site-A"
    elif any(["Y-A" in s for s in shapes]):
        shape = "lat-A"  # XYZ
    elif any(["Y-P" in s for s in shapes]):
        shape = "lat-P"  # XYZ
    elif any(["Y-na" in s for s in shapes]):
        shape = "lat"
    elif any(["TRS-na" in s for s in shapes]):
        shape = "TRS"
    elif any(["TR-na" in s for s in shapes]):
        shape = "TR"
    elif any(["L-na" in s for s in shapes]):
        shape = "COSPcurtain"
    elif any(["L-H40" in s for s in shapes]):
        shape = "COSPcurtainH40"
    elif any(["S-na" in s for s in shapes]):
        shape = "XY"  # fine once remapped
    elif any(["na-na" in s for s in shapes]):
        shape = "0d"  # analyser realm
    # else : shape="??"
    else:
        shape = "XY"
    return shape


def make_source_string(sources, source_id):
    """
    From the dic of sources in CMIP6-CV, Creates the string representation of a
    given model (source_id) according to doc on global_file_attributes, so :

    <modified source_id> (<year>): atmosphere: <model_name> (<technical_name>, <resolution_and_levels>); ocean: <model_name> (<technical_name>, <resolution_and_levels>); sea_ice: <model_name> (<technical_name>); land: <model_name> (<technical_name>); aerosol: <model_name> (<technical_name>); atmospheric_chemistry <model_name> (<technical_name>); ocean_biogeochemistry <model_name> (<technical_name>); land_ice <model_name> (<technical_name>);

    """
    # mpmoine_correction:make_source_string: pour lire correctement le fichier 'CMIP6_source_id.json'
    source = sources[source_id]
    components = source['model_component']
    rep = source_id + " (" + source['release_year'] + "): "
    for realm in ["aerosol", "atmos", "atmosChem", "land", "ocean", "ocnBgchem", "seaIce"]:
        component = components[realm]
        description = component['description']
        if description != "none": rep = rep + "\n" + realm + ": " + description
    return rep


def build_axis_definitions():
    """
    Build a dict of axis definitions
    """
    for g in dq.coll['grids'].items:
        pass


class dr2xml_error(Exception):
    def __init__(self, valeur):
        self.valeur = valeur

    def __str__(self):
        return `self.valeur`


print_DR_errors = True

import sys, os
import json


# GRAPHVIZ#from table2freq import table2freq
# -from dr2xml import dr2xml_error

# A class for unifying CMOR vars and home variables
# mpmoine_last_modif:simple_CMORvar: ajout des attributs 'mip_era', 'missing' et 'dimids'
# mpmoine_future_modif:simple_CMORvar: ajout de l'attribut 'label_without_psuffix' et suppresion de l'attribut dimids
# mpmoine_correction:simple_CMORvar: ajout de l'attribut 'label_non_ambiguous'
class simple_CMORvar(object):
    def __init__(self):
        self.type = False
        self.modeling_realm = None
        self.grids = [""]
        self.label = None  # taken equal to the CMORvar label
        self.label_without_area = None  # taken equal to MIPvar label
        self.label_without_psuffix = None
        self.label_non_ambiguous = None
        self.frequency = None
        self.mipTable = None
        self.positive = None
        self.description = None
        self.stdname = None
        self.stdunits = None
        self.long_name = None
        self.struct = None
        self.sdims = {}
        self.cell_methods = None
        self.cell_measures = None
        self.spatial_shp = None
        self.temporal_shp = None
        self.experiment = None
        self.mip = None
        self.Priority = 1  # Will be changed using DR or extra-Tables
        self.mip_era = False  # Later changed in project name (uppercase) when appropriate
        self.missing = 1.e+20


# mpmoine_future_modif: nouvelle classe simple_Dim
# A class for unifying grid info coming from DR and extra_Tables
# mpmoine_future_modif:simple_Dim: ajout de l'attribut 'is_zoom_of'
# mpmoine_zoom_modif:simple_Dim: ajout de l'attribut 'zoom_label'
#
class simple_Dim(object):
    def __init__(self):
        self.label = False
        self.zoom_label = False
        self.stdname = False
        self.long_name = False
        self.positive = False
        self.requested = ""
        self.value = False
        self.out_name = False
        self.units = False
        self.is_zoom_of = False
        # mpmoine_union_optim: simple_Dim: ajout de l'attribut 'is_union_for'
        self.is_union_for = []


# mpmoine_future_modif: liste des suffixes de noms de variables reperant un ou plusieurs niveaux pression
# List of multi and single pressure level suffixes for which we want the union/zoom axis mecanism turned on
# For not using union/zoom, set 'use_union_zoom' to False in lab settings
multi_plev_suffixes = set(["10", "19", "23", "27", "39", "3", "3h", "4", "7c", "7h", "8", "12"])
single_plev_suffixes = set(["1000", "200", "220", "500", "560", "700", "840", "850", "100"])
# multi_plev_suffixes=set()
# single_plev_suffixes=set()

ambiguous_mipvarnames = None

# 2 dicts for processing home variables
# mpmoine_last_modif: vars.py: spid2label et tmid2label ne sont plus utilises
# 2 dicts and 1 list for processing extra variables
dims2shape = {}
dim2dimid = {}
dr_single_levels = []
stdName2mipvarLabel = {}


# mpmoine_last_modif:read_home_vars_list: fonction modifiee pour accepter des extra_Tables
def read_homeVars_list(hmv_file, expid, mips, dq, path_extra_tables=None):
    """
    A function to get HOME variables that are not planned in the CMIP6 DataRequest but
    the lab want to outpuut anyway

    Args:
      hmv_file (string) : a text file containing the list of home variables
      expid (string) : if willing to filter on a given experiment
      mips (string)  : if willing to filter on  given mips
      path_extra_tables (string): path where to find extra Tables. Mandatory only if
                                  there is'extra' lines in list of home variables.

    Returns:
      A list of 'simplified CMOR variables'
    """
    #
    # File structure: name of attributes to read, number of header line
    home_attrs = ['type', 'label', 'modeling_realm', 'frequency', 'mipTable', 'temporal_shp', 'spatial_shp',
                  'experiment', 'mip']
    skip = 3
    if not os.path.exists(hmv_file): sys.exit("Abort: file for home variables does not exist: " + hmv_file)
    # Read file
    with open(hmv_file, "r") as fp:
        data = fp.readlines()
    # Build list of home variables
    homevars = []
    extravars = []
    for line in data[skip:]:
        line_split = line.split(';')
        # get the Table full name
        table = line_split[4].strip(' ')
        # overwrite  5th column with table name without prefix
        if table != 'NONE':
            if '_' not in table: sys.exit("Abort: a prefix is expected in extra Table name: " + table)
            line_split[4] = table.split('_')[1]
        hmv_type = line_split[0].strip(' ')
        if hmv_type != 'extra':
            home_var = simple_CMORvar()
            cc = -1
            for col in line_split:
                ccol = col.lstrip(' ').rstrip('\n\t ')
                if ccol != '':
                    cc += 1
                    setattr(home_var, home_attrs[cc], ccol)
            home_var.label_with_area = home_var.label
            if hmv_type == 'perso':
                home_var.mip_era = 'PERSO'
                # mpmoine_future_modif:read_home_vars_list: valorisation de home_var.label_without_psuffix
                home_var.label_without_psuffix = home_var.label
            if home_var.mip != "ANY":
                if home_var.mip in mips:
                    if home_var.experiment != "ANY":
                        if home_var.experiment == expid: homevars.append(home_var)
                    else:
                        homevars.append(home_var)
            else:
                if home_var.experiment != "ANY":
                    if home_var.experiment == expid: homevars.append(home_var)
                else:
                    homevars.append(home_var)
        else:
            extra_vars = read_extraTable(path_extra_tables, table, dq, printout=False)
            extravars.extend(extra_vars)
    print "Number of 'cmor' and 'perso' among home variables: ", len(homevars)
    print "Number of 'extra' among home variables: ", len(extravars)
    homevars.extend(extravars)
    return homevars


# mpmoine_last_modif:read_extra_table: nouvelle fonction pour lire les extra_Tables
def read_extraTable(path, table, dq, printout=False):
    """
    A function to get variables contained in an EXTRA Table that are is planned in the CMIP6 DataRequest but
    the lab want to output anyway. EXTRA Table is expected in JSON format, conform with the CMOR3 convention.

    Args:
      path (string) : the path where the extra table are located (must include the table name prefix, if any).
      table (string): table name (with its prefix, e.g. 'CMIP6_Amon', 'PRIMAVERA_Oday').
                      Table prefix, if present, is supposed to correspond to : '<mip_era>_'.
      printout (boolean,optional) : enhanced verbosity

    Returns:
      A list of 'simplified CMOR variables'
    """
    #
    if not dims2shape:
        for sshp in dq.coll['spatialShape'].items:
            dims2shape[sshp.dimensions] = sshp.label
        # mpmoine_future_modif:dims2shape: ajout a la main des correpondances dims->shapes Primavera qui ne sont pas couvertes par la DR
        # mpmoine_note: attention, il faut mettre a jour dim2shape a chaque fois qu'une nouvelle correpondance est introduite
        # mpmoine_note: attention, dans les extra-Tables
        dims2shape['longitude|latitude|height100m'] = 'XY-na'
        # mpmoine_note: provisoire, XY-P12 juste pour exemple
        dims2shape['longitude|latitude|plev12'] = 'XY-P12'
        # mpmoine_zoom_modif:dims2shape:: ajout de XY-P23 qui a disparu de la DR-00.00.04 mais est demande dans les tables Primavera
        dims2shape['longitude|latitude|plev23'] = 'XY-P23'
        # mpmoine_zoom_modif:dims2shape:: ajout de XY-P10 qui n'est pas dans la DR mais demande dans les tables Primavera
        dims2shape['longitude|latitude|plev10'] = 'XY-P10'
    #
    if not dim2dimid:
        for g in dq.coll['grids'].items:
            dim2dimid[g.label] = g.uid
    #
    # mpmoine_correction:read_extra_table: Solution de Martin Juckes du 04/05/2017 en utilisant cids necessaire a partir de la version 01.00.08 => plus besoin de la fonction 'cids2singlev'
    if not dr_single_levels:
        for struct in dq.coll['structure'].items:
            spshp = dq.inx.uid[struct.spid]
            if spshp.label == "XY-na" and 'cids' in struct.__dict__:
                if struct.cids[0] != '':  ## this line is needed prior to version 01.00.08.
                    c = dq.inx.uid[struct.cids[0]]
                    # if c.axis == 'Z': # mpmoine_note: non car je veux dans dr_single_levels toutes les dimensions singletons (ex. 'typenatgr'), par seulement les niveaux
                    dr_single_levels.append(c.label)
        # other single levels in extra Tables, not in DR
        # mpmoine: les ajouts ici correspondent  aux single levels Primavera.
        other_single_levels = ['height50m', 'p100']
        dr_single_levels.extend(other_single_levels)
    #
    extravars = []
    dr_slevs = dr_single_levels
    mip_era = table.split('_')[0]
    json_table = path + "/" + table + ".json"
    json_coordinate = path + "/" + mip_era + "_coordinate.json"
    if not os.path.exists(json_table): sys.exit("Abort: file for extra Table does not exist: " + json_table)
    tbl = table.split('_')[1]
    with open(json_table, "r") as jt:
        json_tdata = jt.read()
        tdata = json.loads(json_tdata)
        # mpmoine_correction:read_extra_table: read_extra_table: ajout de precautions 'NOT-SET' pour certains attributs pour eviter les chaines vides qui font planter XIOS (">  <")
        for k, v in tdata["variable_entry"].iteritems():
            extra_var = simple_CMORvar()
            extra_var.type = 'extra'
            extra_var.mip_era = mip_era
            extra_var.label = v["out_name"].strip(' ')
            extra_var.stdname = v["standard_name"].strip(' ')
            extra_var.long_name = v["long_name"].strip(' ')
            extra_var.stdunits = v["units"].strip(' ')
            extra_var.modeling_realm = v["modeling_realm"].strip(' ')
            extra_var.frequency = table2freq[tbl][1]
            extra_var.mipTable = tbl
            extra_var.cell_methods = v["cell_methods"].strip(' ')
            extra_var.cell_measures = v["cell_measures"].strip(' ')
            extra_var.positive = v["positive"].strip(' ')
            prio = mip_era.lower() + "_priority"
            extra_var.Priority = float(v[prio])
            # Tranlate full-dimensions read in Table (e.g. "longitude latitude time p850")
            # into DR spatial-only dimensions (e.g. "longitude|latitude")
            dims = (v["dimensions"]).split(" ")
            # get the index of time dimension to supress, if any
            inddims_to_sup = []
            dsingle = None
            for d in dims:
                if "time" in d:
                    dtime = d
                    inddims_to_sup.append(dims.index(dtime))
                    ind_time = [dims.index(dtime)]
                # get the index of single level to suppress, if any
                for sl in dr_slevs:
                    if d == sl:
                        dsingle = d
                        inddims_to_sup.append(dims.index(dsingle))
                        # supress dimensions corresponding to time and single levels
            dr_dims = [d for i, d in enumerate(dims) if i not in inddims_to_sup]
            # supress only the dimension corresponding to time
            all_dr_dims = [d for i, d in enumerate(dims) if i not in ind_time]
            # rewrite dimension with DR convention
            drdims = ""
            for d in dr_dims:
                if drdims:
                    drdims = drdims + "|" + d
                else:
                    drdims = d
            if dims2shape.has_key(drdims):
                extra_var.spatial_shp = dims2shape[drdims]
            else:
                # mpmoine_note: provisoire, on devrait toujours pouvoir associer une spatial shape a des dimensions.
                # mpmoine_note: Je rencontre ce cas pour l'instant avec les tables Primavera ou
                # mpmoine_note: on a "latitude|longitude" au lieu de "longitude|latitude"
                print "Warning: spatial shape corresponding to ", drdims, "for variable", v["out_name"], \
                    "in Table", table, " not found in DR."
            # list of spatial dimension identifiers
            # mpmoine_future_modif:read_extra_table: introduction de extra_var.sdims, ajout lecture des dimensions dans
            # mpmoine_future_modif:read_extra_table: une table de coordinates quand pas trouvees dans la DR
            dr_dimids = []
            for d in all_dr_dims:
                if dim2dimid.has_key(d):
                    dr_dimids.append(dim2dimid[d])
                    extra_dim = get_simpleDim_from_DimId(dim2dimid[d], dq)
                    extra_var.sdims.update({extra_dim.label: extra_dim})
                else:
                    extra_sdim = simple_Dim()
                    with open(json_coordinate, "r") as jc:
                        json_cdata = jc.read()
                        cdata = json.loads(json_cdata)
                        extra_sdim.label = d
                        extra_sdim.stdname = cdata["axis_entry"][d]["standard_name"]
                        extra_sdim.units = cdata["axis_entry"][d]["units"]
                        extra_sdim.long_name = cdata["axis_entry"][d]["long_name"]
                        extra_sdim.out_name = cdata["axis_entry"][d]["out_name"]
                        extra_sdim.positive = cdata["axis_entry"][d]["positive"]
                        string_of_requested = ""
                        for ilev in cdata["axis_entry"][d]["requested"]:
                            string_of_requested = string_of_requested + " " + ilev
                        extra_sdim.requested = string_of_requested.rstrip(" ")  # values of multi vertical levels
                        extra_sdim.value = cdata["axis_entry"][d]["value"]  # value of single vertical level
                    extra_var.sdims.update({extra_sdim.label: extra_sdim})
                    print "Info: dimid corresponding to ", d, "for variable", v["out_name"], \
                        "in Table", table, " not found in DR => read it in extra coordinates Table: ", extra_sdim.stdname, extra_sdim.requested
            # mpmoine_future_modif: read_extra_table: suppression de extra_var.dimids -> elargi avec extra_var.sdims
            # mpmoine_future_modif:read_extra_table: on renseigne l'attribut label_without_psuffix (doit etre fait apres la valorisation de sdims)
            extra_var.label_without_psuffix = Remove_pSuffix(extra_var, multi_plev_suffixes, single_plev_suffixes,
                                                             realms='atmos aerosol atmosChem')

            extravars.append(extra_var)
    if printout:
        print "Info: Number of variables in extra tables ", table, ": ", len(extravars)
    return extravars


def get_SpatialAndTemporal_Shapes(cmvar, dq):
    # mpmoine_last_modif:get_spatial_and_temporal_shapes: le try/except n'etait pas la bonne solution
    spatial_shape = False
    temporal_shape = False
    if cmvar.stid == "__struct_not_found_001__":
        if print_DR_errors:
            print "Warning: stid for ", cmvar.label, " in table ", cmvar.mipTable, " is a broken link to structure in DR: ", cmvar.stid
    else:
        for struct in dq.coll['structure'].items:
            if struct.uid == cmvar.stid:
                spatial_shape = dq.inx.uid[struct.spid].label
                temporal_shape = dq.inx.uid[struct.tmid].label
    if print_DR_errors:
        if not spatial_shape:
            print "Warning: spatial shape for ", cmvar.label, " in table ", cmvar.mipTable, " not found in DR."
        if not temporal_shape:
            print "Warning: temporal shape for ", cmvar.label, " in table ", cmvar.mipTable, " not found in DR."
    return [spatial_shape, temporal_shape]


# mpmoine_last_modif: process_home_vars: argument supplementaire 'path_extra_tables' et expid au lieu de lset
def process_homeVars(lset, mip_vars_list, dq, expid=False, printout=False):
    printmore = False
    # Read HOME variables
    home_vars_list = read_homeVars_list(lset['listof_home_vars'],
                                        expid, lset['mips'], dq, lset['path_extra_tables'])
    for hv in home_vars_list:
        hv_info = {"varname": hv.label, "realm": hv.modeling_realm,
                   "freq": hv.frequency, "table": hv.mipTable}
        # if printout : print hv_info
        if hv.type == 'cmor':
            # Complement each HOME variable with attributes got from
            # the corresponding CMOR variable (if exist)
            updated_hv = get_corresp_CMORvar(hv, dq)
            if (updated_hv):
                already_in_dr = False
                for cmv in mip_vars_list:
                    matching = (cmv.label == updated_hv.label and \
                                cmv.modeling_realm == updated_hv.modeling_realm and \
                                cmv.frequency == updated_hv.frequency and \
                                cmv.mipTable == updated_hv.mipTable and \
                                cmv.temporal_shp == updated_hv.temporal_shp and \
                                cmv.spatial_shp == updated_hv.spatial_shp)
                    if matching: already_in_dr = True

                # Corresponding CMOR Variable found
                if not already_in_dr:
                    # Append HOME variable only if not already
                    # selected with the DataRequest
                    if printmore: print "Info:", hv_info, \
                        "HOMEVar is not in DR." \
                        " => Taken into account."
                    mip_vars_list.append(updated_hv)
                else:
                    if printmore:
                        print "Info:", hv_info, \
                            "HOMEVar is already in DR." \
                            " => Not taken into account."
            else:
                if printout:
                    print "Error:", hv_info, \
                        "HOMEVar announced as cmor but no corresponding " \
                        " CMORVar found => Not taken into account."
                    dr2xml_error("Abort: HOMEVar is cmor but no corresponding" \
                                 " CMORVar found.")
        elif hv.type == 'perso':
            # Check if HOME variable anounced as 'perso' is in fact 'cmor'
            is_cmor = get_corresp_CMORvar(hv, dq)
            if not is_cmor:
                # Check if HOME variable differs from CMOR one only by shapes
                has_cmor_varname = any([cmvar.label == hv.label for
                                        cmvar in dq.coll['CMORvar'].items])
                # hasCMORVarName(hv)
                if has_cmor_varname:
                    if printout:
                        print "Warning:", hv_info, "HOMEVar is anounced " \
                                                   " as perso, is not a CMORVar, but has a cmor name." \
                                                   " => Not taken into account."
                    dr2xml_error("Abort: HOMEVar is anounced as perso," \
                                 " is not a CMORVar, but has a cmor name.")
                else:
                    if printmore: print "Info:", hv_info, \
                        "HOMEVar is purely personnal. => Taken into account."
                    mip_vars_list.append(hv)
            else:
                if printout:
                    print "Error:", hv_info, "HOMEVar is anounced as perso," \
                                             " but in reality is cmor => Not taken into account."
                dr2xml_error("Abort: HOMEVar is anounced as perso but " \
                             "should be cmor.")
        # mpmoine_last_modif: process_home_vars: ajout du cas type='extra'
        elif hv.type == 'extra':
            if hv.Priority <= lset["max_priority"]:
                if printmore: print "Info:", hv_info, "HOMEVar is read in an extra Table with priority " \
                    , hv.Priority, " => Taken into account."
                mip_vars_list.append(hv)
        else:
            if printout:
                print "Error:", hv_info, "HOMEVar type", hv.type, \
                    "does not correspond to any known keyword." \
                    " => Not taken into account."
            dr2xml_error("Abort: unknown type keyword provided " \
                         "for HOMEVar %s:" % `hv_info`)


def get_corresp_CMORvar(hmvar, dq):
    collect = dq.coll['CMORvar']
    count = 0
    for cmvar in collect.items:
        # Consider case where no modeling_realm associated to the
        # current CMORvar as matching anymay.
        # mpmoine_TBD: A mieux gerer avec les orphan_variables ?
        match_label = (cmvar.label == hmvar.label)
        match_freq = (cmvar.frequency == hmvar.frequency)
        match_table = (cmvar.mipTable == hmvar.mipTable)
        match_realm = (hmvar.modeling_realm in cmvar.modeling_realm.split(' '))
        empty_realm = (cmvar.modeling_realm == '')
        matching = (match_label and match_freq and match_table and \
                    (match_realm or empty_realm))
        if matching:
            same_shapes = (get_SpatialAndTemporal_Shapes(cmvar, dq) == \
                           [hmvar.spatial_shp, hmvar.temporal_shp])
            if same_shapes:
                count += 1
                cmvar_found = cmvar
            else:
                print "Error: ", [hmvar.label, hmvar.mipTable], \
                    "HOMEVar: Spatial and Temporal Shapes specified " \
                    "DO NOT match CMORvar ones." \
                    " -> Provided:", [hmvar.spatial_shp, hmvar.temporal_shp], \
                    'Expected:', get_SpatialAndTemporal_Shapes(cmvar, dq)
    if count == 1:
        complement_svar_using_cmorvar(hmvar, cmvar_found, dq)
        return hmvar
    return False


def complement_svar_using_cmorvar(svar, cmvar, dq):
    """
    The label for SVAR will be suffixed by an area name it the
    MIPvarname is ambiguous for that

    Used by get_corresp_cmor_var and by select_cmor_vars_for_lab
    """
    global ambiguous_mipvarnames
    if ambiguous_mipvarnames is None:
        ambiguous_mipvarnames = analyze_ambiguous_MIPvarnames(dq)

    # mpmoine_last_modif: spid2label et tmid2label ne sont plus utilises

    # mpmoine_future_modif:complement_svar_using_cmorvar: reorganisation des lignes de code

    # Get information form CMORvar
    svar.frequency = cmvar.frequency.rstrip(' ')
    svar.mipTable = cmvar.mipTable.rstrip(' ')
    svar.Priority = cmvar.defaultPriority
    svar.positive = cmvar.positive.rstrip(' ')
    svar.modeling_realm = cmvar.modeling_realm.rstrip(' ')
    svar.label = cmvar.label.rstrip(' ')
    [svar.spatial_shp, svar.temporal_shp] = get_SpatialAndTemporal_Shapes(cmvar, dq)

    # Get information from MIPvar
    # mpmoine_next_modif:complement_svar_using_cmorvar: gestion d'exception pour l'acces a la 'mipvar'
    try:
        mipvar = dq.inx.uid[cmvar.vid]
        svar.label_without_area = mipvar.label.rstrip(' ')
        # mpmoine_correction:complement_svar_using_cmorvar: le long_name doit etre le title de la CMORvar et non pas de la MIPvar
        # TBS# svar.long_name = mipvar.title
        svar.long_name = cmvar.title.rstrip(' ')
        if mipvar.description:
            svar.description = mipvar.description.rstrip(' ')
        else:
            svar.description = mipvar.title
        svar.stdunits = mipvar.units.rstrip(' ')
        sn = None
        try:
            sn = dq.inx.uid[mipvar.sn]
        except:
            pass
            # print "Issue accessing sn for %s %s!"%(cmvar.label,cmvar.mipTable)
        if sn and sn._h.label == 'standardname':
            svar.stdname = sn.uid.rstrip(' ')
            # svar.stdunits = stdname.units
            # svar.description = stdname.description
        else:
            # If CF standard name is NOK, let us use MIP variables attributes
            svar.stdname = mipvar.label.rstrip(' ')
            if print_DR_errors:
                print "DR Error: issue with stdname for " + svar.label, "in", svar.mipTable, " => take the MIPvar label instead."
    except:
        if print_DR_errors:
            print "DR Error: issue with MIPvar for " + svar.label, " => no label_without_area, long_name, stdname, description and units derived."
    #
    # Get information form Structure
    try:
        st = dq.inx.uid[cmvar.stid]
        svar.struct = st
        try:
            svar.cm = dq.inx.uid[st.cmid].cell_methods
            svar.cell_methods = dq.inx.uid[st.cmid].cell_methods.rstrip(' ')
        except:
            if print_DR_errors: print "DR Error: issue with cell_method for " + st.label
            # TBS# svar.cell_methods=None
        try:
            svar.cell_measures = dq.inx.uid[cmvar.stid].cell_measures.rstrip(' ')
        except:
            if print_DR_errors: print "DR Error: Issue with cell_measures for " + `cmvar`
        # mpmoine_last_modif:complement_svar_using_cmorvar: on affecte ici svar.dimids (avant: dans create_xios_field_ref)
        # mpmoine_last_modif:complement_svar_using_cmorvar: provisoire, pour by-passer le cas d'une CMORvar qui n'a pas de structure associee ('dreqItem_remarks')
        # mpmoine_future_modif:complement_svar_using_cmorvar: on ne recherche les dimids que si on a pas affaire a une constante
        if svar.spatial_shp != "na-na":
            try:
                spid = dq.inx.uid[svar.struct.spid]
                try:
                    # mpmoine_future_modif:complement_svar_using_cmorvar: suppression de svar.dimids -> elargi avec svar.sdims
                    dimids = spid.dimids
                    # mpmoine_future_modif:complement_svar_using_cmorvar: on rajoute les single levels dans le traitement des dimensions (dimids->all_dimids)
                    all_dimids = dimids
                    # mpmoine_correction: Solution de Martin Juckes du 04/05/2017 en utilisant cids necessaire a partir de la version 01.00.08
                    if 'cids' in svar.struct.__dict__:
                        cids = svar.struct.cids
                        # when cids not empty, cids=('dim:p850',) or ('dim:typec4pft', 'dim:typenatgr') for e.g.; when empty , cids=('',).
                        if cids[0] != '':  ## this line is needed prior to version 01.00.08.
                            all_dimids += cids
                    # mpmoine_future_modif:complement_svar_using_cmorvar: on rajoute les single levels dans le traitement des dimensions (dimids->all_dimids)
                    for dimid in all_dimids:
                        # mpmoine_future_modif:complement_svar_using_cmorvar: on valorise svar.sdims avec la fonction get_simple_dim_from_dim_id
                        sdim = get_simpleDim_from_DimId(dimid, dq)
                        svar.sdims.update({sdim.label: sdim})
                except:
                    if print_DR_errors:
                        print "DR Error: issue with dimids for ", svar.label, "in Table ", svar.mipTable, " => no sdims derived."
            except:
                if print_DR_errors:
                    print "DR Error: issue with spid for ", svar.label, "in Table ", svar.mipTable, " => no sdims derived."
    except:
        if print_DR_errors:
            print "DR Error: issue with stid for", svar.label, "in Table ", svar.mipTable, "  => no cell_methods, cell_measures, dimids and sdims derived."

    area = cellmethod2area(svar.cell_methods)
    if area:
        ambiguous = any([svar.label == alabel and svar.modeling_realm == arealm
                         for (alabel, (arealm, lmethod)) in ambiguous_mipvarnames])
        if ambiguous:
            # Special case for a set of land variables
            if not (svar.modeling_realm == 'land' and svar.label[0] == 'c'):
                # mpmoine_correction:complement_svar_using_cmorvar: la levee d'ambiguite par ajour de "_land" par ex., ne doit pas impacter le svar.label
                # mpmoine_correction:complement_svar_using_cmorvar: sinon le "_land " se retrouve dans le nom du fichier netcdf
                # TBS# svar.label=svar.label+"_"+area
                svar.label_non_ambiguous = svar.label + "_" + area
    # mpmoine_future_modif:complement_svar_using_cmorvar: on renseigne l'attribut label_without_psuffix (doit etre fait apres la valorisation de sdims)
    # mpmoine_further_zoom_modif:complement_svar_using_cmorvar: deplacement de remove_p_suffix apres la levee d'ambiguite 'where something' (verifie: aucune des variables ambigues n'est demandee en plev)
    # removing pressure suffix must occur after raising ambuguities (add of area suffix) because this 2 processes cannot be cummulate at this stage.
    # this is acceptable since none of the variables requeted on pressure levels have ambiguous names.
    svar.label_without_psuffix = Remove_pSuffix(svar, multi_plev_suffixes, single_plev_suffixes,
                                                realms='atmos aerosol atmosChem')
    #
    # Fix type and mip_era
    svar.type = 'cmor'
    # mpm_last_modif:complement_svar_using_cmorvar: mip_era='CMIP6' dans le cas CMORvar
    svar.mip_era = 'CMIP6'


# momoine_future_modif: nouvelle fonction get_simple_dim_from_dim_id utilisee par complement_svar_using_cmorvar et read_extra_Tables
def get_simpleDim_from_DimId(dimid, dq):
    sdim = simple_Dim()
    d = dq.inx.uid[dimid]
    sdim.label = d.label
    sdim.positive = d.positive
    sdim.requested = d.requested
    sdim.value = d.value
    sdim.stdname = dq.inx.uid[d.standardName].uid
    sdim.long_name = d.title
    sdim.out_name = d.altLabel
    sdim.units = d.units
    return sdim


# mpmoine_future_modif: nouvelle fonction remove_p_suffix
def Remove_pSuffix(svar, mlev_sfxs, slev_sfxs, realms):
    #
    # remove suffixes only if both suffix of svar.label *and* suffix of one of the svar.dims.label  match the search suffix
    # to avoid truncation of variable names like 'ch4' requested on 'plev19', where '4' does not stand for a plev set
    #
    # mpmoine_zoom_modif:remove_p_suffix: correction de la methode de suppression du suffixe de pression (corrige notamment ta23 -> ta2, 3 etant dans la liste des suffixes)
    import re
    r = re.compile("([a-zA-Z]+)([0-9]+)")
    #
    # mpmoine_correction:write_xios_file_def_for_svar:remove_p_suffix: suppression des terminaisons en "Clim" le cas echant
    split_label = svar.label.split("Clim")
    label_out = split_label[0]
    #
    svar_realms = set(svar.modeling_realm.split())
    valid_realms = set(realms.split())
    if svar_realms.intersection(valid_realms):
        mvl = r.match(label_out)
        if mvl and any(label_out.endswith(s) for s in mlev_sfxs.union(slev_sfxs)):
            for sdim in svar.sdims.values():
                mdl = r.match(sdim.label)
                if mdl and mdl.group(2) == mvl.group(2):
                    label_out = mvl.group(1)
    return label_out


def cellmethod2area(method):
    """
    Analyze METHOD to identify if its part related to area includes
    some key words which describe given area types
    """
    if method is None: return None
    if "where floating_ice_shelf" in method: return "fisf"
    if "where grounded_ice_shelf" in method: return "gisf"
    if "where snow over sea_ice area" in method: return "sosi"
    if "where ice_free_sea over sea " in method: return "ifs"
    if "where land" in method: return "land"
    if "where sea_ice" in method: return "si"
    if "where sea" in method: return "sea"
    if "where snow" in method: return "snow"
    if "where cloud" in method: return "cloud"
    if "where landuse" in method: return "lu"
    if "where ice_shelf" in method: return "isf"


def analyze_ambiguous_MIPvarnames(dq):
    """
    Return the list of MIP varnames whose list of CMORvars for a single realm
    show distinct values for the area part of the cell_methods
    """
    # Compute a dict which keys are MIP varnames and values = list
    # of CMORvars items for the varname
    d = dict()
    for v in dq.coll['var'].items:
        if v.label not in d: d[v.label] = []
        refs = dq.inx.iref_by_sect[v.uid].a['CMORvar']
        for r in refs:
            d[v.label].append(dq.inx.uid[r])
            # if v.label=="prra" : print "one prra"
    # print "d[prra]=",d["prra"]
    # Replace dic values by dic of cell_methods
    for vlabel in d:
        if len(d[vlabel]) > 1:
            cvl = d[vlabel]
            d[vlabel] = dict()
            for cv in cvl:
                st = dq.inx.uid[cv.stid]
                try:
                    cm = dq.inx.uid[st.cmid].cell_methods
                    # mpmoine_a_verifier: certaines de ces chaines n existent pas dans les cell_methods de la DR
                    cm1 = cm.replace("time: mean", "").replace("time: point", ""). \
                        replace(" within years  over years", ""). \
                        replace('time: maximum within days  over days', ''). \
                        replace('time: minimum within days  over days', ''). \
                        replace('time: minimum', ''). \
                        replace('time: maximum', ''). \
                        replace('with samples ', '')
                    realm = cv.modeling_realm
                    if realm == "ocean" or realm == "ocnBgchem":
                        cm1 = cm1.replace("area: mean where sea ", "")
                    # if realm=='land':
                    #    cm1=cm1.replace('area: mean where land ','')
                    if True or "area:" in cm1:
                        cm2 = cm1  # .replace("area:","")
                        if realm not in d[vlabel]:
                            d[vlabel][realm] = []
                        if cm2 not in d[vlabel][realm]:
                            d[vlabel][realm].append(cm2)
                        # if vlabel=="prra" :
                        #    print "cm2=",cm2, d[vlabel]
                except:
                    pass
                    # print "No cell method for %s %s"%(st.label,cv.label)
        else:
            d[vlabel] = None
    # for l in d : print l,d[l]
    # print "d[prra]=",d["prra"]
    # sd=d.keys() ; sd.sort()
    # for var in sd :
    #    if d[var] and any( [ len(l) > 1 for l in d[var].values() ]) :
    #        print "%20s %s"%(var,`d[var]`)
    #        pass
    # Analyze ambiguous cases regarding area part of the cell_method
    ambiguous = []
    for vlabel in d:
        if d[vlabel]:
            # print vlabel,d[vlabel]
            for realm in d[vlabel]:
                if len(d[vlabel][realm]) > 1 and \
                        any(["area" in cm for cm in d[vlabel][realm]]):
                    ambiguous.append((vlabel, (realm, d[vlabel][realm])))
    return ambiguous


"""
Management of output grids 

Principles : the Data Request may specify which grid to use : either native or a common, regular, one. This specifed per requestLink, which means per set of variables and experiments. 

dr2xml allows for the lab to choose among various policy  :
   - DR or None : always follow DR spec
   - native     : never not follow DR spec (always use native or close-to-native grid)
   - native+DR  : always produce on the union of grids
   - adhoc      : decide on each case, based on CMORvar attributes, using a 
                  lab-specific scheme implemented in a lab-provided Python 
                  function which should replace function lab_adhoc_grid_policy

Also : management of fields size/split_frequency 

"""


# GRAPHVIZ#from table2freq import table2freq
# -from dr2xml import dr2xml_error

def normalize(grid):
    """ in DR 1.0.2, values are :
    ['', 'model grid', '100km', '50km or smaller', 'cfsites', '1deg', '2deg', '25km or smaller', 'native']"""
    if grid in ["native", "model grid", ""]: return ""
    return grid.replace(" or smaller", "")


def decide_for_grids(cmvarid, grids, lset, dq):
    """
    Decide which set of grids a given variable should be produced on

    CMVARID is uid of the CMORvar
    GRIDS is a list of strings for grid as specified in requestLink
    LSET is the laboratory settings dictionnary. It carries a policy re. grids

    Returns a list of grid strings (with some normalization) (see below)

    TBD : use Martin's acronyms for grid policy
    """
    #
    # Normalize grids list and and remove duplicates
    ngrids = map(normalize, grids)
    sgrids = set()
    for g in ngrids: sgrids.add(g)
    ngrids = list(sgrids)
    #
    policy = lset.get("grid_policy")
    if policy is None or policy == "DR":  # Follow DR spec
        return ngrids
    elif policy == "native":  # Follow lab grids choice (gr or gn depending on context - see lset['grids"])
        return [""]
    elif policy == "native+DR":  # Produce both in 'native' and DR grid
        return list(sgrids.add(''))
    elif policy == "adhoc":
        return lab_adhoc_grid_policy(cmvarid, ngrids, lset, dq)
    else:
        dr2xml_error("Invalid grid policy %s" % policy)


def lab_adhoc_grid_policy(cmvarid, grids, lset, dq):
    """
    Decide , in a lab specific way, which set of grids a given
    variable should be produced on You should re-engine code below to
    your own decision scheme, if the schemes of the standard grid
    policy choices (see fucntion decide_for_grid) do not fit

    CMVARID is uid of the CMORvar
    GRIDS is a list of strings for grid as specified in requestLink (with some normalization)
    LSET is the laboratory settings dictionnary. It carries a policy re. grids

    Returns either a single grid string or a list of such strings
    """
    return CNRM_grid_policy(cmvarid, grids, lset, dq)


def CNRM_grid_policy(cmvarid, grids, lset, dq):  # TBD
    """
    See doc of lab_adhoc_grid_policy
    """
    if dq.inx.uid[cmvarid].label in ["tos", "sos"]: return (["", "1deg"])
    if "cfsites" in grids: return ["", "cfsites"]
    return [""]


def grid2resol(grid):
    """ Returns string for nominal_resolution for a DR grid name"""
    if grid == "1deg": return "1x1 degree"
    return ("undescribed")


def grid2desc(grid):
    """ Returns string for grid description for a DR grid name"""
    if grid == "1deg":
        return "data regridded to a CMIP6 standard 1x1 degree latxlon grid from the native grid"
    return ("no description for this grid")


def field_size(svar, mcfg):
    # ['nho','nlo','nha','nla','nlas','nls','nh1']  /  nz = sc.mcfg['nlo']
    nb_cosp_sites = 129
    nb_curtain_sites = 1000  # TBD : better estimate of 'curtain' size
    # TBD : better size estimates for atmosphere/ocean zonal means, and ocean transects
    nb_lat = mcfg['nh1']  # TBC
    nb_lat_ocean = mcfg['nh1']
    ocean_transect_size = mcfg['nh1']  # TBC, mais comment le calculer ?
    #
    siz = 0
    s = svar.spatial_shp
    if (s == "XY-A"):  # Global field on model atmosphere levels
        siz = mcfg['nla'] * mcfg['nha']
    elif (s == "XY-AH"):  # Global field on model atmosphere half-levels
        siz = (mcfg['nla'] + 1) * mcfg['nha']
    elif (s == "XY-P7T"):  # Global field (7 pressure tropospheric levels)
        siz = 7 * mcfg['nha']
    elif (s[0:4] == "XY-P"):  # Global field (pressure levels)
        siz = int(s[4:]) * mcfg['nha']
    elif (s[0:4] == "XY-H"):  # Global field (altitudes)
        siz = int(s[4:]) * mcfg['nha']

    elif (s == "S-AH"):  # Atmospheric profiles (half levels) at specified sites
        siz = (mcfg['nla'] + 1) * nb_cosp_sites
    elif (s == "S-A"):  # Atmospheric profiles at specified sites
        siz = mcfg['nla'] * nb_cosp_sites
    elif (s == "S-na"):  # Site (129 specified sites)
        siz = nb_cosp_sites

    elif (s == "L-na"):  # COSP curtain
        siz = nb_curtain_sites
    elif (s == "L-H40"):  # Site profile (at 40 altitudes)
        siz = 40 * nb_curtain_sites

    elif (s == "Y-P19"):  # Atmospheric Zonal Mean (on 19 pressure levels)
        # mpmoine_next_modif:field_size: nb_lat au lieu de nblat (vu par Arnaud)
        siz = nb_lat * 19
    elif (s == "Y-P39"):  # Atmospheric Zonal Mean (on 39 pressure levels)
        siz = nb_lat * 39
    elif (s == "Y-A"):  # Zonal mean (on model levels)
        siz = nb_lat * mcfg['nla']
    elif (s == "Y-na"):  # Zonal mean (on surface)
        siz = nb_lat
    elif (s == "na-A"):  # Atmospheric profile (model levels)
        # mpmoine_correction:field_size: 'na-A' s'applique a des dims (alevel)+spectband mais aussi a (alevel,site) => *nb_cosp_sites
        siz = mcfg['nla'] * nb_cosp_sites

    elif (s == "XY-S"):  # Global field on soil levels
        siz = mcfg['nls'] * mcfg['nha']

    elif (s == "XY-O"):  # Global ocean field on model levels
        siz = mcfg['nlo'] * mcfg['nho']

    elif (s == "XY-na"):  # Global field (single level)
        siz = mcfg['nha']
        if svar.modeling_realm in \
                ['ocean', 'seaIce', 'ocean seaIce', 'ocnBgchem', 'seaIce ocean']:
            siz = mcfg['nho']

    elif (s == "YB-R"):  # Ocean Basin Meridional Section (on density surfaces)
        siz = mcfg['nlo'] * nb_lat_ocean
    elif (s == "YB-O"):  # Ocean Basin Meridional Section
        siz = mcfg['nlo'] * nb_lat_ocean
    elif (s == "YB-na"):  # Ocean Basin Zonal Mean
        siz = nb_lat_ocean

    elif (s == "TR-na"):  # Ocean Transect
        siz = ocean_transect_size
    elif (s == "TRS-na"):  # Sea-ice ocean transect
        siz = ocean_transect_size

    elif (s == "na-na"):  # Global mean/constant
        siz = 1

    return siz


# mpmoine_last_modif:split_frequency_for_variable: suppression de l'argument table
# mpmoine_next_modif:split_frequency_for_variable: passage de 'context' en argument pour recuperer le model_timestep
def split_frequency_for_variable(svar, lset, mcfg, context):
    """
    Compute variable level split_freq and returns it as a string

    Method : if shape is basic, compute period using field size and a
    parameter from lset indicating max filesize, with some smart
    rounding.  Otherwise, use a fixed value which depends on shape,
    with a default value

    """
    max_size = lset.get("max_file_size_in_floats", 500 * 1.e6)
    size = field_size(svar, mcfg)
    # mpmoine_last_modif:split_frequency_for_variable: on ne passe plus par table2freq pour recuperer
    # mpmoine_last_modif:split_frequency_for_variable: la frequence de la variable mais par svar.frequency
    freq = svar.frequency
    if (size != 0):
        # Try by years first
        # mpmoine_next_modif:split_frequency_for_variable: passage de 'model_timestep' en argument de timesteps_per_freq_and_duration
        size_per_year = size * timesteps_per_freq_and_duration(freq, 365, lset["model_timestep"][context])
        nbyears = max_size / float(size_per_year)
        if nbyears > 1.:
            if nbyears < 10:
                return ("1y")
            elif nbyears < 50:
                return ("10y")
            elif nbyears < 100:
                return ("50y")
            elif nbyears < 200:
                return ("100y")
            else:
                return ("200y")
        else:
            # Try by month
            # mpmoine_next_modif:split_frequency_for_variable: passage de 'model_timestep' en argument de timesteps_per_freq_and_duration
            size_per_month = size * timesteps_per_freq_and_duration(freq, 31, lset["model_timestep"][context])
            nbmonths = max_size / float(size_per_month)
            if nbmonths > 1.:
                return ("1mo")
            else:
                # Try by day
                # mpmoine_next_modif:split_frequency_for_variable: passage de 'model_timestep' en argument de timesteps_per_freq_and_duration
                size_per_day = size * timesteps_per_freq_and_duration(freq, 1, lset["model_timestep"][context])
                nbdays = max_size / float(size_per_day)
                if nbdays > 1.:
                    return ("1d")
                else:
                    # mpmoine_last_modif:split_frequency_for_variable: on ne passe plus par table2freq pour recuperer
                    # mpmoine_last_modif:split_frequency_for_variable: la frequence de la variable mais par svar.frequency
                    raise (dr2xml_error("No way to put even a single day " + \
                                        "of data in %g for frequency %s, var %s, table %s" % \
                                        (max_size, freq, svar.label, svar.mipTable)))
    else:
        # mpmoine_zoom_modif:split_frequency_for_variable: print de warning si on arrive pas a calculer une split_freq
        print "Warning: field size is 0, cannot compute split frequency."


# mpmoine_next_modif: ajout de 'model_timestep' en argument de timesteps_per_freq_and_duration
def timesteps_per_freq_and_duration(freq, nbdays, model_tstep):
    # This function returns the number of records within nbdays
    duration = 0.
    # Translate freq strings to duration in days
    if freq == "3hr":
        duration = 1. / 8
    elif freq == "6hr":
        duration = 1. / 4
    elif freq == "day":
        duration = 1.
    # mpmoine_next_modif:timesteps_per_freq_and_duration: ajour de la frequence 'hr'
    elif freq == "1hr" or freq == "hr":
        duration = 1. / 24
    elif freq == "mon":
        duration = 31.
    elif freq == "yr":
        duration = 365.
    # mpmoine_next_modif:timesteps_per_freq_and_duration: ajout des cas frequence 'subhr' et 'dec'
    elif freq == "subhr":
        duration = 1. / (86400. / model_tstep)
    elif freq == "dec":
        duration = 10. * 365
    # If freq actually translate to a duration, return
    # number of timesteps for number of days
    if duration != 0.:
        return float(nbdays) / duration
    # Otherwise , retrun a senesible value
    elif freq == "fx":
        return 1.
    elif freq == "monClim":
        return 12.
    elif freq == "dayClim":
        return 24.


""" 
    Provide frequencies for a table name - Both in XIOS syntax and in CMIP6_CV 
    and also split_frequencies for the files hodling the whole of a table's variables 
    
    Rationale: Because CMIP6_CV does not (yet) provide the correspondance between a table name 
    and the corresponding frequency (albeit this is instrumental in DRS), and because 
    we need to translate anyway to XIOS syntax
"""

table2freq = {
    "3hr": ("3h", "3hr"),

    "6hrLev": ("6h", "6hr"),
    "6hrPlev": ("6h", "6hr"),
    "6hrPlevPt": ("6h", "6hr"),

    "AERday": ("1d", "day"),
    "AERfx": ("1d", "fx"),
    # mpmoine_next_modif: frequence CMIP6 pour AERhr = 'hr' et non '1hr'
    # TBD: remplacer "hr" par "1hr" selon reponse de D. Nadeau a l'issue https://github.com/PCMDI/cmip6-cmor-tables/issues/59
    "AERhr": ("1h", "hr"),
    "AERmon": ("1mo", "mon"),
    "AERmonZ": ("1mo", "mon"),

    "Amon": ("1mo", "mon"),

    "CF3hr": ("3h", "3hr"),
    "CFday": ("1d", "day"),
    "CFmon": ("1mo", "mon"),
    # mpmoine_next_modif: table2freq: frequence pour les tables subhr
    # mpmoine_future_modif: table2freq: la syntaxe xios pour le subhr est '1ts' et non 'instant' (vu par Arnaud)
    "CFsubhr": ("1ts", "subhr"),
    "CFsubhrOff": ("1ts", "subhr"),
    "E1hr": ("1h", "1hr"),
    # mpmoine_future_modif: table2freq: la syntaxe xios pour 1hr est '1h' et non '1hr'
    "E1hrClimMon": ("1h", "1hr"),
    "E3hr": ("3h", "3hr"),
    "E3hrPt": ("3h", "3hr"),
    "E6hrZ": ("6h", "6hr"),
    "Eday": ("1d", "day"),
    "EdayZ": ("1d", "day"),
    "Efx": ("1d", "fx"),
    "Emon": ("1mo", "mon"),
    "EmonZ": ("1mo", "mon"),
    # mpmoine_next_modif: table2freq: frequence pour les tables subhr
    # mpmoine_future_modif: table2freq: la syntaxe pour le subhe est '1ts' et non 'instant' (vu par Arnaud)
    "Esubhr": ("1ts", "subhr"),
    "Eyr": ("1y", "yr"),

    "IfxAnt": ("1d", "fx"),
    "IfxGre": ("1d", "fx"),
    "ImonAnt": ("1mo", "mon"),
    "ImonGre": ("1mo", "mon"),
    "IyrAnt": ("1y", "yr"),
    "IyrGre": ("1y", "yr"),

    "LImon": ("1mo", "mon"),
    "Lmon": ("1mo", "mon"),

    "Oclim": ("1d", "monClim"),
    "Oday": ("1d", "day"),
    "Odec": ("10y", "dec"),
    "Ofx": ("1d", "fx"),
    "Omon": ("1mo", "mon"),
    "Oyr": ("1y", "yr"),

    "SIday": ("1d", "day"),
    "SImon": ("1mo", "mon"),

    "day": ("1d", "day"),
    "fx": ("1d", "fx"),

    # mpmoine_last_modif: table2freq: ajout des tables Primavera
    "Prim1hr": ("1h", "1hr"),
    "Prim3hr": ("3h", "3hr"),
    "Prim3hrPt": ("3h", "3hr"),
    "Prim6hr": ("6h", "6hr"),
    "Prim6hrPt": ("6h", "6hr"),
    "PrimO6hr": ("6h", "6hr"),
    "PrimOday": ("1d", "day"),
    "PrimOmon": ("1mo", "mon"),
    "PrimSIday": ("1d", "day"),
    "Primday": ("1d", "day"),
    "PrimdayPt": ("1d", "day"),
    "Primmon": ("1mo", "mon"),
    "PrimmonZ": ("1mo", "mon"),

    "Myproday": ("1d", "day"),
    "testAmon": ("1mo", "mon"),

}

table2splitfreq = {
    "E3hrPt": "1mo",  # 3-hourly (instantaneous, extension) [3hr] (22 variables)
    "E3hr": "1mo",  # 3-hourly (time mean, extension) [3hr] (57 variables)
    "CF3hr": "1mo",  # 3-hourly associated with cloud forcing [3hr] (43 variables)
    "3hr": "1mo",  # 3-hourly data [3hr] (23 variables)
    "E6hrZ": "1mo",  # 6-hourly Zonal Mean (extension) [6hr] (2 variables)
    "6hrPlevPt": "1mo",  # 6-hourly atmospheric data on pressure levels (instantaneous) [6hr] (31 variables)
    "6hrPlev": "1mo",  # 6-hourly atmospheric data on pressure levels (time mean) [6hr] (29 variables)
    "6hrLev": "1mo",  # 6-hourly data on atmospheric model levels [6hr] (10 variables)
    "IyrAnt": "100y",  # Annual fields on the Antarctic ice sheet [yr] (33 variables)
    "IyrGre": "100y",  # Annual fields on the Greenland ice sheet [yr] (33 variables)
    "Oyr": "10y",  # Annual ocean variables [yr] (125 variables)
    "Eday": "1mo",  # Daily (time mean, extension) [day] (123 variables)
    "Eyr": "10y",  # Daily (time mean, extension) [yr] (22 variables)
    "day": "1mo",  # Daily Data (extension - contains both atmospheric and oceanographic data) [day] (35 variables)
    "Oday": "1mo",  # Daily ocean data [day] (6 variables)
    "EdayZ": "1mo",  # Daily Zonal Mean (extension) [day] (15 variables)
    "AERday": "1mo",  # Daily atmospheric chemistry and aerosol data [day] (10 variables)
    "CFday": "1mo",  # Daily data associated with cloud forcing [day] (36 variables)
    "SIday": "1mo",  # Daily sea-ice data [day] (8 variables)
    "Odec": "100y",  # Decadal ocean data [decadal] (24 variables)
    "CFsubhr": "1mo",  # Diagnostics for cloud forcing analysis at specific sites [subhr] (37 variables)
    "Efx": "1y",  # Fixed (extension) [fx] (21 variables)
    "AERfx": "1y",  # Fixed atmospheric chemistry and aerosol data [fx] (1 variables)
    "IfxAnt": "1y",  # Fixed fields on the Antarctic ice sheet [fx] (4 variables)
    "IfxGre": "1y",  # Fixed fields on the Greenland ice sheet [fx] (4 variables)
    "Ofx": "1y",  # Fixed ocean data [fx] (6 variables)
    "E1hr": "1mo",  # Hourly Atmospheric Data (extension) [1hr] (16 variables)
    "AERhr": "1mo",  # Hourly atmospheric chemistry and aerosol data [hr] (5 variables)
    "E1hrClimMon": "100y",  # Diurnal Cycle [1hrClimMon] (5 variables)
    "Emon": "10y",  # Monthly (time mean, extension) [mon] (385 variables)
    "Oclim": "10y",  # Monthly climatologies of ocean data [monClim] (34 variables)
    "SImon": "10y",  # Monthly sea-ice data [mon] (89 variables)
    "CFsubhrOff": "1mo",  # Offline diagnostics for cloud forcing analysis [subhr] (9 variables)
    "AERmon": "10y",  # Monthly atmospheric chemistry and aerosol data [mon] (126 variables)
    "AERmonZ": "10y",  # Monthly atmospheric chemistry and aerosol data [mon] (16 variables)
    "Amon": "10y",  # Monthly atmospheric data [mon] (75 variables)
    "CFmon": "10y",  # Monthly data associated with cloud forcing [mon] (56 variables)
    "LImon": "10y",  # Monthly fields for the terrestrial cryosphere [mon] (37 variables)
    "ImonAnt": "10y",  # Monthly fields on the Antarctic ice sheet [mon] (28 variables)
    "ImonGre": "10y",  # Monthly fields on the Greenland ice sheet [mon] (28 variables)
    "Lmon": "10y",  # Monthly land surface and soil model fields [mon] (54 variables)
    "Omon": "10y",  # Monthly ocean data [mon] (294 variables)
    "EmonZ": "10y",  # Monthly zonal means (time mean, extension) [mon] (31 variables)
    "Esubhr": "10y",  # Sub-hourly (extension) [subhr] (32 variables)
    "fx": "1y",  # Fixed variables [fx] (10 variables)

    # mpmoine_last_modif: table2splitfreq: ajout des tables Primavera
    "Prim1hr": "1mo",
    "Prim3hr": "1mo",
    "Prim3hrPt": "1mo",
    "Prim6hr": "1mo",
    "Prim6hrPt": "1mo",
    "PrimO6hr": "1mo",
    "PrimOday": "1mo",
    "PrimOmon": "10y",
    "PrimSIday": "1mo",
    "Primday": "1mo",
    "PrimdayPt": "1mo",
    "Primmon": "10y",
    "PrimmonZ": "10y",

    "Myproday": "1mo",

}

# mpmoine_last_modif: table2freq.py: nouveau: cmipFreq2xiosFreq
cmipFreq2xiosFreq = {}
for v in table2freq.values():
    if not cmipFreq2xiosFreq.has_key(v[1]): cmipFreq2xiosFreq[v[1]] = v[0]

# coding: utf-8

# Whats' necessary for reading XIOS xml file and process attribute's inheritance for
# being able to request the grid_ref for any valid XIOS 'field' object

# Main useful functions :
#   <opaque>    context = init_context(context_name,printout=False)
#   <ET object>    grid = d2grid(field_id,context,printout=False)

import os, os.path, re
import xml.etree.ElementTree as ET

# Define for each object kind those attributes useful for grid inheritance
attributes = dict()
attributes['field'] = ['grid_ref', 'field_ref']
attributes['field_definition'] = attributes['field']
attributes['field_group'] = attributes['field']
attributes['grid'] = ['axis_ref', 'domain_ref', 'grid_ref']
attributes['grid_group'] = attributes['grid']
attributes['context'] = []
attributes['axis'] = ['axis_ref']


# attributes['axis_definition']=[]  #attributes['domain_definition']=[]
# attributes['grid_definition']=[]  #attributes['calendar']=[]

# mpmoine_amelioration: ajout de l'argument 'path_parse' a la fonction read_src pour pouvoir lire les context.xml d'Arnaud
def read_src(elt, path_parse, printout=False, level=0, dont_read=[]):
    """
    Recursively reads the subfiles indicated by tag 'src' in childs of ELT
    """
    childs = []
    for child in elt:
        if 'src' in child.attrib:
            # mpmoine_amelioration:read_src: ajout de path_parse pour acceder aux context_<X>.xml
            filen = path_parse + "/" + child.attrib['src']
            skip = False
            for prefix in dont_read:
                if os.path.basename(filen)[0:len(prefix)] == prefix:
                    print "Skipping %s" % filen
                    skip = True
            if skip: continue
            # mpmoine_correction: read_src: gestion du type de codage XML pour pouvoir lire les context.xml d'Arnaud
            et = ET.parse(filen).getroot()
            if printout:
                print level * "\t" + "Reading %s, %s=%s" % (filen, et.tag, gattrib(et, 'id', 'no_id'))
            for el in et:
                if printout:
                    print (level + 1) * "\t" + "Storing %s in %s id=%s" % (
                        el.tag, child.tag, gattrib(child, 'id', 'no_id'))
                child.append(el)
    for child in elt:
        # print level*"\t"+"Recursing on %s %s"%(child.tag,gattrib(child,'id','no_id'))
        read_src(child, path_parse, printout, level + 1, dont_read)


def gattrib(e, attrib_name, default=None):
    if attrib_name in e.attrib:
        return e.attrib[attrib_name]
    else:
        return default


def merge_sons(elt, printout=False, level=0):
    """
    Merge all mergeable childs of  ELT based on tag, or
    on tag+id when tag is 'context' or 'field' or '..._group'
    """
    toremove = []
    # Using a dict with first instance of an elt for each tag (or tag+id)
    bytag = dict()
    tags_to_merge = ['context', 'file_definition', 'field_definition',
                     'axis_definition', 'grid_definition', 'calendar', 'field',
                     'field_group', 'file_group']
    for child in elt:
        if child.tag not in tags_to_merge: continue
        if child.tag not in ['context', 'field'] and '_group' not in child.tag:
            tag = child.tag
        else:
            if 'id' in child.attrib:
                tag = child.tag + "_" + child.attrib['id']
            else:
                continue  # do not merge attributes for anonymous fields
        if tag not in bytag:
            bytag[tag] = child
        else:
            if child != bytag[tag]:
                if 'src' in child.attrib:
                    name = child.attrib['src']
                else:
                    if 'id' in child.attrib:
                        name = child.attrib['id']
                    else:
                        name = 'no_id'
                if (printout):
                    print level * "\t" + "Moving %s %s content to %s" % (child.tag, name, tag)
                    #
                # Move childs from secondary entry to first entry (brother)
                for sub in child: bytag[tag].append(sub)
                # Update attributes, too
                for a in child.attrib: bytag[tag].attrib[a] = child.attrib[a]
                toremove.append(child)
    for child in toremove:
        if printout: print "removing one %s child : %s" % (`elt`, `child`)
        elt.remove(child)
    # Recursion
    for child in elt:
        if printout: print level * "\t" + "%s %s" % (child.tag, child.attrib.get('id', 'no_id'))
        merge_sons(child, printout, level + 1)


def solve_downward(attrib, elt, value=None, printout=False, level=0):
    """ propagate attribute ATTRIB 's VALUE downward of ELT,
    setting recursively it for all childs to the parent value or
    to the value encountered in an intermediate node
    """
    for child in elt:
        value_down = value
        if printout: print level * "\t" + " solving on " + `child`,
        if attrib in attributes.get(child.tag, []):
            if attrib not in child.attrib:
                if value is not None:
                    child.attrib[attrib] = value
                    if printout: print " set :" + value
                else:
                    if printout: print " pass"
            else:
                value_down = child.attrib[attrib]
                if printout: print " get :" + value_down
        else:
            if printout: print
        solve_downward(attrib, child, value_down, printout, level + 1)


def make_index(elt, index=None, printout=False, level=0):
    """
    Create an index of all elements having an id in ELT childs recursively
    and complement attributes and children of these indexed objects when
    crossing their id multiple times
    """
    if index is None: index = dict()
    for child in elt:
        if 'id' in child.attrib:
            the_id = child.attrib['id']
            if printout: print level * "\t" + " indexing " + the_id,
            if the_id in index:
                if printout: print " (merging)"
                # Update indexed object with current attributes
                for a in child.attrib: index[the_id].attrib[a] = child.attrib[a]
                # Add child chidlren to indexed objects
                for sub in child:  index[the_id].append(sub)
            else:
                if printout: print " init index"
                index[the_id] = child
        # else:
        #    if printout : print
    for child in elt:
        make_index(child, index, printout, level + 1)
    return (index)


def attrib_by_ref(elt, attrib, index, printout, level):
    """
        Provide ATTRIB value for ELT' id using its references
        and objects's dict INDEX
        """
    for a in elt.attrib:
        if '_ref' in a:
            refid = elt.attrib[a]
            if printout: print "\n" + (level + 1) * "\t" + a + " -> " + refid,
            try:
                ref = index[refid]
                if attrib in ref.attrib:
                    rep = ref.attrib[attrib]
                    if printout: print " ---> !! GOT : " + rep + " !!!"
                    return rep
                else:
                    rep = attrib_by_ref(ref, attrib, index, printout, level + 1)
                    if rep: return rep
            except:
                if not refid.startswith("dummy_"): print "Error : reference '%s' is invalid" % refid


def solve_by_ref(attrib, index, elt, printout=False, level=0):
    """
    Solve remainig attributes by ref, otherwise by default value
    """
    got_one = 0
    for child in elt:
        if type(child) != type('') and child.tag != 'variable':
            if 'id' in child.attrib:
                name = child.attrib['id']
            else:
                name = `child`
            if printout: print level * "\t" + attrib + " by_ref on  " + name,
            #
            if child.tag in attributes and attrib in attributes[child.tag]:
                if attrib not in child.attrib:
                    byref = attrib_by_ref(child, attrib, index, printout, level)
                    if byref:
                        # if printout : print ", setting byref to "+
byref,
                        child.attrib[attrib] = byref
                        got_one = got_one + 1
                    else:
                        if printout: print
                else:
                    if printout: print ", already set : %s" % child.attrib[attrib]
                got = solve_by_ref(attrib, index, child, printout, level + 1)
                got_one = got_one + got
            else:
                if printout: print " : N/A"
    return got_one


def select_context(rootel, context_id):
    for context in rootel:
        if 'id' in context.attrib and context.attrib['id'] == context_id:
            return context


# mpmoine_amelioration: ajout de l'argument 'path_parse' a la fonction init_context
def init_context(context_id, path_parse, printout=False):
    # mpmoine_merge_dev2_v0.12:init_context: ajout de "./parse/" pour acceder a iodef.xml
    rootel = ET.parse(path_parse + "/iodef.xml").getroot()
    # mpmoine_amelioration:init_context: ajout de l'argument 'path_parse' a la fonction read_src
    read_src(rootel, path_parse, printout=printout, dont_read=["dr2xml_"])
    merge_sons(rootel, printout)
    rootel = select_context(rootel, context_id)
    if rootel is not None:
        refs = ["grid_ref", "domain_ref", "axis_ref", "field_ref"]
        for ref in refs:
            solve_downward(ref, rootel, None)
        # ET.dump(rootel)
        index = make_index(rootel, None, printout)
        for ref in refs:
            while True:
                n = solve_by_ref(ref, index, rootel, printout)
                if printout: print "%d refs solved" % n
                if n == 0: break
        # ET.dump(rootel)
        return (index)


def id2grid(field_id, index, printout=False):
    """
    Returns the list of Element composing the grid IOXof a field
    """
    if field_id in index:
        attrib = index[field_id].attrib
        if 'grid_ref' in attrib:
            grid_ref_field_id = attrib['grid_ref']
            if grid_ref_field_id in index:
                return index[grid_ref_field_id]
            else:
                if printout: print("field %s reference is %s but has no grid" % (field_id, grid_ref_field_id))
        else:
            if printout: print("field %s has no grid_ref" % (field_id))
    else:
        if printout: print("field %s is not known" % field_id)


if False:

    nemo = init_context('nemo', False)
    # print nemo.keys()
    grid = id2grid("CMIP6_O18sw", nemo, True)
    print grid.attrib['id'];
    print

    arpsfx = init_context('arpsfx', False)
    grid = id2grid("CMIP6_cdnc", arpsfx, True)
    # grid=None
    if grid is not None:
        # print "Grid id is :"+grid.attrib['id']
        print ET.tostring(grid);
        grid_string = ET.tostring(grid)
        new_grid_string = re.sub('axis_ref= *.([\w_])*.', 'axis_ref="axis_autre"', grid_string)
        print new_grid_string

dr2cmip6_expname = {

    "Forced-Atmos-Land": "highresSST-present",
    "Forced-Atmos-Land-2050": "highresSST-future",
    "Coupled": "highres-future",
}
