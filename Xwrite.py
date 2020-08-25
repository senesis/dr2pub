#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XIOS writing files tools.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

# To access reduce function in python3
from functools import reduce
# To have ordered dictionaries
from collections import OrderedDict

import json
import re
import datetime
from io import open

# Utilities
from utils import dr2xml_error, print_struct

# Global variables and configuration tools
from config import get_config_variable

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_with_default, get_variable_from_lset_without_default, \
    get_variable_from_sset_with_default, get_source_id_and_type, get_variable_from_sset_without_default, \
    get_variable_from_sset_else_lset_with_default, is_key_in_lset, is_key_in_sset, get_lset_iteritems, \
    get_sset_iteritems, format_dict_for_printing
# Interface to Data Request
from dr_interface import get_DR_version

from xml_interface import create_xml_element, create_xml_sub_element, create_string_from_xml_element, \
    remove_subelement_in_xml_element, add_xml_comment_to_element, create_pretty_xml_doc

# Settings tools
from analyzer import DRgrid2gridatts, analyze_cell_time_method, freq2datefmt, longest_possible_period, \
    Cmip6Freq2XiosFreq

# CFsites tools
from cfsites import cfsites_domain_id, add_cfsites_in_defs, cfsites_grid_id, cfsites_input_filedef

# Tools to deal with ping files
from pingfiles_interface import check_for_file_input

# Grids tools
from grids import change_domain_in_grid, change_axes_in_grid, get_grid_def_with_lset, create_standard_domains

# Variables tools
from vars_cmor import ping_alias
from vars_home import get_simplevar
from vars_selection import get_sc, endyear_for_CMORvar, get_grid_choice

# Post-processing tools
from postprocessing import process_vertical_interpolation, process_zonal_mean, process_diurnal_cycle

# XIOS tools
from Xparse import id2gridid, idHasExprWithAt

# File splitting tools
from file_splitting import split_frequency_for_variable


warnings_for_optimisation = []


def wr(out, key, dic_or_val=None, num_type="string", default=None):
    """
    Short cut for a repetitive pattern : add in 'out'
    a string variable name and value
    If dic_or_val is not None
      if  dic_or_val is a dict,
        if key is in value is dic_or_val[key],
        otherwise use default as value , except if default is False
      otherwise, use arg dic_or_val as value if not None nor False,
    otherwise use value of local variable 'key'
    """
    print_variables = get_variable_from_lset_with_default("print_variables", True)
    if not print_variables:
        return
    elif isinstance(print_variables, list) and key not in print_variables:
        return

    val = None
    if isinstance(dic_or_val, (dict, OrderedDict)):
        if key in dic_or_val:
            val = dic_or_val[key]
        else:
            if default is not None:
                if default is not False:
                    val = default
            else:
                print('error : %s not in dic and default is None' % key)
    else:
        if dic_or_val is not None:
            val = dic_or_val
        else:
            print('error in wr,  no value provided for %s' % key)
    if val:
        if num_type == "string":
            # val=val.replace(">","&gt").replace("<","&lt").replace("&","&amp").replace("'","&apos").replace('"',"&quot").strip()
            val = val.replace(">", "&gt").replace("<", "&lt").strip()
            # CMIP6 spec : no more than 1024 char
            val = val[0:1024]
        if num_type != "string" or len(val) > 0:
            attrib_dict = OrderedDict()
            attrib_dict["name"] = key
            attrib_dict["type"] = num_type
            create_xml_sub_element(xml_element=out, tag="variable", text=val, attrib=attrib_dict)


def write_xios_file_def_for_svar(sv, year, table, lset, sset, out, cvspath,
                                 field_defs, axis_defs, grid_defs, domain_defs, scalar_defs, file_defs,
                                 dummies, skipped_vars_per_table, actually_written_vars,
                                 prefix, context, grid, pingvars=None, enddate=None,
                                 attributes=[], debug=[]):
    """
    Generate an XIOS file_def entry in out for :
      - a dict for laboratory settings
      - a dict of simulation settings
      - a 'simplifed CMORvar' sv
      - which all belong to given table
      - a path 'cvs' for Controlled Vocabulary

    Lenghty code, but not longer than the corresponding specification document

    1- After a prologue, attributes valid for all variables are
    written as file-level metadata, in the same order than in
    WIP document;
    2- Next, field-level metadata are written
    3- For 3D variables in model levels or half-levels, also write the auxilliary
    variables requested by CF convention (e.g. for hybrid coordinate, surface_pressure field
    plus AP and B arrays and their bounds, and lev + lev_bnds with formula attribute)
    """
    #
    # If list of included vars has size 1, activate debug on the corresponding variable
    inc = get_variable_from_lset_with_default('included_vars', [])
    if len(inc) == 1:
        debug = inc

    # gestion des attributs pour lesquels on a recupere des chaines vides (" " est Faux mais est ecrit " "")
    # --------------------------------------------------------------------
    # Put a warning for field attributes that shouldn't be empty strings
    # --------------------------------------------------------------------
    # if not sv.stdname       : sv.stdname       = "missing" #"empty in DR "+get_DR_version()
    if not sv.long_name:
        sv.long_name = "empty in DR " + get_DR_version()
    # if not sv.cell_methods  : sv.cell_methods  = "empty in DR "+get_DR_version()
    # if not sv.cell_measures : sv.cell_measures = "cell measure is not specified in DR "+get_DR_version()
    if not sv.units:
        sv.units = "empty in DR " + get_DR_version()

    # --------------------------------------------------------------------
    # Define alias for field_ref in file-def file
    # - may be replaced by alias1 later
    # - this is not necessarily the alias used in ping file because of
    #   intermediate field id(s) due to union/zoom
    # --------------------------------------------------------------------
    # We use a simple convention for variable names in ping files :
    if sv.type in ['perso', 'dev']:
        alias = sv.label
        alias_ping = sv.label
    else:
        # MPM : si on a defini un label non ambigu alors on l'utilise comme alias (i.e. le field_ref)
        # et pour l'alias seulement (le nom de variable dans le nom de fichier restant svar.label)
        if sv.label_non_ambiguous:
            alias = get_variable_from_lset_without_default("ping_variables_prefix") + sv.label_non_ambiguous
        else:
            # 'tau' is ambiguous in DR 01.00.18 : either a variable name (stress)
            # or a dimension name (optical thickness). We choose to rename the stress
            if sv.label != "tau":
                alias = get_variable_from_lset_without_default("ping_variables_prefix") + sv.label
            else:
                alias = get_variable_from_lset_without_default("ping_variables_prefix") + "tau_stress"
        if sv.label in debug:
            print("write_xios_file_def_for_svar ... processing %s, alias=%s" % (sv.label, alias))

        # suppression des terminaisons en "Clim" pour l'alias : elles concernent uniquement les cas
        # d'absence de variation inter-annuelle sur les GHG. Peut-etre genant pour IPSL ?
        # Du coup, les simus avec constance des GHG (picontrol) sont traitees comme celles avec variation
        split_alias = alias.split("Clim")
        alias = split_alias[0]
        if pingvars is not None:
            # Get alias without pressure_suffix but possibly with area_suffix
            alias_ping = ping_alias(sv, pingvars)
    #
    # process only variables in pingvars except for dev variables
    if alias_ping not in pingvars and sv.type != "dev":
        # print "+++ =>>>>>>>>>>>", alias_ping, " ", sv.label
        table = sv.mipTable
        if table not in skipped_vars_per_table:
            skipped_vars_per_table[table] = []
        skipped_vars_per_table[table].append(sv.label + "(" + str(sv.Priority) + ")")
        return
    #
    # --------------------------------------------------------------------
    # Set global CMOR file attributes
    # --------------------------------------------------------------------
    #
    project = get_variable_from_sset_with_default('project', "CMIP6")
    source_id, source_type = get_source_id_and_type()
    experiment_id = get_variable_from_sset_without_default('experiment_id')
    institution_id = get_variable_from_lset_without_default('institution_id')
    if get_variable_from_sset_with_default("CORDEX_data", False):
        driving_model_id = get_variable_from_sset_without_default('driving_model_id')
        driving_model_ensemble_member = get_variable_from_sset_without_default('driving_model_ensemble_member')
        driving_experiment = get_variable_from_sset_without_default('driving_experiment')
        driving_experiment_name = get_variable_from_sset_without_default('driving_experiment_name')
        CORDEX_domain = get_variable_from_sset_without_default('CORDEX_domain')
        lambert_conformal_longitude_of_central_meridian = \
            get_variable_from_sset_without_default('Lambert_conformal_longitude_of_central_meridian')
        lambert_conformal_standard_parallel = \
            get_variable_from_sset_without_default('Lambert_conformal_standard_parallel')
        lambert_conformal_latitude_of_projection_origin = \
            get_variable_from_sset_without_default('Lambert_conformal_latitude_of_projection_origin')
        rcm_version_id = get_variable_from_sset_without_default("rcm_version_id")

    #
    contact = get_variable_from_sset_else_lset_with_default('contact', default=None)
    #
    # Variant matters
    realization_index = get_variable_from_sset_with_default('realization_index', 1)
    initialization_index = get_variable_from_sset_with_default('initialization_index', 1)
    physics_index = get_variable_from_sset_with_default('physics_index', 1)
    forcing_index = get_variable_from_sset_with_default('forcing_index', 1)
    variant_label = "r%di%dp%df%d" % (realization_index, initialization_index, physics_index, forcing_index)
    variant_info_warning = ". Information provided by this attribute may in some cases be flawed. " + \
                           "Users can find more comprehensive and up-to-date documentation " \
                           "via the further_info_url global attribute."
    #
    # WIP Draft 14 july 2016
    mip_era = get_variable_from_sset_else_lset_with_default("mip_era", default=sv.mip_era)
    #
    # WIP doc v 6.2.0 - dec 2016
    # <variable_id>_<table_id>_<source_id>_<experiment_id >_<member_id>_<grid_label>[_<time_range>].nc
    member_id = variant_label
    sub_experiment_id = get_variable_from_sset_with_default('sub_experiment_id', 'none')
    if sub_experiment_id != 'none':
        member_id = sub_experiment_id + "-" + member_id
    #
    # --------------------------------------------------------------------
    # Set grid info
    # --------------------------------------------------------------------
    if grid == "":
        # either native or close-to-native
        grid_choice = get_variable_from_lset_without_default('grid_choice', source_id)
        if sv.type == "dev":
            grid_ref = sv.description.split('|')[1]
            if grid_ref == "native":
                grid_label, target_hgrid_id, zgrid_id, grid_resolution, grid_description = \
                    get_variable_from_lset_without_default('grids_dev', sv.label, grid_choice, context)
            else:
                grid_label, target_hgrid_id, zgrid_id, grid_resolution, grid_description = \
                    get_variable_from_lset_without_default('grids', grid_choice, context)
        else:
            grid_label, target_hgrid_id, zgrid_id, grid_resolution, grid_description = \
                get_variable_from_lset_without_default('grids', grid_choice, context)
    else:
        if grid == 'cfsites':
            target_hgrid_id = cfsites_domain_id
            zgrid_id = None
        else:
            target_hgrid_id = get_variable_from_lset_without_default("ping_variables_prefix") + grid
            zgrid_id = "TBD : Should create zonal grid for CMIP6 standard grid %s" % grid
        grid_label, grid_resolution, grid_description = DRgrid2gridatts(grid, is_dev=(grid == "native" and
                                                                                      sv.type == "dev"))

    if table.endswith("Z"):  # e.g. 'AERmonZ','EmonZ', 'EdayZ'
        grid_label += "z"
        # Below : when reduction was done trough a two steps sum, we needed to divide afterwards
        # by the number of longitudes
        #
        # if is_key_in_lset("nb_longitudes_in_model") and
        # get_variable_from_lset_without_default("nb_longitudes_in_model", context):
        #     # Get from settings the name of Xios variable holding number of longitudes and set by model
        #     nlonz=get_variable_from_lset_without_default("nb_longitudes_in_model", context) # e.g.: nlonz="ndlon"
        # elif context_index.has_key(target_hgrid_id):
        #     # Get the number of longitudes from xml context_index
        #     # an integer if attribute of the target horizontal grid, declared in XMLs: nlonz=256
        #     nlonz=context_index[target_hgrid_id].attrib['ni_glo']
        # else:
        #     raise dr2xml_error("Fatal: Cannot access the number of longitudes (ni_glo) for %s\
        #                 grid required for zonal means computation "%target_hgrid_id)
        # print ">>> DBG >>> nlonz=", nlonz

    if "Ant" in table:
        grid_label += "a"
    if "Gre" in table:
        grid_label += "g"
    #
    with open(cvspath + project + "_experiment_id.json", "r") as json_fp:
        CMIP6_CV_version_metadata = json.loads(json_fp.read())['version_metadata']
        CMIP6_CV_latest_tag = CMIP6_CV_version_metadata.get('latest_tag_point', 'no more value in CMIP6_CV')
    #
    with open(cvspath + project + "_experiment_id.json", "r") as json_fp:
        CMIP6_experiments = json.loads(json_fp.read())['experiment_id']
        if get_variable_from_sset_without_default('experiment_id') not in CMIP6_experiments:
            raise dr2xml_error("Issue getting experiment description in CMIP6 CV for %20s" % sset['experiment_id'])
        expid = get_variable_from_sset_without_default('experiment_id')
        expid_in_filename = get_variable_from_sset_with_default('expid_in_filename', expid)
        if "_" in expid_in_filename:
            raise dr2xml_error("Cannot use character '_' in expid_in_filename (%s)" % expid_in_filename)
        exp_entry = CMIP6_experiments[expid]
        experiment = get_variable_from_sset_with_default("experiment", exp_entry["experiment"])
        description = get_variable_from_sset_with_default("description", exp_entry['description'])
        activity_id = get_variable_from_sset_else_lset_with_default('activity_id', default=exp_entry['activity_id'])
        if is_key_in_sset("parent_activity_id"):
            parent_activity_id = get_variable_from_sset_without_default("parent_acivity_id")
        elif is_key_in_sset("activity_id"):
            parent_activity_id = get_variable_from_sset_without_default("activity_id")
        elif is_key_in_lset("parent_activity_id"):
            parent_activity_id = get_variable_from_lset_without_default("parent_activity_id")
        else:
            parent_activity_id = get_variable_from_sset_with_default("activity_id", exp_entry["parent_activity_id"])
        if isinstance(parent_activity_id, list) and len(parent_activity_id) > 1:
            parent_activity_id = reduce(lambda x, y: x+" "+y, parent_activity_id)
        parent_experiment_id =  get_variable_from_sset_else_lset_with_default("parent_experiment_id",
                                                                              default=exp_entry['parent_experiment_id'])
        if isinstance(parent_experiment_id, list) and len(parent_experiment_id) > 1:
            parent_experiment_id = reduce(lambda x, y: x+" "+y, parent_experiment_id)
        required_components = exp_entry['required_model_components']  # .split(" ")
        allowed_components = exp_entry['additional_allowed_model_components']  # .split(" ")
    #
    # Check model components re. CV components
    actual_components = source_type.split(" ")
    ok = True
    for c in required_components:
        if c not in actual_components:
            ok = False
            if not get_variable_from_sset_with_default("CORDEX_data", False):
                print("Model component %s is required by CMIP6 CV for experiment %s and not present (present=%s)" %
                      (c, experiment_id, repr(actual_components)))
    for c in actual_components:
        if c not in allowed_components and c not in required_components:
            ok = False or get_variable_from_sset_with_default('bypass_CV_components', False)
            if not get_variable_from_sset_with_default("CORDEX_data", False):
                print("Warning: Model component %s is present but not required nor allowed (%s)" %
                      (c, repr(allowed_components)))
    if not ok:
        raise dr2xml_error("Issue with model components")
    #
    # --------------------------------------------------------------------
    # Set NetCDF output file name according to the DRS
    # --------------------------------------------------------------------
    #
    date_range = "%start_date%-%end_date%"  # XIOS syntax
    operation, detect_missing, foo = analyze_cell_time_method(sv.cell_methods, sv.label, table, printout=False)
    # print "--> ",sv.label, sv.frequency, table
    date_format, offset_begin, offset_end = freq2datefmt(sv.frequency, operation, table)
    #
    if "fx" in sv.frequency:
        if get_variable_from_sset_with_default("CORDEX_data", False):
            filename = "_".join(([prefix + sv.label, CORDEX_domain.get(context), driving_model_id, expid_in_filename,
                                  driving_model_ensemble_member, source_id, rcm_version_id, sv.frequency]))
        else:
            filename = "_".join(([prefix + sv.label, table, source_id, expid_in_filename, member_id, grid_label]))
        varname_for_filename = sv.label
    else:
        varname_for_filename = sv.mipVarLabel
        if get_variable_from_lset_with_default('use_cmorvar_label_in_filename', False):
            varname_for_filename = sv.label
        # DR21 has a bug with tsland : the MIP variable is named "ts"
        if sv.label == "tsland":
            varname_for_filename = "tsland"
        # WIP doc v6.2.3 : a suffix "-clim" should be added if climatology
        # if False and "Clim" in sv.frequency: suffix="-clim"
        if sv.frequency in ["1hrCM", "monC"]:
            suffix = "-clim"
        else:
            suffix = ""
        if get_variable_from_sset_with_default("CORDEX_data", False):
            liste_attributes = [prefix + varname_for_filename, CORDEX_domain.get(context), driving_model_id,
                                expid_in_filename, driving_model_ensemble_member, source_id, rcm_version_id, sv.frequency, date_range +
                                suffix]
            filename = "_".join([attribute for attribute in liste_attributes if attribute != ""])
        else:
            filename = "_".join([prefix + varname_for_filename, table, source_id, expid_in_filename, member_id,
                                 grid_label, date_range + suffix])
    # Create an other file which will contain the list of file names of perso and dev variables
    list_perso_and_dev_file_name = "dr2xml_list_perso_and_dev_file_names"
    if sv.type in ["perso", "dev"]:
        with open(list_perso_and_dev_file_name, mode="a", encoding="utf-8") as list_perso_and_dev:
            list_perso_and_dev.write(".*{}.*\n".format("_".join([varname_for_filename, table, source_id,
                                                               expid_in_filename, member_id, grid_label])))
    #
    if not (is_key_in_lset('mip_era') or is_key_in_sset("mip_era")):
        further_info_url = "https://furtherinfo.es-doc.org/%s.%s.%s.%s.%s.%s" % (
            mip_era, institution_id, source_id, expid_in_filename,
            sub_experiment_id, variant_label)
    else:
        further_info_url = ""
    #
    # --------------------------------------------------------------------
    # Compute XIOS split frequency
    # --------------------------------------------------------------------
    sc = get_sc()
    resolution = get_variable_from_lset_without_default('grid_choice', source_id)
    split_freq = split_frequency_for_variable(sv, resolution, sc.mcfg, context)
    # Cap split_freq by setting max_split_freq (if expressed in years)
    if split_freq[-1] == 'y':
        max_split_freq = get_variable_from_sset_with_default('max_split_freq', None)
        if max_split_freq is None:
            max_split_freq = get_variable_from_lset_with_default('max_split_freq', None)
        if max_split_freq is not None:
            if max_split_freq[0:-1] != "y":
                dr2xml_error("max_split_freq must end with an 'y' (%s)" % max_split_freq)
            split_freq = "{}y".format(min(int(max_split_freq[0:-1]), int(split_freq[0:-1])))
    # print "split_freq: %-25s %-10s %-8s"%(sv.label,sv.mipTable,split_freq)
    #
    # --------------------------------------------------------------------
    # Write XIOS file node:
    # including global CMOR file attributes
    # --------------------------------------------------------------------
    dict_file = OrderedDict()
    dict_file["id"] = "_".join([sv.label, table, grid_label])
    dict_file["name"] = filename
    freq = longest_possible_period(Cmip6Freq2XiosFreq(sv.frequency, table),
                                   get_variable_from_lset_with_default("too_long_periods", []))
    dict_file["output_freq"] = freq
    dict_file["append"] = "true"
    dict_file["output_level"] = str(get_variable_from_lset_with_default("output_level", 10))
    dict_file["compression_level"] = str(get_variable_from_lset_with_default("compression_level", 0))
    if "fx" not in sv.frequency:
        dict_file["split_freq"] = split_freq
        dict_file["split_freq_format"] = date_format
        #
        # Modifiers for date parts of the filename, due to silly KT conventions.
        if offset_begin is not False:
            dict_file["split_start_offset"] = offset_begin
        if offset_end is not False:
            dict_file["split_end_offset"] = offset_end
        lastyear = None
        # Try to get enddate for the CMOR variable from the DR
        if sv.cmvar is not None:
            # print "calling endyear_for... for %s, with year="%(sv.label), year
            lastyear = endyear_for_CMORvar(sv.cmvar, expid, year, sv.label in debug)
            # print "lastyear=",lastyear," enddate=",enddate
        if lastyear is None or (enddate is not None and lastyear >= int(enddate[0:4])):
            # DR doesn't specify an end date for that var, or a very late one
            if get_variable_from_lset_with_default('dr2xml_manages_enddate', True):
                # Use run end date as the latest possible date
                # enddate must be 20140101 , rather than 20131231
                if enddate is not None:
                    endyear = enddate[0:4]
                    endmonth = enddate[4:6]
                    endday = enddate[6:8]
                    dict_file["split_last_date"] = "{}-{}-{} 00:00:00".format(endyear, endmonth, endday)
                else:
                    dict_file["split_last_date"] = "10000-01-01 00:00:00"
        else:
            # Use requestItems-based end date as the latest possible date when it is earlier than run end date
            if sv.label in debug:
                print("split_last_date year %d derived from DR for variable %s in table %s for year %d" %
                      (lastyear, sv.label, table, year))
            endyear = "{:04d}".format(lastyear + 1)
            if lastyear < 1000:
                dr2xml_error(
                    "split_last_date year %d derived from DR for variable %s in table %s for year %d does not make "
                    "sense except maybe for paleo runs; please set the right value for 'end_year' in experiment's "
                    "settings file" % (lastyear, sv.label, table, year))
            endmonth = "01"
            endday = "01"
            dict_file["split_last_date"] = "{}-{}-{} 00:00:00".format(endyear, endmonth, endday)
    #
    # dict_file["timeseries"] = "exclusive"
    dict_file["time_units"] = "days"
    dict_file["time_counter_name"] = "time"
    dict_file["time_counter"] = "exclusive"
    dict_file["time_stamp_name"] = "creation_date"
    dict_file["time_stamp_format"] = "%Y-%m-%dT%H:%M:%SZ"
    dict_file["uuid_name"] = "tracking_id"
    dict_file["uuid_format"] = "hdl:{}/%uuid%".format(get_variable_from_sset_else_lset_with_default("HDL", "21.14100"))
    dict_file["convention_str"] = get_config_variable("conventions")
    # out.write(' description="A %s result for experiment %s of %s"'%
    #            (lset['source_id'],sset['experiment_id'],sset.get('project',"CMIP6")))
    xml_file = create_xml_element(tag="file", attrib=dict_file)
    #
    if isinstance(activity_id, list):
        activity_idr = reduce(lambda x, y: x + " " + y, activity_id)
    else:
        activity_idr = activity_id
    wr(xml_file, 'activity_id', activity_idr)
    #
    if contact and contact is not "":
        wr(xml_file, 'contact', contact)
    wr(xml_file, 'data_specs_version', get_DR_version())
    wr(xml_file, 'dr2xml_version', get_config_variable("version"))
    #
    wr(xml_file, 'experiment_id', expid_in_filename)
    if experiment_id == expid_in_filename:
        wr(xml_file, 'description', description)
        wr(xml_file, 'title', description)
        wr(xml_file, 'experiment', experiment)
    #
    # Fixing cell_measures is done in vars.py
    #
    dynamic_comment = ""
    if "seaIce" in sv.modeling_realm and 'areacella' in sv.cell_measures and sv.label != "siconca":
        dynamic_comment = '. Due an error in DR01.00.21 and to technical constraints, this variable may have ' \
                          'attribute cell_measures set to area: areacella, while it actually is area: areacello'

    #
    # When remapping occurs to a regular grid -> CF does not ask for cell_measure
    # but CMIP6 do ask for it !
    # if grid_label[0:2]=='gr': sv.cell_measures=""
    # TBD : find a way to provide an areacella field for variables which are remapped to a 'CMIP6' grid such as '1deg'

    #
    # CF rule : if the file variable has a cell_measures attribute, and
    # the corresponding 'measure' variable is not included in the file,
    # it must be quoted as external_variable
    external_variables = ''
    if "area:" in sv.cell_measures:
        external_variables += " " + re.sub(".*area: ([^ ]*).*", r'\1', sv.cell_measures)
    if "volume:" in sv.cell_measures:
        external_variables += " " + re.sub(".*volume: ([^ ]*).*", r'\1', sv.cell_measures)
    if 'fx' in table:
        external_variables = ""
    if external_variables:
        wr(xml_file, 'external_variables', external_variables)
    #
    #
    wr(xml_file, 'forcing_index', forcing_index, num_type="int")
    wr(xml_file, 'frequency', sv.frequency)
    #
    if further_info_url:
        wr(xml_file, 'further_info_url', further_info_url)
    #
    wr(xml_file, 'grid', grid_description)
    wr(xml_file, 'grid_label', grid_label)
    wr(xml_file, 'nominal_resolution', grid_resolution)
    comment = get_variable_from_lset_with_default('comment', '') +\
              " " + get_variable_from_sset_with_default('comment', '') + dynamic_comment
    wr(xml_file, 'comment', comment)
    wr(xml_file, 'history', sset, default='none')
    wr(xml_file, "initialization_index", initialization_index, num_type="int")
    wr(xml_file, "institution_id", institution_id)
    if get_variable_from_sset_with_default("CORDEX_data", False):
        wr(xml_file, "CORDEX_domain", CORDEX_domain.get(context))
        wr(xml_file, "driving_model_id", driving_model_id)
        wr(xml_file, "driving_model_ensemble_member", driving_model_ensemble_member)
        wr(xml_file, "driving_experiment_name", driving_experiment_name)
        wr(xml_file, "driving_experiment", driving_experiment)
        wr(xml_file, "Lambert_conformal_longitude_of_central_meridian", lambert_conformal_longitude_of_central_meridian)
        wr(xml_file, "Lambert_conformal_standard_parallel", lambert_conformal_standard_parallel)
        wr(xml_file, "Lambert_conformal_latitude_of_projection_origin", lambert_conformal_latitude_of_projection_origin)
    if is_key_in_lset('institution'):
        inst = get_variable_from_lset_without_default('institution')
    else:
        with open(cvspath + project + "_institution_id.json", "r") as json_fp:
            try:
                inst = json.loads(json_fp.read())['institution_id'][institution_id]
            except:
                raise dr2xml_error("Fatal: Institution_id for %s not found in CMIP6_CV at %s" % (institution, cvspath))
    wr(xml_file, "institution", inst)
    #
    with open(cvspath + project + "_license.json", "r") as json_fp:
        license = json.loads(json_fp.read())['license'][0]
    # mpmoine_cmor_update: 'licence' est trop long... passe pas le CMIP6-Checker
    # => 'institution_id' au lieu de inst='institution'
    license = license.replace("<Your Centre Name>", institution_id)
    license = license.replace("[NonCommercial-]", "NonCommercial-")
    license = license.replace("[ and at <some URL maintained by modeling group>]",
                              " and at " + get_variable_from_lset_without_default("info_url"))
    wr(xml_file, "license", license)
    wr(xml_file, 'mip_era', mip_era)
    #
    if parent_experiment_id and parent_experiment_id != 'no parent' and parent_experiment_id != ['no parent']:
        wr(xml_file, 'parent_experiment_id', reduce(lambda x, y: x + " " + y, parent_experiment_id))
        wr(xml_file, 'parent_mip_era', sset, default=mip_era)
        wr(xml_file, 'parent_activity_id', reduce(lambda x, y: x + " " + y, parent_activity_id))
        wr(xml_file, 'parent_source_id', sset, default=source_id)
        # TBD : syntaxe XIOS pour designer le time units de la simu courante
        parent_time_ref_year = get_variable_from_sset_with_default('parent_time_ref_year', "1850")
        parent_time_units = "days since {}-01-01 00:00:00".format(parent_time_ref_year)
        wr(xml_file, 'parent_time_units', sset, default=parent_time_units)
        wr(xml_file, 'parent_variant_label', sset, default=variant_label)
        wr(xml_file, 'branch_method', sset, default='standard')
        # Use branch year in parent if available
        if is_key_in_sset("branch_year_in_parent") and source_id in get_variable_from_lset_without_default('branching'):
            if experiment_id in get_variable_from_lset_without_default('branching', source_id) and \
                    get_variable_from_sset_without_default("branch_year_in_parent") not in \
                    get_variable_from_lset_without_default('branching', source_id, experiment_id, 1):
                dr2xml_error(
                    "branch_year_in_parent (%d) doesn't belong to the list of branch_years declared for this experiment"
                    " %s" % (get_variable_from_sset_without_default("branch_year_in_parent"),
                             get_variable_from_lset_without_default('branching', source_id, experiment_id, 1)))
            date_branch = datetime.datetime(get_variable_from_sset_without_default("branch_year_in_parent"),
                                            get_variable_from_sset_with_default("branch_month_in_parent", 1), 1)
            date_ref = datetime.datetime(int(parent_time_ref_year), 1, 1)
            nb_days = (date_branch - date_ref).days
            wr(xml_file, 'branch_time_in_parent', "{}.0D".format(nb_days), "double")
        else:
            wr(xml_file, 'branch_time_in_parent', sset, "double")
        # Use branch year in child if available
        if is_key_in_sset("branch_year_in_parent"):
            date_branch = datetime.datetime(get_variable_from_sset_without_default("branch_year_in_child"), 1, 1)
            date_ref = datetime.datetime(get_variable_from_sset_without_default("child_time_ref_year"), 1, 1)
            nb_days = (date_branch - date_ref).days
            wr(xml_file, 'branch_time_in_child', "{}.0D".format(nb_days), "double")
        else:
            wr(xml_file, 'branch_time_in_child', sset, "double")
    else:
        # Only add branch method meta-data, which is needed for publication
        wr(xml_file, 'branch_method', "no parent")
    #
    wr(xml_file, "physics_index", physics_index, num_type="int")
    if get_variable_from_sset_with_default("CORDEX_data", False):
        wr(xml_file, "product", "output")
    else:
        wr(xml_file, 'product', 'model-output')
    wr(xml_file, "realization_index", realization_index, num_type="int")
    # Patch for an issue id DR01.0021 -> 01.00.24
    crealm = sv.modeling_realm
    if crealm == "ocnBgChem":
        crealm = "ocnBgchem"
    wr(xml_file, 'realm', crealm)
    wr(xml_file, 'references', lset, default=False)
    #
    try:
        with open(cvspath + project + "_source_id.json", "r") as json_fp:
            sources = json.loads(json_fp.read())['source_id']
            source = make_source_string(sources, source_id)
    except:
        if is_key_in_lset('source'):
            source = get_variable_from_lset_without_default('source')
        else:
            raise dr2xml_error("Fatal: source for %s not found in CMIP6_CV at %s, nor in lset" % (source_id, cvspath))
    wr(xml_file, 'source', source)
    wr(xml_file, 'source_id', source_id)
    if isinstance(source_type, list):
        source_type = reduce(lambda x, y: x + " " + y, source_type)
    wr(xml_file, 'source_type', source_type)
    #
    wr(xml_file, 'sub_experiment_id', sub_experiment_id)
    wr(xml_file, 'sub_experiment', sset, default='none')
    #
    wr(xml_file, "table_id", table)
    #
    if not is_key_in_sset('expid_in_filename'):
        wr(xml_file, "title", "{} model output prepared for {} / ".format(source_id, project) + activity_idr + " " +
           experiment_id)
    else:
        wr(xml_file, "title", "{} model output prepared for {} and ".format(source_id, project) + activity_idr + " / " +
           expid_in_filename + " simulation")
    #
    # DR21 has a bug with tsland : the MIP variable is named "ts"
    if sv.label != "tsland":
        wr(xml_file, "variable_id", sv.mipVarLabel)
    else:
        wr(xml_file, "variable_id", "tsland")
    #
    variant_info = get_variable_from_sset_with_default('variant_info', "none")
    if variant_info != "none" and variant_info != "":
        variant_info += variant_info_warning
    if variant_info != "":
        wr(xml_file, "variant_info", variant_info)
    wr(xml_file, "variant_label", variant_label)
    for name, value in sorted(list(attributes)):
        wr(xml_file, name, value)
    non_stand_att = get_variable_from_lset_with_default("non_standard_attributes", OrderedDict())
    for name in sorted(list(non_stand_att)):
        wr(xml_file, name, non_stand_att[name])
    #
    # --------------------------------------------------------------------
    # Build all XIOS auxiliary elements (end_file_defs, field_defs, domain_defs, grid_defs, axis_defs)
    # ---
    # Write XIOS field entry
    # including CF field attributes
    # --------------------------------------------------------------------
    end_field = create_xios_aux_elmts_defs(sv, alias, table, field_defs, axis_defs, grid_defs, domain_defs, scalar_defs,
                                           dummies, context, target_hgrid_id, zgrid_id, pingvars)
    xml_file.append(end_field)
    if sv.spatial_shp[0:4] == 'XY-A' or sv.spatial_shp[0:3] == 'S-A':  # includes half-level cases
        # create a field_def entry for surface pressure
        # print "Searching for ps for var %s, freq %s="%(alias,freq)
        sv_psol = get_simplevar("ps", table, sv.frequency)

        if sv_psol:
            # if not sv_psol.cell_measures : sv_psol.cell_measures = "cell measure is not specified in DR "+
            # get_DR_version()
            psol_field = create_xios_aux_elmts_defs(sv_psol,
                                                    get_variable_from_lset_without_default("ping_variables_prefix")
                                                    + "ps", table, field_defs, axis_defs, grid_defs, domain_defs,
                                                    scalar_defs, dummies, context, target_hgrid_id, zgrid_id, pingvars)
            xml_file.append(psol_field)
        else:
            print("Warning: Cannot complement model levels with psol for variable %s and table %s" %
                  (sv.label, sv.frequency))

    #
    names = OrderedDict()
    if sv.spatial_shp in ['XY-A', 'S-A']:
        # add entries for auxilliary variables : ap, ap_bnds, b, b_bnds
        names["ap"] = "vertical coordinate formula term: ap(k)"
        names["ap_bnds"] = "vertical coordinate formula term: ap(k+1/2)"
        names["b"] = "vertical coordinate formula term: b(k)"
        names["b_bnds"] = "vertical coordinate formula term: b(k+1/2)"
    elif sv.spatial_shp in ['XY-AH', 'S-AH']:
        # add entries for auxilliary variables : ap, ap_bnds, b, b_bnds
        names["ahp"] = "vertical coordinate formula term: ap(k)"
        names["ahp_bnds"] = "vertical coordinate formula term: ap(k+1/2)"
        names["bh"] = "vertical coordinate formula term: b(k)"
        names["bh_bnds"] = "vertical coordinate formula term: b(k+1/2)"

    for tab in list(names):
        ping_variable_prefix = get_variable_from_lset_without_default("ping_variables_prefix")
        attrib_dict = OrderedDict()
        attrib_dict["field_ref"] = "".join([ping_variable_prefix, tab])
        attrib_dict["name"] = tab.replace('h', '')
        attrib_dict["long_name"] = names[tab]
        attrib_dict["operation"] = "once"
        attrib_dict["prec"] = "8"
        create_xml_sub_element(xml_element=xml_file, tag="field", attrib=attrib_dict)
    actually_written_vars.append((sv.label, sv.long_name, sv.mipTable, sv.frequency, sv.Priority, sv.spatial_shp))
    # Add content to xml_file to out
    out.append(xml_file)


def create_xios_aux_elmts_defs(sv, alias, table, field_defs, axis_defs, grid_defs, domain_defs, scalar_defs, dummies,
                               context, target_hgrid_id, zgrid_id, pingvars):
    """
    Create a field_ref string for a simplified variable object sv (with
    lab prefix for the variable name) and returns it

    Add field definitions for intermediate variables in dict field_defs
    Add axis  definitions for interpolations in dict axis_defs
    Use pingvars as the list of variables actually defined in ping file

    """
    # By convention, field references are built as prefix_<MIP_variable_name>
    # Such references must be fulfilled using a dedicated field_def
    # section implementing the match between legacy model field names
    # and such names, called 'ping section'
    #
    # Identify which 'ping' variable ultimatley matches the requested
    # CMOR variable, based on shapes. This may involve building
    # intermediate variables, in order to  apply corresponding operations

    # The preferred order of operation is : vertical interp (which
    # is time-dependant), time-averaging, horizontal operations (using
    # expr=@this)
    #
    # --------------------------------------------------------------------
    # Build XIOS axis elements (stored in axis_defs)
    # Proceed with vertical interpolation if needed
    # ---
    # Build XIOS auxiliary field elements (stored in field_defs)
    # --------------------------------------------------------------------
    ssh = sv.spatial_shp
    prefix = get_variable_from_lset_without_default("ping_variables_prefix")

    # The id of the currently most downstream field is last_field_id
    last_field_id = alias

    context_index = get_config_variable("context_index")

    if sv.type == "dev":
        alias_ping = alias
        if alias_ping in context_index:
            grid_id_in_ping = id2gridid(alias_ping, context_index)
            sv.description = None
        else:
            (grid_id, grid_ref) = sv.description.split("|")
            sv.description = None
            field_dict = OrderedDict()
            field_dict["id"] = alias_ping
            field_dict["long_name"] = sv.long_name
            field_dict["standard_name"] = sv.stdname
            field_dict["unit"] = sv.units
            if grid_ref == "native":
                grid_ref = ""
            else:
                field_dict["grid_ref"] = grid_ref
            field_def = create_xml_element(tag="field", attrib=field_dict)
            field_defs[alias_ping] = field_def
            grid_id_in_ping = context_index[grid_id].attrib["id"]
    else:
        alias_ping = ping_alias(sv, pingvars)
        grid_id_in_ping = id2gridid(alias_ping, context_index)
    last_grid_id = grid_id_in_ping
    # last_grid_id=None
    #
    grid_with_vertical_interpolation = None

    # translate 'outermost' time cell_methods to Xios 'operation')
    operation, detect_missing, clim = analyze_cell_time_method(sv.cell_methods, sv.label, table, printout=False)
    #
    # --------------------------------------------------------------------
    # Handle vertical interpolation, both XY-any and Y-P outputs
    # --------------------------------------------------------------------
    #
    # if ssh[0:4] in ['XY-H','XY-P'] or ssh[0:3] == 'Y-P' or \
    # must exclude COSP outputs which are already interpolated to height or P7 levels
    if (ssh[0:4] == 'XY-P' and ssh != 'XY-P7') or \
            ssh[0:3] == 'Y-P' or \
            ((ssh[0:5] == 'XY-na' or ssh[0:4] == 'Y-na' or ssh == "XY-perso") and
             prefix + sv.label not in pingvars and sv.label_without_psuffix != sv.label):
        # TBD check - last case is for singleton
        last_grid_id, last_field_id = process_vertical_interpolation(sv, alias, pingvars, last_grid_id, field_defs,
                                                                     axis_defs, grid_defs, domain_defs, table)
        # If vertical interpolation is done, change the value of those boolean to modify the behaviour of dr2xml
        grid_with_vertical_interpolation = True

    #
    # --------------------------------------------------------------------
    # Handle the case of singleton dimensions
    # --------------------------------------------------------------------
    #
    if has_singleton(sv):
        last_field_id, last_grid_id = process_singleton(sv, last_field_id, pingvars, field_defs, grid_defs, scalar_defs,
                                                        table)
    #
    # TBD : handle explicitly the case of scalars (global means, shape na-na) :
    # enforce <scalar name="sector" standard_name="region" label="global" >, or , better,
    # remove the XIOS-generated scalar introduced by reduce_domain
    #
    # --------------------------------------------------------------------
    # Handle zonal means
    # --------------------------------------------------------------------
    #
    if ssh[0:2] == 'Y-':  # zonal mean and atm zonal mean on pressure levels
        last_field_id, last_grid_id = \
            process_zonal_mean(last_field_id, last_grid_id, target_hgrid_id, zgrid_id, field_defs, axis_defs, grid_defs,
                               domain_defs, operation, sv.frequency)

    #
    # --------------------------------------------------------------------
    # Build a construct for computing a climatology (if applicable)
    # --------------------------------------------------------------------
    if clim:
        if sv.frequency == "1hrCM":
            last_field_id, last_grid_id = process_diurnal_cycle(last_field_id, field_defs, grid_defs, axis_defs)
        else:
            raise dr2xml_error("Cannot handle climatology cell_method for frequency %s and variable "
                               % sv.frequency, sv.label)
    #
    # --------------------------------------------------------------------
    # Create intermediate field_def for enforcing operation upstream
    # --------------------------------------------------------------------
    #
    but_last_field_id = last_field_id
    last_field_id = last_field_id + "_" + operation
    last_field_dict = OrderedDict()
    last_field_dict["id"] = last_field_id
    last_field_dict["field_ref"] = but_last_field_id
    last_field_dict["operation"] = operation
    field_defs[last_field_id] = create_xml_element(tag="field", attrib=last_field_dict)
    #
    # --------------------------------------------------------------------
    # Change horizontal grid if requested
    # --------------------------------------------------------------------
    #
    if target_hgrid_id:
        # This does not apply for a series of shapes
        if ssh[0:2] == 'Y-' or ssh == 'na-na' or ssh == 'TR-na' or ssh == 'TRS-na' or ssh[
                                                                                      0:3] == 'YB-' or ssh == 'na-A':
            pass
        else:
            if target_hgrid_id == cfsites_domain_id:
                add_cfsites_in_defs(grid_defs, domain_defs)
            # Apply DR required remapping, either toward cfsites grid or a regular grid
            last_grid_id = change_domain_in_grid(target_hgrid_id, grid_defs, src_grid_id=last_grid_id)
    #
    # --------------------------------------------------------------------
    # Change axes in grid to CMIP6-compliant ones
    # --------------------------------------------------------------------
    #
    last_grid_id = change_axes_in_grid(last_grid_id, grid_defs, axis_defs)
    #
    # --------------------------------------------------------------------
    # Create <field> construct to be inserted in a file_def, which includes re-griding
    # --------------------------------------------------------------------
    #
    rep_dict = OrderedDict()
    rep_dict["field_ref"] = last_field_id
    if sv.label == "tsland":
        rep_dict["name"] = "tsland"
    else:
        rep_dict["name"] = sv.mipVarLabel
    if last_grid_id != grid_id_in_ping:
        rep_dict["grid_ref"] = last_grid_id
    #
    #
    # --------------------------------------------------------------------
    # Add offset if operation=instant for some specific variables defined in lab_settings
    # --------------------------------------------------------------------
    #
    if operation == 'instant':
        for ts in get_variable_from_lset_with_default('special_timestep_vars', []):
            if sv.label in get_variable_from_lset_without_default('special_timestep_vars', ts):
                xios_freq = Cmip6Freq2XiosFreq(sv.frequency, table)
                # works only if units are different :
                rep_dict["freq_offset"] = "-".join([xios_freq, ts])
    #
    # --------------------------------------------------------------------
    # handle data type and missing value
    # --------------------------------------------------------------------
    #
    detect_missing = "True"
    missing_value = "1.e+20"
    if sv.prec.strip() in ["float", "real", ""]:
        prec = "4"
    elif sv.prec.strip() == "double":
        prec = "8"
    elif sv.prec.strip() == "integer" or sv.prec.strip() == "int":
        prec = "2"
        missing_value = "0"  # 16384"
    else:
        raise dr2xml_error("prec=%s for sv=%s" % (sv.prec, sv.label))
    rep_dict["detect_missing_value"] = detect_missing
    rep_dict["default_value"] = missing_value
    rep_dict["prec"] = prec
    #
    # TBD : implement DR recommendation for cell_method : The syntax is to append, in brackets,
    # TBD    'interval: *amount* *units*', for example 'area: time: mean (interval: 1 hr)'.
    # TBD    The units must be valid UDUNITS, e.g. day or hr.
    rep_dict["cell_methods"] = sv.cell_methods
    rep_dict["cell_methods_mode"] = "overwrite"
    # --------------------------------------------------------------------
    # enforce time average before remapping (when there is one) except if there
    # is an expr, set in ping for the ping variable of that field, and which
    # involves time operation (using @)
    # --------------------------------------------------------------------
    rep_dict["operation"] = operation
    #
    if not idHasExprWithAt(alias, context_index):
        # either no expr, or expr without an @  ->
        # may use @ for optimizing operations order (average before re-gridding)
        if last_grid_id != grid_id_in_ping:
            if operation in ['average', 'instant']:
                # do use @ for optimizing :
                rep_dict["freq_op"] = longest_possible_period(Cmip6Freq2XiosFreq(sv.frequency, table),
                                                              get_variable_from_lset_with_default("too_long_periods",
                                                                                                  []))
                # must set freq_op (this souldn't be necessary, but is needed with Xios 1442)
                rep_dict["freq_op"] = longest_possible_period(Cmip6Freq2XiosFreq(sv.frequency, table),
                                                              get_variable_from_lset_with_default("too_long_periods",
                                                                                                  []))
    else:  # field has an expr, with an @
        # Cannot optimize
        if operation == 'instant':
            # must reset expr (if any) if instant, for using arithm. operation defined in ping.
            # this allows that the type of operation applied is really 'instant', and not the one
            # that operands did inherit from ping_file
            rep_dict["expr"] = "_reset_"
        if operation == 'average':
            warnings_for_optimisation.append(alias)
        rep_dict["freq_op"] = longest_possible_period(Cmip6Freq2XiosFreq(sv.frequency, table),
                                                      get_variable_from_lset_with_default("too_long_periods", []))

    rep = create_xml_element(tag="field", attrib=rep_dict)

    if not idHasExprWithAt(alias, context_index) and last_grid_id != grid_id_in_ping:
        # either no expr, or expr without an @  ->
        # may use @ for optimizing operations order (average before re-gridding)
        if operation == 'average':
            # do use @ for optimizing :
            rep.text = "@{}".format(last_field_id)
        elif operation == 'instant' and get_variable_from_lset_with_default("useAtForInstant", False):
            rep.text = "@{}".format(last_field_id)
    #
    # --------------------------------------------------------------------
    # Add Xios variables for creating NetCDF attributes matching CMIP6 specs
    # --------------------------------------------------------------------
    comment = None
    # Process experiment-specific comment for the variable
    if sv.label in get_variable_from_sset_without_default('comments'):
        comment = get_variable_from_sset_without_default('comments', sv.label)
    else:  # Process lab-specific comment for the variable
        if sv.label in get_variable_from_lset_without_default('comments'):
            comment = get_variable_from_lset_without_default('comments', sv.label)
    if comment:
        rep.append(wrv('comment', comment))  # TBI
    #
    if sv.stdname:
        rep.append(wrv("standard_name", sv.stdname))
    #
    desc = sv.description
    # if desc :
    # desc=desc.replace(">","&gt;").replace("<","&lt;").replace("&","&amp;").replace("'","&apos;").replace('"',"&quot;")
    if desc:
        desc = desc.replace(">", "&gt;").replace("<", "&lt;").strip()
    rep.append(wrv("description", desc))
    #
    rep.append(wrv("long_name", sv.long_name))
    if sv.positive != "None" and sv.positive != "":
        rep.append(wrv("positive", sv.positive))
    rep.append(wrv('history', 'none'))
    if sv.units:
        rep.append(wrv('units', sv.units))
    if sv.cell_methods:
        if get_variable_from_sset_with_default("CORDEX_data", False) and "area: time: mean" in sv.cell_methods:
            rep.append(wrv("cell_methods", "time:mean"))
        else:
            rep.append(wrv('cell_methods', sv.cell_methods))
    if sv.cell_measures:
        rep.append(wrv('cell_measures', sv.cell_measures))
    #
    if sv.struct is not None:
        fmeanings = sv.struct.flag_meanings
        if fmeanings is not None and fmeanings.strip() != '':
            rep.append(wrv('flag_meanings', fmeanings.strip()))
        fvalues = sv.struct.flag_values
        if fvalues is not None and fvalues.strip() != '':
            rep.append(wrv('flag_values', fvalues.strip()))
    if get_variable_from_sset_with_default("CORDEX_data", False):
        rep.append(wrv('grid_mapping', "Lambert_Conformal"))
    #
    # We override the Xios value for interval_operation because it sets it to
    # the freq_output value with our settings (for complicated reasons)
    if grid_with_vertical_interpolation:
        interval_op = get_variable_from_lset_without_default("vertical_interpolation_sample_freq")
    else:
        source, source_type = get_source_id_and_type()
        grid_choice = get_variable_from_lset_without_default("grid_choice", source)
        interval_op = repr(int(get_variable_from_lset_without_default('sampling_timestep', grid_choice, context))) + \
                      " s"
    if operation != 'once':
        rep.append(wrv('interval_operation', interval_op))

    # mpmoine_note: 'missing_value(s)' normalement plus necessaire, a verifier
    # TBS rep.append(wrv("missing_values", sv.missing, num_type="double"))
    #
    return rep


def process_singleton(sv, alias, pingvars, field_defs, grid_defs, scalar_defs, table):
    """
    Based on singleton dimensions of variable SV, and assuming that this/these dimension(s)
    is/are not yet represented by a scalar Xios construct in corresponding field's grid,
    creates a further field with such a grid, including creating the scalar and
    re-using the domain of original grid

    """

    printout = False
    # get grid for the variable , before vertical interpo. if any
    # (could rather use last_grid_id and analyze if it has pressure dim)
    alias_ping = ping_alias(sv, pingvars)
    context_index = get_config_variable("context_index")
    input_grid_id = id2gridid(alias_ping, context_index)
    input_grid_def = get_grid_def_with_lset(input_grid_id, grid_defs)
    if printout:
        print("process_singleton : ", "processing %s with grid %s " % (alias, input_grid_id))
    #
    further_field_id = alias
    further_grid_id = input_grid_id
    further_grid_def = input_grid_def
    #
    # for each sv's singleton dimension, create the scalar, add a scalar
    # construct in a further grid, and convert field to a further field
    for dimk in sorted(list(sv.sdims)):
        sdim = sv.sdims[dimk]
        if is_singleton(sdim):  # Only one dim should match
            #
            # Create a scalar for singleton dimension
            # sdim.label is non-ambiguous id, thanks to the DR, but its value may be
            # ambiguous w.r.t. a dr2xml suffix for interpolating to a single pressure level
            scalar_id = "Scal" + sdim.label
            name = sdim.out_name
            # These dimensions are shared by some variables with another sdim with same out_name ('type'):
            if sdim.label in ["typec3pft", "typec4pft"]:
                name = "pfttype"
            #
            scalar_dict = OrderedDict()
            scalar_dict["id"] = scalar_id
            scalar_dict["name"] = name
            #
            if sdim.stdname.strip() != '' and sdim.label != "typewetla":
                scalar_dict["standard_name"] = sdim.stdname
            #
            scalar_dict["long_name"] = sdim.title
            #
            if sdim.type == 'character':
                scalar_dict["label"] = sdim.label
            else:
                types = {'double': '8', 'float': '4', 'integer': '2'}
                scalar_dict["prec"] = types[sdim.type]
                scalar_dict["value"] = sdim.value
            #
            if sdim.bounds == "yes":
                try:
                    bounds = sdim.boundsValues.split()
                    scalar_dict["bounds"] = "(0,1)[ {} {} ]".format(bounds[0], bounds[1])
                    scalar_dict["bounds_name"] = "{}_bounds".format(sdim.out_name)
                except:
                    if sdim.label != "lambda550nm":
                        raise dr2xml_error("Issue for var %s with dim %s bounds=%s" % (sv.label, sdim.label, bounds))
            #
            if sdim.axis != '':
                # Space axis, probably Z
                scalar_dict["axis_type"] = sdim.axis
                if sdim.positive:
                    scalar_dict["positive"] = sdim.positive
            #
            if sdim.units != '':
                scalar_dict["unit"] = sdim.units
            #
            scalar_def = create_xml_element(tag="scalar", attrib=scalar_dict)
            scalar_defs[scalar_id] = scalar_def
            if printout:
                print("process_singleton : ", "adding scalar %s" % create_string_from_xml_element(scalar_def))
            #
            # Create a grid with added (or changed) scalar
            glabel = further_grid_id + "_" + scalar_id
            further_grid_def = add_scalar_in_grid(further_grid_def, glabel, scalar_id, name,
                                                  sdim.axis == "Z" and further_grid_def != "NATURE_landuse")
            if printout:
                print("process_singleton : ", " adding grid %s" % create_string_from_xml_element(further_grid_def))
            grid_defs[glabel] = further_grid_def
            further_grid_id = glabel

    # Compare grid definition (in case the input_grid already had correct ref to scalars)
    if further_grid_def != input_grid_def:
        #  create derived_field through an Xios operation (apply all scalars at once)
        further_field_id = alias + "_" + further_grid_id.replace(input_grid_id + '_', '')
        # Must init operation and detect_missing when there is no field ref
        field_def_dict = OrderedDict()
        field_def_dict["id"] = further_field_id
        field_def_dict["grid_ref"] = further_grid_id
        field_def_dict["operation"] = "instant"
        field_def_dict["detect_missing_value"] = "true"
        field_def = create_xml_element(tag="field", text=alias, attrib=field_def_dict)
        field_defs[further_field_id] = field_def
        if printout:
            print("process_singleton : ", " adding field %s" % create_string_from_xml_element(field_def))
    return further_field_id, further_grid_id


def has_singleton(sv):
    """
    Determine if a variable has a singleton dimension.
    :param sv: variable
    :return: boolean indicating whether the variable has a singleton dimension
    """
    rep = any([is_singleton(sv.sdims[k]) for k in sv.sdims])
    return rep


def is_singleton(sdim):
    """
    Based on sdim (dimensions) characteristics, determine if it corresponds to a singleton
    :param sdim: dimensions characteristics
    :return: boolean indicating whether sdim corresponds to a singleton or not
    """
    if sdim.axis == '':
        # Case of non-spatial dims. Singleton only have a 'value' (except Scatratio has a lot (in DR01.00.21))
        return sdim.value != '' and len(sdim.value.strip().split(" ")) == 1
    else:
        # Case of space dimension singletons. Should a 'value' and no 'requested'
        return ((sdim.value != '') and (sdim.requested.strip() == '')) \
               or (sdim.label == "typewetla")  # The latter is a bug in DR01.00.21 : typewetla has no value there


def add_scalar_in_grid(gridin_def, gridout_id, scalar_id, scalar_name, remove_axis, change_scalar=True):
    """
    Returns a grid_definition with id GRIDOUT_ID from an input grid definition
    GRIDIN_DEF, by adding a reference to scalar SCALAR_ID

    If CHANGE_SCALAR is True and GRIDIN_DEF has an axis with an extract_axis child,
    remove it (because it is assumed to be a less well-defined proxy for the DR scalar

    If such a reference is already included in that grid definition, just return
    input def

    if REMOVE_AXIS is True, if GRIDIN_DEF already includes an axis, remove it for output grid

    Note : name of input_grid is not changed in output_grid

    """
    rep = gridin_def.copy()
    test_scalar_in_grid = False
    for child in rep:
        if child.tag == "scalar":
            if "scalar_ref" in child.attrib and child.attrib["scalar_ref"] == scalar_id:
                test_scalar_in_grid = True
    if test_scalar_in_grid:
        return rep
    # TBD : in change_scalar : discard extract_axis only if really relevant (get the right axis)
    # TBD : in change_scalar : preserve ordering of domains/axes...
    if change_scalar:
        count = 0
        children_to_remove = list()
        for child in rep:
            test_child = False
            if child.tag == "scalar":
                for scalar_child in child:
                    if scalar_child.tag == "extract_axis":
                        test_child = True
            if test_child:
                count += 1
                children_to_remove.append(child)
        for child_to_remove in children_to_remove:
            rep.remove(child_to_remove)
    if "id" in rep.attrib:
        rep.attrib["id"] = gridout_id
        scalar_dict = OrderedDict()
        scalar_dict["scalar_ref"] = scalar_id
        scalar_dict["name"] = scalar_name
        create_xml_sub_element(xml_element=rep, tag="scalar", attrib=scalar_dict)
    else:
        raise dr2xml_error("No way to add scalar '%s' in grid '%s'" % (scalar_id, gridin_def))
    # Remove any axis if asked for
    if remove_axis:
        remove_subelement_in_xml_element(xml_element=rep, tag="axis")
        # if count==1 :
        #    print "Info: axis has been removed for scalar %s (%s)"%(scalar_name,scalar_id)
        #    print "grid_def="+rep
    return rep


def wrv(name, value, num_type="string"):
    """
    Create a string corresponding of a variable for Xios files.
    :param name: name of the variable
    :param value: value of the variable
    :param num_type: type of the variable
    :return: string corresponding to the xml variable
    """
    print_variables = get_variable_from_lset_with_default("print_variables", True)
    if not print_variables:
        return None
    elif isinstance(print_variables, list) and name not in print_variables:
        return None
    if isinstance(value, str):
        value = value[0:1024]  # CMIP6 spec : no more than 1024 char
    # Format a 'variable' entry
    attrib_dict = OrderedDict()
    attrib_dict["name"] = name
    attrib_dict["type"] = num_type
    return create_xml_element(tag="variable", text=str(value), attrib=attrib_dict)


def make_source_string(sources, source_id):
    """
    From the dic of sources in CMIP6-CV, Creates the string representation of a
    given model (source_id) according to doc on global_file_attributes, so :

    <modified source_id> (<year>): atmosphere: <model_name> (<technical_name>, <resolution_and_levels>);
    ocean: <model_name> (<technical_name>, <resolution_and_levels>); sea_ice: <model_name> (<technical_name>);
    land: <model_name> (<technical_name>); aerosol: <model_name> (<technical_name>);
    atmospheric_chemistry <model_name> (<technical_name>); ocean_biogeochemistry <model_name> (<technical_name>);
    land_ice <model_name> (<technical_name>);

    """
    # mpmoine_correction:make_source_string: pour lire correctement le fichier 'CMIP6_source_id.json'
    source = sources[source_id]
    components = source['model_component']
    rep = source_id + " (" + source['release_year'] + "): "
    for realm in ["aerosol", "atmos", "atmosChem", "land", "ocean", "ocnBgchem", "seaIce"]:
        component = components[realm]
        description = component['description']
        if description != "none":
            rep = rep + "\n" + realm + ": " + description
    return rep


def write_xios_file_def(filename, svars_per_table, year, lset, sset, cvs_path, field_defs, axis_defs, grid_defs,
                        scalar_defs, file_defs, dummies, skipped_vars_per_table, actually_written_vars, prefix, context,
                        pingvars=None, enddate=None, attributes=[]):
    """
    Write XIOS file_def.
    """
    # --------------------------------------------------------------------
    # Start writing XIOS file_def file:
    # file_definition node, including field child-nodes
    # --------------------------------------------------------------------
    # Create xml element for context
    xml_context = create_xml_element(tag="context", attrib=OrderedDict(id=context))
    # Add all comments
    add_xml_comment_to_element(element=xml_context, text="CMIP6 Data Request version {}".format(get_DR_version()))
    add_xml_comment_to_element(element=xml_context, text="CMIP6-CV version {}".format("??"))
    add_xml_comment_to_element(element=xml_context,
                               text="CMIP6_conventions_version {}".format(get_config_variable("CMIP6_conventions_version")))
    add_xml_comment_to_element(element=xml_context, text="dr2xml version {}".format(get_config_variable("version")))
    add_xml_comment_to_element(element=xml_context,
                               text="\n".join(["Lab_and_model settings", format_dict_for_printing("lset")]))
    add_xml_comment_to_element(element=xml_context,
                               text="\n".join(["Simulation settings", format_dict_for_printing("sset")]))
    add_xml_comment_to_element(element=xml_context, text="Year processed {}".format(year))
    # Initialize some variables
    domain_defs = OrderedDict()
    foo, sourcetype = get_source_id_and_type()
    # Add xml_file_definition
    xml_file_dict = OrderedDict()
    xml_file_dict["type"] = "one_file"
    xml_file_dict["enabled"] = "true"
    xml_file_definition = create_xml_element(tag="file_definition", attrib=xml_file_dict)
    # Loop on values to fill the xml element
    for table in sorted(list(svars_per_table)):
        count = OrderedDict()
        for svar in sorted(svars_per_table[table], key=lambda x: (x.label + "_" + table)):
            if get_variable_from_lset_with_default("allow_duplicates_in_same_table", False) \
                    or svar.mipVarLabel not in count:
                if not get_variable_from_lset_with_default("use_cmorvar_label_in_filename", False) \
                        and svar.mipVarLabel in count:
                    form = "If you really want to actually produce both %s and %s in table %s, " + \
                           "you must set 'use_cmorvar_label_in_filename' to True in lab settings"
                    raise dr2xml_error(form % (svar.label, count[svar.mipVarLabel].label, table))
                count[svar.mipVarLabel] = svar
                for grid in svar.grids:
                    a, hgrid, b, c, d = get_variable_from_lset_without_default('grids', get_grid_choice(), context)
                    check_for_file_input(svar, hgrid, pingvars, field_defs, grid_defs, domain_defs, file_defs)
                    write_xios_file_def_for_svar(svar, year, table, lset, sset, xml_file_definition, cvs_path,
                                                 field_defs, axis_defs, grid_defs, domain_defs, scalar_defs, file_defs,
                                                 dummies, skipped_vars_per_table, actually_written_vars,
                                                 prefix, context, grid, pingvars, enddate, attributes)
            else:
                print("Duplicate variable %s,%s in table %s is skipped, preferred is %s" %
                      (svar.label, svar.mipVarLabel, table, count[svar.mipVarLabel].label))
    # Add cfsites if needed
    if cfsites_grid_id in grid_defs:
        xml_file_definition.append(cfsites_input_filedef())
    # Add other file definitions
    for file_def in file_defs:
        xml_file_definition.append(file_defs[file_def])
    xml_context.append(xml_file_definition)
    #
    # --------------------------------------------------------------------
    # End writing XIOS file_def file:
    # field_definition, axis_definition, grid_definition
    # and domain_definition auxilliary nodes
    # --------------------------------------------------------------------
    # Write all domain, axis, field defs needed for these file_defs
    xml_field_definition = create_xml_element(tag="field_definition")
    is_reset_field_group = get_variable_from_lset_with_default("nemo_sources_management_policy_master_of_the_world",
                                                               False) and context == 'nemo'
    if is_reset_field_group:
        xml_field_group_dict = OrderedDict()
        xml_field_group_dict["freq_op"] = "_reset_"
        xml_field_group_dict["freq_offset"] = "_reset_"
        xml_field_group = create_xml_element(tag="field_group", attrib=xml_field_group_dict)
        for xml_field in list(field_defs):
            xml_field_group.append(field_defs[xml_field])
        xml_field_definition.append(xml_field_group)
    else:
        for xml_field in list(field_defs):
            xml_field_definition.append(field_defs[xml_field])
    xml_context.append(xml_field_definition)
    #
    xml_axis_definition = create_xml_element(tag="axis_definition")
    xml_axis_group = create_xml_element(tag="axis_group", attrib=OrderedDict(prec="8"))
    for xml_axis in list(axis_defs):
        xml_axis_group.append(axis_defs[xml_axis])
    if False and get_variable_from_lset_with_default('use_union_zoom', False):
        for xml_axis in list(union_axis_defs):
            xml_axis_group.append(union_axis_defs[xml_axis])
    xml_axis_definition.append(xml_axis_group)
    xml_context.append(xml_axis_definition)
    #
    xml_domain_definition = create_xml_element(tag="domain_definition")
    xml_domain_group = create_xml_element(tag="domain_group", attrib=OrderedDict(prec="8"))
    if get_variable_from_lset_without_default('grid_policy') != "native":
        create_standard_domains(domain_defs)
    for xml_domain in list(domain_defs):
        xml_domain_group.append(domain_defs[xml_domain])
    xml_domain_definition.append(xml_domain_group)
    xml_context.append(xml_domain_definition)
    #
    xml_grid_definition = create_xml_element(tag="grid_definition")
    for xml_grid in list(grid_defs):
        xml_grid_definition.append(grid_defs[xml_grid])
    if False and get_variable_from_lset_with_default('use_union_zoom', False):
        for xml_grid in list(union_grid_defs):
            xml_grid_definition.append(union_grid_defs[xml_grid])
    xml_context.append(xml_grid_definition)
    #
    xml_scalar_definition = create_xml_element(tag="scalar_definition")
    for xml_scalar in list(scalar_defs):
        xml_scalar_definition.append(scalar_defs[xml_scalar])
    xml_context.append(xml_scalar_definition)
    # Write the xml element to the dedicated file
    create_pretty_xml_doc(xml_element=xml_context, filename=filename)
