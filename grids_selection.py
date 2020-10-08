#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management of output grids

Principles : the Data Request may specify which grid to use : either native or a common, regular, one.
             This specified per requestLink, which means per set of variables and experiments.

dr2xml allows for the lab to choose among various policy  :
   - DR or None : always follow DR spec
   - native     : never not follow DR spec (always use native or close-to-native grid)
   - native+DR  : always produce on the union of grids
   - adhoc      : decide on each case, based on CMORvar attributes, using a
                  lab-specific scheme implemented in a lab-provided Python
                  function which should replace function lab_adhoc_grid_policy

"""

from __future__ import print_function, division, absolute_import, unicode_literals

# Utilities
from utils import Dr2xmlError

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_with_default
# Interface to Data Request
from dr_interface import get_uid


def normalize(grid):
    """ in DR 1.0.2, values are :
    ['', 'model grid', '100km', '50km or smaller', 'cfsites', '1deg', '2deg', '25km or smaller', 'native']
    """
    if grid in ["native", "model grid", ""]:
        return ""
    return grid.replace(" or smaller", "")


def decide_for_grids(cmvarid, grids):
    """
    Decide which set of grids a given variable should be produced on

    CMVARID is uid of the CMORvar
    GRIDS is a list of strings for grid as specified in requestLink
    LSET is the laboratory settings dictionnary. It carries a policy re. grids

    Returns a list of grid strings (with some normalization) (see below)

    TBD : use Martin's acronyms for grid policy
    """
    # Normalize and remove duplicates in grids list
    ngrids = map(normalize, grids)
    sgrids = set()
    for g in ngrids:
        sgrids.add(g)
    ngrids = list(sgrids)
    #
    policy = get_variable_from_lset_with_default("grid_policy")
    if policy is None or policy == "DR":  # Follow DR spec
        return ngrids
    elif policy == "native":  # Follow lab grids choice (gr or gn depending on context - see lset['grids"])
        if ngrids == ['cfsites']:
            return ngrids
        else:
            return [""]
    elif policy == "native+DR":  # Produce both in 'native' and DR grid
        if ngrids == ['cfsites']:
            return ngrids
        else:
            sgrids.add('')
            return list(sgrids)
    elif policy == "adhoc":
        return lab_adhoc_grid_policy(cmvarid, ngrids)
    else:
        Dr2xmlError("Invalid grid policy %s" % policy)


def lab_adhoc_grid_policy(cmvarid, grids):
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
    return CNRM_grid_policy(cmvarid, grids)


def CNRM_grid_policy(cmvarid, grids):  # TBD
    """
    See doc of lab_adhoc_grid_policy
    """
    if get_uid(cmvarid).label in ["sos"]:
        return [g for g in grids if g in ["", "1deg"]]
    elif get_uid(cmvarid).label in ["tos"] and (get_uid(cmvarid).mipTable not in ["3hr"] or
                                                get_variable_from_lset_with_default("allow_tos_3hr_1deg", True)):
        if get_variable_from_lset_with_default("adhoc_policy_do_add_1deg_grid_for_tos", False):
            list_grids = list()
            if "" in grids:
                list_grids.append("")
            list_grids.append("1deg")
            return list_grids
        else:
            return [g for g in grids if g in ["", "1deg"]]
    else:
        ngrids = [g for g in grids if g not in ["1deg", "2deg", "100km", "50km"]]
        # if "cfsites" in grids : return ["","cfsites"]
        if len(ngrids) == 0:
            ngrids = [""]  # We should at least provide native grid
        return ngrids
