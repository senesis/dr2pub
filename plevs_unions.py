#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module to deal with pressure level unions management.
It is not used nor finished.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict

# Global variables and configuration tools
from config import get_config_variable

# Logger
from logger import get_logger

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_without_default

# Grids tools
from grids import create_axis_def, create_grid_def

# Variables tools
from vars_cmor import SimpleDim

# XIOS reading and writing tools
from Xparse import id2gridid


def create_xios_axis_and_grids_for_plevs_unions(svars, plev_sfxs, dummies, axis_defs, grid_defs, field_defs, ping_refs):
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
    logger = get_logger()
    prefix = get_variable_from_lset_without_default("ping_variables_prefix")
    # First, search plev unions for each label_without_psuffix and build dict_plevs
    dict_plevs = OrderedDict()
    for sv in svars:
        if not sv.modeling_realm:
            logger.warning("Warning: no modeling_realm associated to:", sv.label, sv.mipTable, sv.mip_era)
        for sd in sv.sdims.values():
            # couvre les dimensions verticales de type 'plev7h' ou 'p850'
            if sd.label.startswith("p") and any(sd.label.endswith(s) for s in plev_sfxs) and sd.label != 'pl700':
                lwps = sv.label_without_psuffix
                if lwps:
                    present_in_ping = (prefix + lwps) in ping_refs
                    dummy_in_ping = None
                    if present_in_ping:
                        dummy_in_ping = ("dummy" in ping_refs[prefix + lwps])

                    if present_in_ping and (not dummy_in_ping or dummies == 'include'):
                        sv.sdims[sd.label].is_zoom_of = "union_plevs_" + lwps
                        if lwps not in dict_plevs:
                            dict_plevs[lwps] = {sd.label: {sv.label: sv}}
                        else:
                            if sd.label not in dict_plevs[lwps]:
                                dict_plevs[lwps].update({sd.label: {sv.label: sv}})
                            else:
                                if sv.label not in dict_plevs[lwps][sd.label]:
                                    dict_plevs[lwps][sd.label].update({sv.label: sv})
                                else:
                                    # TBS# print sv.label,"in table",sv.mipTable,"already listed for",sd.label
                                    pass
                    else:
                        logger.info("Info: ", lwps, "not taken into account for building plevs union axis because ",
                                    prefix + lwps,)
                        if not present_in_ping:
                            logger.info("is not an entry in the pingfile")
                        else:
                            logger.info("has a dummy reference in the pingfile")

                    # svar will be expected on a zoom axis of the union. Corresponding vertical dim must
                    # have a zoom_label named plevXX_<lwps> (multiple pressure levels)
                    # or pXX_<lwps> (single pressure level)
                    sv.sdims[sd.label].zoom_label = 'zoom_' + sd.label + "_" + lwps
                else:
                    logger.warning("Warning: dim is pressure but label_without_psuffix=", lwps,
                                   "for", sv.label, sv.mipTable, sv.mip_era)
            # else :
            #    print "for var %s/%s, dim %s is not related to pressure"%(sv.label,sv.label_without_psuffix,sd.label)
    #
    # Second, create xios axis for union of plevs
    union_axis_defs = axis_defs
    union_grid_defs = grid_defs
    # union_axis_defs={}
    # union_grid_defs={}
    for lwps in list(dict_plevs):
        sdim_union = SimpleDim()
        plevs_union_xios = ""
        plevs_union = set()
        for plev in list(dict_plevs[lwps]):
            plev_values = []
            for sv in dict_plevs[lwps][plev].values():
                if not plev_values:
                    # svar is the first one with this plev => get its level values
                    # on reecrase les attributs de sdim_union a chaque nouveau plev. Pas utile mais
                    # c'est la facon la plus simple de faire
                    sdsv = sv.sdims[plev]
                    if sdsv.stdname:
                        sdim_union.stdname = sdsv.stdname
                    if sdsv.long_name:
                        sdim_union.long_name = sdsv.long_name
                    if sdsv.positive:
                        sdim_union.positive = sdsv.positive
                    if sdsv.out_name:
                        sdim_union.out_name = sdsv.out_name
                    if sdsv.units:
                        sdim_union.units = sdsv.units
                    if sdsv.requested:
                        # case of multi pressure levels
                        plev_values = set(sdsv.requested.split())
                        sdim_union.is_union_for.append(sv.label + "_" + sd.label)
                    elif sdsv.value:
                        # case of single pressure level
                        plev_values = set(sdsv.value.split())
                        sdim_union.is_union_for.append(sv.label + "_" + sd.label)
                    else:
                        logger.warning("Warning: No requested nor value found for", svar.label,
                                       "with vertical dimesion", plev)
                    plevs_union = plevs_union.union(plev_values)
                    logger.debug("    -- on", plev, ":", plev_values)
                logger.debug("       *", sv.label, "(", sv.mipTable, ")")
        list_plevs_union = list(plevs_union)
        list_plevs_union_num = [float(lev) for lev in list_plevs_union]
        list_plevs_union_num.sort(reverse=True)
        list_plevs_union = [str(lev) for lev in list_plevs_union_num]
        for lev in list_plevs_union:
            plevs_union_xios += " " + lev
        logger.debug(">>> XIOS plevs union:", plevs_union_xios)
        sdim_union.label = "union_plevs_" + lwps
        if len(list_plevs_union) > 1:
            sdim_union.requested = plevs_union_xios
        if len(list_plevs_union) == 1:
            sdim_union.value = plevs_union_xios
        logger.info("creating axis def for union :%s" % sdim_union.label)
        axis_def = create_axis_def(sdim_union, union_axis_defs, field_defs)
        create_grid_def(union_grid_defs, axis_def, sdim_union.out_name,
                        id2gridid(prefix + lwps, get_config_variable("context_index")))
    #
    # return (union_axis_defs,union_grid_defs)
