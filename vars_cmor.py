#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CMOR variables tools.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict

# Utilities
from utils import Dr2xmlError

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_without_default
# Interface to Data Request
from dr_interface import get_collection, get_uid, get_request_by_id_by_sect, print_DR_errors

# Settings tools
from analyzer import cellmethod2area


def get_cmor_var(label, table):
    """
    Returns CMOR variable for a given label in a given table
    (could be optimized using inverse index)
    """
    collect = get_collection('CMORvar')
    thevar = None
    for cmvar in collect.items:
        if cmvar.mipTable == table and cmvar.label == label:
            thevar = cmvar
            break
    return thevar


def get_spatial_and_temporal_shapes(cmvar):
    """
    Get the spatial et temporal shape of a CMOR variable from the DR.
    """
    spatial_shape = False
    temporal_shape = False
    if cmvar.stid == "__struct_not_found_001__":
        if print_DR_errors:
            print("Warning: stid for ", cmvar.label, " in table ", cmvar.mipTable,
                  " is a broken link to structure in DR: ", cmvar.stid)
    else:
        struct = get_uid(cmvar.stid)
        spatial_shape = get_uid(struct.spid).label
        temporal_shape = get_uid(struct.tmid).label
    if print_DR_errors:
        if not spatial_shape:
            print("Warning: spatial shape for ", cmvar.label, " in table ", cmvar.mipTable, " not found in DR.")
        if not temporal_shape:
            print("Warning: temporal shape for ", cmvar.label, " in table ", cmvar.mipTable, " not found in DR.")
    return [spatial_shape, temporal_shape]


def analyze_ambiguous_mip_varnames(debug=[]):
    """
    Return the list of MIP varnames whose list of CMORvars for a single realm
    show distinct values for the area part of the cell_methods
    """
    # Compute a dict which keys are MIP varnames and values = list
    # of CMORvars items for the varname
    d = OrderedDict()
    for v in get_collection('var').items:
        if v.label not in d:
            d[v.label] = []
            if v.label in debug:
                print("Adding %s" % v.label)
        refs = get_request_by_id_by_sect(v.uid, 'CMORvar')
        for r in refs:
            d[v.label].append(get_uid(r))
            if v.label in debug:
                print("Adding CmorVar %s(%s) for %s" % (v.label, get_uid(r).mipTable, get_uid(r).label))

    # Replace dic values by dic of area portion of cell_methods
    for vlabel in d:
        if len(d[vlabel]) > 1:
            cvl = d[vlabel]
            d[vlabel] = OrderedDict()
            for cv in cvl:
                st = get_uid(cv.stid)
                cm = None
                try:
                    cm = get_uid(st.cmid).cell_methods
                except:
                    # pass
                    print("No cell method for %-15s %s(%s)" % (st.label, cv.label, cv.mipTable))
                if cm is not None:
                    area = cellmethod2area(cm)
                    realm = cv.modeling_realm
                    if area == 'sea' and realm == 'ocean':
                        area = None
                    # realm=""
                    if vlabel in debug:
                        print("for %s 's CMORvar %s(%s), area=%s" % (vlabel, cv.label, cv.mipTable, area))
                    if realm not in d[vlabel]:
                        d[vlabel][realm] = OrderedDict()
                    if area not in d[vlabel][realm]:
                        d[vlabel][realm][area] = []
                    d[vlabel][realm][area].append(cv.mipTable)
            if vlabel in debug:
                print(vlabel, d[vlabel])
        else:
            d[vlabel] = None

    # Analyze ambiguous cases regarding area part of the cell_method
    ambiguous = []
    for vlabel in d:
        if d[vlabel]:
            # print vlabel,d[vlabel]
            for realm in d[vlabel]:
                if len(d[vlabel][realm]) > 1:
                    ambiguous.append((vlabel, (realm, d[vlabel][realm])))
    if "all" in debug:
        for v, p in ambiguous:
            print(v)
            b, d = p
            for r in d:
                print("\t", r, d[r])
    return ambiguous


def ping_alias(svar, pingvars, error_on_fail=False):
    """
    Dans le pingfile, grace a la gestion des interpolations
    verticales, on n'attend pas forcement les alias complets des
    variables (CMIP6_<label>), on peut se contenter des alias
    reduits (CMIP6_<lwps>)

    par ailleurs, si on a defini un label non ambigu alors on l'utilise
    comme ping_alias (i.e. le field_ref)
    """
    pref = get_variable_from_lset_without_default("ping_variables_prefix")
    if svar.label_non_ambiguous:
        # print "+++ non ambiguous", svar.label,svar.label_non_ambiguous
        alias_ping = pref + svar.label_non_ambiguous  # e.g. 'CMIP6_tsn_land' and not 'CMIP6_tsn'
    else:
        # print "+++ ambiguous", svar.label
        # Ping file may provide the variable on the relevant pressure level - e.g. CMIP6_rv850
        alias_ping = pref + svar.label
        if alias_ping not in pingvars:
            # if not, ping_alias is supposed to be without a pressure level suffix
            alias_ping = pref + svar.label_without_psuffix  # e.g. 'CMIP6_hus' and not 'CMIP6_hus7h'
        # print "+++ alias_ping = ", pref, svar.label_without_psuffix, alias_ping
    if alias_ping not in pingvars:
        if error_on_fail:
            raise Dr2xmlError("Cannot find an alias in ping for variable %s" % svar.label)
        else:
            return None
    return alias_ping


def analyze_priority(cmvar, lmips):
    """
    Returns the max priority of the CMOR variable, for a set of mips
    """
    prio = cmvar.defaultPriority
    rv_ids = get_request_by_id_by_sect(cmvar.uid, 'requestVar')
    for rv_id in rv_ids:
        rv = get_uid(rv_id)
        vg = get_uid(rv.vgid)
        if vg.mip in lmips:
            if rv.priority < prio:
                prio = rv.priority
    return prio


class SimpleCMORVar(object):
    """
    A class for unifying CMOR vars and home variables
    """
    def __init__(self):
        self.type = False
        self.modeling_realm = None
        self.grids = [""]
        self.label = None  # taken equal to the CMORvar label
        self.mipVarLabel = None  # taken equal to MIPvar label
        self.label_without_psuffix = None
        self.label_non_ambiguous = None
        self.frequency = None
        self.mipTable = None
        self.positive = None
        self.description = None
        self.stdname = None
        self.units = None
        self.long_name = None
        self.struct = None
        self.sdims = OrderedDict()
        self.other_dims_size = 1
        self.cell_methods = None
        self.cell_measures = None
        self.spatial_shp = None
        self.temporal_shp = None
        self.experiment = None
        self.mip = None
        self.Priority = 1  # Will be changed using DR or extra-Tables
        self.mip_era = False  # Later changed in projectname (uppercase) when appropriate
        self.prec = "float"
        self.missing = 1.e+20
        self.cmvar = None  # corresponding CMORvar, if any


class SimpleDim(object):
    """
    A class for unifying grid info coming from DR and extra_Tables
    """
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
        self.bounds = False
        self.boundsValues = False
        self.axis = False
        self.type = False
        self.coords = False
        self.title = False
        self.is_union_for = []
