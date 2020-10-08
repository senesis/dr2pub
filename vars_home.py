#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Variables general tools.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from six import string_types
from collections import OrderedDict

import sys
import os
import json
import re
from io import open

# DR interface
from dr_interface import get_collection, get_uid, get_cmor_var_id_by_label, print_DR_stdname_errors, print_DR_errors

# Settings dictionaries interface
from settings_interface import get_variable_from_sset_else_lset_with_default, get_variable_from_lset_with_default, \
    get_variable_from_lset_without_default, get_variable_from_sset_with_default

from vars_cmor import get_cmor_var, get_spatial_and_temporal_shapes, analyze_ambiguous_mip_varnames, SimpleCMORVar, \
    SimpleDim
from analyzer import guess_freq_from_table_name, cellmethod2area
from utils import VarsError


# List of multi and single pressure level suffixes for which we want the union/zoom axis mecanism turned on
# For not using union/zoom, set 'use_union_zoom' to False in lab settings

# SS : le jeu plev7c est un jeu de couches du simulateur ISCCP - pas d'interpolation
# multi_plev_suffixes=set(["10","19","23","27","39","3","3h","4","7c","7h","8","12"])
multi_plev_suffixes = set(["10", "19", "23", "27", "39", "3", "3h", "4", "7h", "8", "12"])

# SS : les niveaux 220, 560 et 840 sont des couches du simulateur ISCCP - pas d'interpolation
# single_plev_suffixes=set(["1000","200","220","500","560","700","840","850","100"])
single_plev_suffixes = set(["1000", "200", "500", "700", "850", "100"])

ambiguous_mipvarnames = None

# 2 dicts for processing home variables
# 2 dicts and 1 list for processing extra variables
dims2shape = OrderedDict()
dim2dimid = OrderedDict()
dr_single_levels = list()
stdName2mipvarLabel = OrderedDict()
tcmName2tcmValue = {"time-mean": "time: mean", "time-point": "time: point"}
# A dict for storing home_variables issues re. standard_names
sn_issues_home = OrderedDict()
homevars_list = None


def read_home_vars_list(hmv_file, expid, mips, path_extra_tables=None, printout=False):
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
    global homevars_list
    #
    if hmv_file is None:
        return []
    if homevars_list is not None:
        return homevars_list
    # File structure: name of attributes to read, number of header line
    home_attrs = ['type', 'label', 'modeling_realm', 'frequency', 'mipTable', 'temporal_shp', 'spatial_shp',
                  'experiment', 'mip']
    dev_home_attrs = ['units', 'long_name', 'stdname']
    data = []
    file_list = hmv_file.replace('  ', ' ').split(' ')
    for fil in file_list:
        if fil.strip() == '':
            continue
        if not os.path.exists(fil):
            raise VarsError("Abort: file for home variables does not exist: %s" % fil)
        # Read file
        with open(fil, "r") as fp:
            data.extend(fp.readlines())
    # Build list of home variables
    homevars = []
    extravars = []
    extra_vars_per_table = OrderedDict()
    for line in [l for l in data if len(l) > 0 and not l.startswith("#")]:
        line_split = line.split(';')
        # get the Table full name
        table = line_split[4].strip(' ')
        # overwrite  5th column with table name without prefix
        if table != 'NONE':
            if '_' not in table:
                sys.exit("Abort: a prefix is expected in extra Table name: " + table)
            line_split[4] = table.split('_')[1]
        hmv_type = line_split[0].strip(' ')
        # Build the list of attributes
        # If extra, the table can be added as a whole or by variable
        extra_tables = []
        # if hmv_type!='extra':
        home_var = SimpleCMORVar()
        # Build the line that will contain all useful elements
        line_to_treat = []
        for col in line_split:
            ccol = col.lstrip(' ').rstrip('\n\t ')
            if ccol != '':
                line_to_treat.append(ccol)
        # Get the last columns in case of dev variable
        if hmv_type == "dev":
            for (key, value) in zip(home_attrs+dev_home_attrs, line_to_treat):
                setattr(home_var, key, value)
            # Add the grids description (grid_id and grid_ref)
            remain_attrs = line_to_treat[len(home_attrs+dev_home_attrs):]
            if len(remain_attrs) < 2:
                raise VarsError("Missing geometry description for dev variable {}.".format(home_var.label))
            else:
                # Consider the two first items to be grids description
                home_var.description = "|".join(remain_attrs)
        else:
            for (key, value) in zip(home_attrs, line_to_treat):
                setattr(home_var, key, value)

        if hmv_type != 'extra':
            home_var.label_with_area = home_var.label
            if hmv_type == 'perso':
                home_var.mip_era = 'PERSO'
                home_var.cell_methods = tcmName2tcmValue[home_var.temporal_shp]
                home_var.label_without_psuffix = home_var.label
                home_var.cell_measures = ""
            elif hmv_type == "dev":
                home_var.mip_era = 'DEV'
                home_var.mipVarLabel = home_var.label
                if home_var.frequency == "fx":
                    home_var.cell_methods = None
                else:
                    home_var.cell_methods = tcmName2tcmValue[home_var.temporal_shp]
                home_var.label_without_psuffix = home_var.label
                home_var.cell_measures = ""
            if home_var.spatial_shp == "XY-perso":
                home_var_sdims_info = get_variable_from_sset_with_default('perso_sdims_description', OrderedDict())
                if home_var.label in home_var_sdims_info:
                    home_var_sdims = OrderedDict()
                    for home_var_dim in home_var_sdims_info[home_var.label]:
                        home_var_sdim = SimpleDim()
                        home_var_sdim.label = home_var_dim
                        for sdim_key in ["zoom_label", "stdname", "long_name", "positive", "requested", "value",
                                         "out_name", "units", "is_zoom_of", "bounds", "boundsValue", "axis", "type",
                                         "coords", "title", "is_union_for"]:
                            if sdim_key in home_var_sdims_info[home_var.label][home_var_dim]:
                                setattr(home_var_dim, sdim_key,
                                        home_var_sdims_info[home_var.label][home_var_dim][sdim_key])
                        home_var_sdims[home_var_dim] = home_var_sdim
                    home_var.sdims = home_var_sdims
                else:
                    print ("Could not find custom sdims for {} in simulation settings.".format(home_var.label))
                    raise VarsError("Could not find custom sdims for %s in simulation settings." % home_var.label)
            actual_mip = home_var.mip
            if actual_mip.startswith(r"[") and actual_mip.endswith(r"]"):
                new_mip = actual_mip[1:]
                new_mip = new_mip[:-1]
                new_mip = new_mip.split(",")
                home_var.mip = new_mip
            if (isinstance(home_var.mip, string_types) and (home_var.mip == "ANY" or home_var.mip in mips)) or \
                    (isinstance(home_var.mip, list) and mips.issuperset(home_var.mip)):
                if home_var.experiment != "ANY":
                    # if home_var.experiment==expid: homevars.append(home_var)
                    if expid in home_var.experiment:
                        homevars.append(home_var)
                else:
                    homevars.append(home_var)
        else:
            if table not in extra_vars_per_table:
                extra_vars_per_table[table] = read_extra_table(path_extra_tables, table, printout=printout)
            if home_var.label == "ANY":
                if home_var.mip == "ANY" or home_var.mip in mips:
                    if home_var.experiment != "ANY":
                        if expid in home_var.experiment:
                            extravars.extend(extra_vars_per_table[table])
                    else:
                        extravars.extend(extra_vars_per_table[table])
            else:
                # find home_var in extra_vars
                var_found = None
                for var in extra_vars_per_table[table]:
                    if var.label == home_var.label:
                        var_found = var
                        break
                if var_found is None:
                    print("Warning: 'extra' variable %s not found in table %s" % (home_var.label, table))
                else:
                    if home_var.mip == "ANY" or home_var.mip in mips:
                        if home_var.experiment != "ANY":
                            if expid in home_var.experiment:
                                extravars.append(var_found)
                        else:
                            extravars.append(var_found)
    if printout:
        print("Number of 'cmor', 'dev' and 'perso' among home variables: ", len(homevars))
        print("Number of 'extra' among home variables: ", len(extravars))
    homevars.extend(extravars)
    homevars_list = homevars
    return homevars


def read_extra_table(path, table, printout=False):
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
        for sshp in get_collection('spatialShape').items:
            dims2shape[sshp.dimensions] = sshp.label
        # mpmoine_future_modif:dims2shape: ajout a la main des correpondances dims->shapes Primavera qui ne sont pas
        # couvertes par la DR
        # mpmoine_note: attention, il faut mettre a jour dim2shape a chaque fois qu'une nouvelle correpondance
        # est introduite
        # mpmoine_note: attention, dans les extra-Tables
        dims2shape['longitude|latitude|height100m'] = 'XY-na'
        # mpmoine_note: provisoire, XY-P12 juste pour exemple
        dims2shape['longitude|latitude|plev12'] = 'XY-P12'
        # mpmoine_zoom_modif:dims2shape:: ajout de XY-P23 qui a disparu de la DR-00.00.04 mais est demande dans les
        # tables Primavera
        dims2shape['longitude|latitude|plev23'] = 'XY-P23'
        # mpmoine_zoom_modif:dims2shape:: ajout de XY-P10 qui n'est pas dans la DR mais demande dans les tables
        # Primavera
        dims2shape['longitude|latitude|plev10'] = 'XY-P10'
        # David : test
        dims2shape['longitude|latitude|plev7hm'] = 'XY-P7HM'
        # Romain
        dims2shape['longitude|latitude|plev19hm'] = 'XY-P19HM'
        # By level for CORDEX
        dims2shape['longitude|latitude|plev925'] = 'XY-P925HM'
        dims2shape['longitude|latitude|plev850'] = 'XY-P850HM'
        dims2shape['longitude|latitude|plev700'] = 'XY-P700HM'
        dims2shape['longitude|latitude|plev500'] = 'XY-P500HM'
        dims2shape['longitude|latitude|plev200'] = 'XY-P200HM'
    #
    if not dim2dimid:
        for g in get_collection('grids').items:
            dim2dimid[g.label] = g.uid
    #
    if not dr_single_levels:
        for struct in get_collection('structure').items:
            spshp = get_uid(struct.spid)
            if spshp.label == "XY-na" and 'cids' in struct.__dict__:
                if struct.cids[0] != '':  # this line is needed prior to version 01.00.08.
                    c = get_uid(struct.cids[0])
                    # if c.axis == 'Z': # mpmoine_note: non car je veux dans dr_single_levels toutes les dimensions
                    # singletons (ex. 'typenatgr'), par seulement les niveaux
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
    if not os.path.exists(json_table):
        sys.exit("Abort: file for extra Table does not exist: " + json_table)
    tbl = table.split('_')[1]
    dim_from_extra = OrderedDict()
    dynamic_shapes = OrderedDict()
    with open(json_table, "r") as jt:
        json_tdata = jt.read()
        tdata = json.loads(json_tdata)
        for k, v in tdata["variable_entry"].items():
            extra_var = SimpleCMORVar()
            extra_var.type = 'extra'
            extra_var.mip_era = mip_era
            extra_var.label = v["out_name"].strip(' ')
            extra_var.mipVarLabel = extra_var.label
            extra_var.stdname = v.get("standard_name", "").strip(' ')
            extra_var.long_name = v["long_name"].strip(' ')
            extra_var.units = v["units"].strip(' ')
            extra_var.modeling_realm = v["modeling_realm"].strip(' ')
            # extra_var.frequency=table2freq[tbl][1]
            if get_variable_from_sset_with_default("CORDEX_data", False):
                extra_var.frequency = v.get("frequency", guess_freq_from_table_name(tbl)).strip(' ')
            else:
                extra_var.frequency = guess_freq_from_table_name(tbl)
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
            ind_time = []
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
            if drdims in dims2shape:
                extra_var.spatial_shp = dims2shape[drdims]
            elif drdims[0:19] == 'longitude|latitude|':
                # Allow the user to put any additional vertical dimension name
                # which syntax fits further tests, such as P8MINE
                edim = drdims[19:]
                extra_var.spatial_shp = 'XY-' + edim
                if edim not in dynamic_shapes:
                    dynamic_shapes[edim] = OrderedDict()
                if v["out_name"] not in dynamic_shapes[edim]:
                    dynamic_shapes[edim][v["out_name"]] = extra_var.spatial_shp
                # print "Warning: spatial shape corresponding to ",drdims,"for variable",v["out_name"],\
                #      "in Table",table," not explicitly known by DR nor dr2xml, trying %s"%extra_var.spatial_shp
            else:
                # mpmoine_note: provisoire, on devrait toujours pouvoir associer une spatial shape a des dimensions.
                # mpmoine_note: Je rencontre ce cas pour l'instant avec les tables Primavera ou
                # mpmoine_note: on a "latitude|longitude" au lieu de "longitude|latitude"
                print("Warning: spatial shape corresponding to ", drdims, "for variable", v["out_name"], "in Table",
                      table, " not found in DR.")
            dr_dimids = []
            for d in all_dr_dims:
                if d in dim2dimid:
                    dr_dimids.append(dim2dimid[d])
                    extra_dim, dummy = get_simple_dim_from_dim_id(dim2dimid[d])
                    extra_var.sdims[extra_dim.label] = extra_dim
                else:
                    extra_sdim = SimpleDim()
                    with open(json_coordinate, "r") as jc:
                        json_cdata = jc.read()
                        cdata = json.loads(json_cdata)
                        extra_sdim.label = d
                        extra_sdim.axis = cdata["axis_entry"][d]["axis"]
                        extra_sdim.stdname = cdata["axis_entry"][d]["standard_name"]
                        extra_sdim.units = cdata["axis_entry"][d]["units"]
                        extra_sdim.long_name = cdata["axis_entry"][d]["long_name"]
                        extra_sdim.out_name = cdata["axis_entry"][d]["out_name"]
                        extra_sdim.positive = cdata["axis_entry"][d]["positive"]
                        if "title" in cdata["axis_entry"][d]:
                            extra_sdim.title = cdata["axis_entry"][d]["title"]
                        else:
                            extra_sdim.title = cdata["axis_entry"][d]["long_name"]
                        string_of_requested = ""
                        for ilev in cdata["axis_entry"][d]["requested"]:
                            string_of_requested = string_of_requested + " " + ilev
                        extra_sdim.requested = string_of_requested.rstrip(" ")  # values of multi vertical levels
                        extra_sdim.value = cdata["axis_entry"][d]["value"]  # value of single vertical level
                        extra_sdim.type = cdata["axis_entry"][d]["type"]  # axis type
                    extra_var.sdims[extra_sdim.label] = extra_sdim
                    if True:
                        # print "Info: dimid corresponding to ",d,"for variable",v["out_name"],\
                        #  "in Table",table," not found in DR => read it in extra coordinates Table: ",
                        #  extra_sdim.stdname,extra_sdim.requested
                        if d not in dim_from_extra:
                            dim_from_extra[d] = OrderedDict()
                        if v['out_name'] not in dim_from_extra:
                            dim_from_extra[d][v['out_name']] = (extra_sdim.stdname, extra_sdim.requested)
            extra_var.label_without_psuffix = remove_p_suffix(extra_var, multi_plev_suffixes, single_plev_suffixes,
                                                              realms='atmos aerosol atmosChem')

            extravars.append(extra_var)
    if printout:
        print("For extra table ", table, " (which has %d variables): " % len(extravars))
        print("\tVariables which dim was found in extra coordinates table:")
        for d in sorted(list(dim_from_extra)):
            print("\t\t%20s : " % d, *sorted(dim_from_extra[d]))
            print()
        print("\tDynamical XY-xxx spatial shapes (shapes not found in DR)")
        for d in sorted(list(dynamic_shapes)):
            print("\t\t%20s : " % ("XY-" + d), *sorted(dynamic_shapes[d]))
            print()

    return extravars


def process_home_vars(mip_vars_list, mips, expid=False, printout=False):
    """
    Deal with home variables.
    """
    printmore = False
    # Read HOME variables
    homevars = get_variable_from_sset_else_lset_with_default('listof_home_vars', default=None)
    path_extra_tables = get_variable_from_sset_else_lset_with_default('path_extra_tables', default=None)
    home_vars_list = read_home_vars_list(homevars, expid, mips, path_extra_tables, printout=printout)
    for hv in home_vars_list:
        printmore = False and (hv.label == 'lwsnl')
        hv_info = {"varname": hv.label, "realm": hv.modeling_realm,
                   "freq": hv.frequency, "table": hv.mipTable}
        if printmore:
            print(hv_info)
        if hv.type == 'cmor':
            # Complement each HOME variable with attributes got from
            # the corresponding CMOR variable (if exist)
            updated_hv = get_corresp_cmor_var(hv)
            if updated_hv:
                already_in_dr = False
                for cmv in mip_vars_list:
                    matching = (cmv.label == updated_hv.label and cmv.modeling_realm == updated_hv.modeling_realm and
                                cmv.frequency == updated_hv.frequency and cmv.mipTable == updated_hv.mipTable and
                                cmv.temporal_shp == updated_hv.temporal_shp and
                                cmv.spatial_shp == updated_hv.spatial_shp)
                    if matching:
                        already_in_dr = True
                        break

                # Corresponding CMOR Variable found
                if not already_in_dr:
                    # Append HOME variable only if not already
                    # selected with the DataRequest
                    if printmore:
                        print("Info:", hv_info, "HOMEVar is not in DR. => Taken into account.")
                    mip_vars_list.append(updated_hv)
                else:
                    if printmore:
                        print("Info:", hv_info, "HOMEVar is already in DR. => Not taken into account.")
            else:
                if printout or printmore:
                    print("Error:", hv_info, "HOMEVar announced as cmor but no corresponding CMORVar found "
                                             "=> Not taken into account.")
                    raise VarsError("Abort: HOMEVar %s is declared as cmor but no corresponding CMORVar found."
                                    % repr(hv_info))
        elif hv.type == 'perso':
            # Check if HOME variable anounced as 'perso' is in fact 'cmor'
            is_cmor = get_corresp_cmor_var(hv)
            if not is_cmor:
                # Check if HOME variable differs from CMOR one only by shapes
                has_cmor_varname = any([cmvar.label == hv.label for
                                        cmvar in get_collection('CMORvar').items])
                # has_cmor_varname=any(get_cmor_var_id_by_label(hv.label))
                if has_cmor_varname:
                    if printout:
                        print("Warning:", hv_info,
                              "HOMEVar is anounced  as perso, is not a CMORVar, but has a cmor name. "
                              "=> Not taken into account.")
                    raise VarsError("Abort: HOMEVar is anounced as perso, is not a CMORVar, but has a cmor name.")
                else:
                    if printmore:
                        print("Info:", hv_info, "HOMEVar is purely personnal. => Taken into account.")
                    mip_vars_list.append(hv)
            else:
                if printout:
                    print("Error:", hv_info,
                          "HOMEVar is anounced as perso, but in reality is cmor => Not taken into account.")
                raise VarsError("Abort: HOMEVar is anounced as perso but should be cmor.")
        elif hv.type == 'dev':
            # Check if HOME variable anounced as 'dev' is in fact 'cmor'
            is_cmor = get_corresp_cmor_var(hv)
            if not is_cmor:
                # Check if HOME variable differs from CMOR one only by shapes
                has_cmor_varname = any([cmvar.label == hv.label for
                                        cmvar in get_collection('CMORvar').items])
                # has_cmor_varname=any(get_cmor_var_id_by_label(hv.label))
                if has_cmor_varname:
                    if printout:
                        print("Warning:", hv_info, "HOMEVar is anounced  as dev, is not a CMORVar, but has a cmor name."
                                                   " => Not taken into account.")
                    raise VarsError("Abort: HOMEVar is anounced as dev, is not a CMORVar, but has a cmor name.")
                else:
                    if printmore:
                        print("Info:", hv_info, "HOMEVar is purely dev. => Taken into account.")
                    mip_vars_list.append(hv)
            else:
                if printout:
                    print("Error:", hv_info,
                          "HOMEVar is anounced as dev, but in reality is cmor => Not taken into account.")
                raise VarsError("Abort: HOMEVar is anounced as dev but should be cmor.")
        elif hv.type == 'extra':
            if hv.Priority <= get_variable_from_lset_without_default("max_priority"):
                if printmore:
                    print("Info:", hv_info, "HOMEVar is read in an extra Table with priority ", hv.Priority,
                          " => Taken into account.")
                mip_vars_list.append(hv)
        else:
            if printout:
                print("Error:", hv_info, "HOMEVar type", hv.type,
                      "does not correspond to any known keyword. => Not taken into account.")
            raise VarsError("Abort: unknown type keyword provided for HOMEVar %s:" % repr(hv_info))


def get_corresp_cmor_var(hmvar):
    """
    For a home variable, find the CMOR var which corresponds.
    """
    printout = False and ("lwsnl" in hmvar.label)
    count = 0
    empty_table = (hmvar.mipTable == 'NONE') or (hmvar.mipTable[0:4] == 'None')
    for cmvarid in get_cmor_var_id_by_label(hmvar.label):
        cmvar = get_uid(cmvarid)
        if printout:
            print("get_corresp, checking %s vs %s in %s" % (hmvar.label, cmvar.label, cmvar.mipTable))
        #
        # Consider case where no modeling_realm associated to the
        # current CMORvar as matching anyway.
        # mpmoine_TBD: A mieux gerer avec les orphan_variables ?
        match_label = (cmvar.label == hmvar.label)
        match_freq = (cmvar.frequency == hmvar.frequency) or \
                     ("SoilPools" in hmvar.label and hmvar.frequency == "mon" and cmvar.frequency == "monPt")
        match_table = (cmvar.mipTable == hmvar.mipTable)
        match_realm = (hmvar.modeling_realm in cmvar.modeling_realm.split(' ')) or \
                      (hmvar.modeling_realm == cmvar.modeling_realm)
        empty_realm = (cmvar.modeling_realm == '')

        matching = (match_label and (match_freq or empty_table) and (match_table or empty_table) and
                    (match_realm or empty_realm))
        if matching:
            if printout:
                print("matches")
            same_shapes = (get_spatial_and_temporal_shapes(cmvar) == [hmvar.spatial_shp, hmvar.temporal_shp])
            if same_shapes:
                count += 1
                cmvar_found = cmvar
                if printout:
                    print("and same shapes !")
            else:
                if not empty_table:
                    print("Error: ", [hmvar.label, hmvar.mipTable],
                          "HOMEVar: Spatial and Temporal Shapes specified DO NOT match CMORvar ones. -> Provided:",
                          [hmvar.spatial_shp, hmvar.temporal_shp], 'Expected:', get_spatial_and_temporal_shapes(cmvar))
        else:
            if printout:
                print("doesn't match", match_label, match_freq, cmvar.frequency, hmvar.frequency,
                      match_table, match_realm, empty_realm, hmvar.mipTable)

    if count >= 1:
        # empty table means that the frequency is changed (but the variable exists in another frequency cmor table
        if empty_table:
            var_freq_asked = hmvar.frequency
        allow_pseudo = get_variable_from_lset_with_default('allow_pseudo_standard_names', False)
        global sn_issues_home
        sn_issues_home = complement_svar_using_cmorvar(hmvar, cmvar_found, sn_issues_home, [], allow_pseudo)
        if empty_table:
            hmvar.frequency = var_freq_asked
            hmvar.mipTable = "None" + hmvar.frequency
        return hmvar
    return False


def complement_svar_using_cmorvar(svar, cmvar, sn_issues, debug=[], allow_pseudo=False):
    """
    SVAR will have an attribute label_non_ambiguous suffixed by an
    area name if the MIPvarname is ambiguous for that

    Used by get_corresp_cmor_var and by select_cmor_vars_for_lab

    """
    global ambiguous_mipvarnames
    if ambiguous_mipvarnames is None:
        ambiguous_mipvarnames = analyze_ambiguous_mip_varnames()

    # Get information form CMORvar
    svar.prec = cmvar.type  # integer / float / double
    svar.frequency = cmvar.frequency.rstrip(' ')
    # Fix for emulating DR01.00.22 from content of DR01.00.21
    if "SoilPools" in cmvar.label:
        svar.frequency = "mon"
    svar.mipTable = cmvar.mipTable.rstrip(' ')
    svar.Priority = cmvar.defaultPriority
    svar.positive = cmvar.positive.rstrip(' ')
    svar.modeling_realm = cmvar.modeling_realm.rstrip(' ')
    if svar.modeling_realm[0:3] == "zoo":
        svar.modeling_realm = "ocnBgChem"  # Because wrong in DR01.00.20
    svar.label = cmvar.label.rstrip(' ')
    [svar.spatial_shp, svar.temporal_shp] = get_spatial_and_temporal_shapes(cmvar)
    svar.cmvar = cmvar

    # Get information from MIPvar
    mipvar = get_uid(cmvar.vid)
    svar.mipVarLabel = mipvar.label.rstrip(' ')
    svar.long_name = cmvar.title.rstrip(' ')
    if cmvar.description:
        svar.description = cmvar.description.rstrip(' ')
    else:
        svar.description = cmvar.title
    svar.units = mipvar.units.rstrip(' ')  # In case no unit is found with stdname
    #
    # see https://github.com/cmip6dr/CMIP6_DataRequest_VariableDefinitions/issues/279
    svar.stdname = ''
    sn = get_uid(mipvar.sn)  # None
    if sn._h.label == 'standardname':
        svar.stdname = sn.uid.strip()
        # svar.units = sn.units
    else:
        if allow_pseudo:
            svar.stdname = sn.uid.strip()
        if sn_issues is not None:
            if svar.stdname not in sn_issues:
                sn_issues[svar.label] = set()
            sn_issues[svar.label].add(svar.mipTable)
    if svar.label == "sitimefrac":
        svar.stdname = "sea_ice_time_fraction"  # For PrePARE missing in DR01.00.21!
    #
    # Get information form Structure
    st = None
    try:
        st = get_uid(cmvar.stid)
    except:
        if print_DR_errors:
            print("DR Error: issue with stid for", svar.label, "in Table ", svar.mipTable,
                  "  => no cell_methods, cell_measures, dimids and sdims derived.")
    if st is not None:
        svar.struct = st
        try:
            svar.cm = get_uid(st.cmid).cell_methods
            methods = get_uid(st.cmid).cell_methods.rstrip(' ')
            methods = methods.replace("mask=siconc or siconca", "mask=siconc")
            # Fix for emulating DR01.00.22 from content of DR01.00.21
            if "SoilPools" in svar.label:
                methods = "area: mean where land time: mean"
            svar.cell_methods = methods
        except:
            if print_DR_errors:
                print("DR Error: issue with cell_method for " + st.label)
            # TBS# svar.cell_methods=None
        try:
            svar.cell_measures = get_uid(cmvar.stid).cell_measures.rstrip(' ')
        except:
            if print_DR_errors:
                print("DR Error: Issue with cell_measures for " + repr(cmvar))

        # A number of DR values indicate a choice or a directive for attribute cell_measures (--OPT, --MODEL ...)
        # See interpretation guidelines at https://www.earthsystemcog.org/projects/wip/drq_interp_cell_center
        if svar.cell_measures == '--MODEL':
            svar.cell_measures = ''
        elif svar.cell_measures == '--OPT':
            svar.cell_measures = ''

        # TBD Next sequences are adhoc for errors DR 01.00.21
        if svar.label in ['tauuo', 'tauvo']:
            svar.cell_measures = 'area: areacello'
        elif svar.cell_measures == 'area: areacella' and \
                svar.label in ['tos', 't20d', 'thetaot700', 'thetaot2000', 'thetaot300', 'mlotst']:
            svar.cell_measures = 'area: areacello'

        # TBD : this cell_measure choice for seaice variables is specific to Nemo
        if "seaIce" in svar.modeling_realm and "areacella" in svar.cell_measures:
            if svar.label == 'siconca':
                svar.cell_measures = 'area: areacella'
            else:
                svar.cell_measures = 'area: areacello'
        #
        product_of_other_dims = 1
        all_dimids = []
        if svar.spatial_shp != "na-na":
            spid = get_uid(svar.struct.spid)
            all_dimids += spid.dimids
        if 'cids' in svar.struct.__dict__:
            cids = svar.struct.cids
            # when cids not empty, cids=('dim:p850',) or ('dim:typec4pft', 'dim:typenatgr') for e.g.;
            # when empty , cids=('',).
            if cids[0] != '':  # this line is needed prior to version 01.00.08.
                all_dimids += cids
            # if (svar.label=="rv850") : print "rv850 has cids %s"%cids
        if 'dids' in svar.struct.__dict__:
            dids = svar.struct.dids
            if dids[0] != '':
                all_dimids += dids
        for dimid in all_dimids:
            sdim, dimsize = get_simple_dim_from_dim_id(dimid)
            if dimsize > 1:
                # print "for var % 15s and dim % 15s, size=%3d"%(svar.label,dimid,dimsize)
                pass
            product_of_other_dims *= dimsize
            svar.sdims[sdim.label] = sdim
        if product_of_other_dims > 1:
            # print 'for % 20s'%svar.label,' product_of_other_dims=',product_of_other_dims
            svar.other_dims_size = product_of_other_dims
    area = cellmethod2area(svar.cell_methods)
    if svar.label in debug:
        print("complement_svar ... processing %s, area=%s" % (svar.label, str(area)))
    if area:
        ambiguous = any([svar.label == alabel and svar.modeling_realm == arealm
                         for (alabel, (arealm, lmethod)) in ambiguous_mipvarnames])
        if svar.label in debug:
            print("complement_svar ... processing %s, ambiguous=%s" % (svar.label, repr(ambiguous)))
        if ambiguous:
            # Special case for a set of land variables
            if not (svar.modeling_realm == 'land' and svar.label[0] == 'c'):
                svar.label_non_ambiguous = svar.label + "_" + area
    if svar.label in debug:
        print("complement_svar ... processing %s, label_non_ambiguous=%s" % (svar.label, svar.label_non_ambiguous))
    # removing pressure suffix must occur after resolving ambiguities (add of area suffix)
    # because this 2 processes cannot be cummulate at this stage.
    # this is acceptable since none of the variables requeted on pressure levels have ambiguous names.
    svar.label_without_psuffix = remove_p_suffix(svar, multi_plev_suffixes, single_plev_suffixes,
                                                 realms='atmos aerosol atmosChem')
    #
    # Fix type and mip_era
    svar.type = 'cmor'
    # mip_era='CMIP6' dans le cas CMORvar
    svar.mip_era = 'CMIP6'
    #
    return sn_issues


def get_simple_dim_from_dim_id(dimid):
    """
    Build a simple_Dim object which characteristics fit with dimid.
    """
    sdim = SimpleDim()
    d = get_uid(dimid)
    sdim.label = d.label
    sdim.positive = d.positive
    sdim.requested = d.requested
    #
    if d.requested and len(d.requested) > 0:
        dimsize = max(len(d.requested.split(" ")), 1)
    elif sdim.label == 'misrBands':
        dimsize = 16  # because value is unset in DR01.00.18
        # print 'got one case with misrbands',d
    else:
        dimsize = 1
    #
    sdim.value = d.value
    try:
        sdim.stdname = get_uid(d.standardName).uid
    except:
        if print_DR_stdname_errors:
            print("Issue with standardname for dimid %s" % dimid)
        sdim.stdname = ""
    sdim.long_name = d.title
    sdim.out_name = d.altLabel
    sdim.units = d.units
    sdim.bounds = d.bounds
    sdim.boundsValues = d.boundsValues
    sdim.axis = d.axis
    sdim.coords = d.coords
    sdim.title = d.title
    sdim.type = d.type
    return sdim, dimsize


def remove_p_suffix(svar, mlev_sfxs, slev_sfxs, realms):
    """
    Remove suffixes only if both suffix of svar.label *and* suffix of one of the svar.dims.label
    match the search suffix to avoid truncation of variable names like 'ch4' requested on 'plev19',
    where '4' does not stand for a plev set
    """
    r = re.compile("([a-zA-Z]+)([0-9]+)")
    #
    # mpmoine_correction:write_xios_file_def_for_svar:remove_p_suffix:
    # suppression des terminaisons en "Clim" le cas echant
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


def get_simplevar(label, table, freq=None):
    """
    Returns 'simplified variable' for a given CMORvar label and table
    """
    svar = SimpleCMORVar()
    psvar = get_cmor_var(label, table)
    #
    # Try to get a var for 'ps' when table is only in Home DR
    if psvar is None and label == "ps" and freq is not None:
        # print "\tSearching for alternate ps "
        if freq in ["3h", "3hr", "3hrPt"]:
            psvar = get_cmor_var('ps', 'E3hrPt')
        elif freq in ["6h", "6hr"]:
            psvar = get_cmor_var('ps', '6hrLev')
        elif freq in ["day"]:
            psvar = get_cmor_var('ps', 'CFday')
        elif freq in ["mon", "1mo"]:
            psvar = get_cmor_var('ps', 'Emon')
        elif freq in ["subhr"]:
            if table == "CFsubhr":
                psvar = get_cmor_var('ps', 'CFsubhr')
            else:
                psvar = get_cmor_var('ps', 'Esubhr')
    if psvar:
        complement_svar_using_cmorvar(svar, psvar, None, [], False)
        return svar


# def hasCMORVarName(hmvar):
#    for cmvar in get_collection('CMORvar').items:
#        if (cmvar.label==hmvar.label): return True
