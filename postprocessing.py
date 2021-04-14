#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Postprocessing functions
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import re
from collections import OrderedDict

# Utilities
from utils import Dr2xmlError

# Logger
from logger import get_logger

# Global variables and configuration tools
from config import get_config_variable

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_without_default, get_variable_from_lset_with_default

# Settings tools
from analyzer import cmip6_freq_to_xios_freq

# Grids tools
from grids import is_vert_dim, create_axis_def, create_grid_def, change_domain_in_grid

# XIOS reading and writing tools
from Xparse import id2grid

# Project tools
from projects import DR2XMLField, DR2XMLScalar, DR2XMLAxis, DR2XMLTemporalSplitting


def process_vertical_interpolation(sv, alias, pingvars, src_grid_id, field_defs, axis_defs, grid_defs, domain_defs,
                                   table):
    """
    Based on vertical dimension of variable SV, creates the intermediate fields
    for triggering vertical interpolation with the required levels; also includes
    creating axes as necessary, and re-constructing a grid which combines the required
    vertical dimension and the horizontal domain of variable's original grid

    Also includes creating an intermediate field for time-sampling before vertical interpolation

    Two flavors : using or not the vertical level union scheme (and if yes, create as
    vertical axis a zoom of the union axis)
    """
    #
    logger = get_logger()
    vdims = [sd for sd in sv.sdims.values() if is_vert_dim(sd)]
    logger.debug("Check if there is a vertical dimension for %s" % sv.label)
    if len(vdims) == 1:
        sd = vdims[0]
    elif len(vdims) > 1:
        raise Dr2xmlError("Too many vertical dims for %s (%s)" % (sv.label, repr(vdims)))
    elif sv.type in ["dev", ]:
        return src_grid_id, alias
    else:
        # Analyze if there is a singleton vertical dimension for the variable
        # sd=scalar_vertical_dimension(sv)
        # if sd is not None :
        #    print "Single level %s for %s"%(sv,sv.label),vdims
        # else:
        raise Dr2xmlError(
            "Not enough vertical dims for %s (%s)" % (sv.label, [(s.label, s.out_name) for s in sv.sdims.values()]))
    logger.debug("Vertical dimension found %s for variable %s" % (sd.label, sv.label))
    #
    #
    # sd=vdims[0]
    alias_with_levels = "_".join([alias, sd.label]) # e.g. 'CMIP6_hus7h_plev7h'
    logger.debug("Alias with levels for sd is %s" % alias_with_levels)
    if alias_with_levels in pingvars:
        logger.warning("No vertical interpolation for %s because the pingfile provides it" % alias_with_levels)
        return src_grid_id, alias_with_levels
        # raise Dr2xmlError("Finding an alias with levels (%s) in pingfile is unexpected")
    #
    prefix = get_variable_from_lset_without_default("ping_variables_prefix")
    lwps = sv.label_without_psuffix
    if sv.type in ["perso", "dev"]:
        alias_in_ping = sv.label
    else:
        alias_in_ping = prefix + lwps  # e.g. 'CMIP6_hus' and not 'CMIP6_hus7h'; 'CMIP6_co2' and not 'CMIP6_co2Clim'
        if alias_in_ping not in pingvars:  # e.g. alias_in_ping='CMIP6_hus'
            raise Dr2xmlError("Field id " + alias_in_ping + " expected in pingfile but not found.")
    #
    # Create field alias_for_sampling for enforcing the operation before time sampling
    operation = get_variable_from_lset_with_default("vertical_interpolation_operation", "instant")
    alias_for_sampling = alias_in_ping + "_with_" + operation
    # <field id="CMIP6_hus_instant" field_ref="CMIP6_hus" operation="instant" />
    field_defs[alias_for_sampling] = DR2XMLField(id=alias_for_sampling, field_ref=alias_in_ping, operation=operation)
    #
    vert_freq = get_variable_from_lset_without_default("vertical_interpolation_sample_freq")
    #
    # Construct an axis for interpolating to this vertical dimension
    # e.g. for zoom_case :
    #    <axis id="zoom_plev7h_hus" axis_ref="union_plevs_hus"> <zoom_axis index="(0,6)[  3 6 11 13 15 20 28 ]"/>
    create_axis_def(sd, axis_defs, field_defs, pingvars)

    # Create field 'alias_sample' which time-samples the field at required freq
    # before vertical interpolation
    alias_sample = "_".join([alias_in_ping, "sampled", vert_freq]) # e.g.  CMIP6_zg_sampled_3h
    # <field id="CMIP6_hus_sampled_3h" field_ref="CMIP6_hus_instant" freq_op="3h" expr="@CMIP6_hus_instant"/>
    field_defs[alias_sample] = DR2XMLField(id=alias_sample, field_ref=alias_for_sampling, freq_op=vert_freq,
                                           detect_missing_value="true", text="@{}".format(alias_for_sampling))

    # Construct a field def for the vertically interpolated variable
    if sd.is_zoom_of:  # cas d'une variable definie grace a 2 axis_def (union+zoom)

        # Construct a grid using variable's grid and target vertical axis
        # e.g. <grid id="FULL_klev_zoom_plev7h_hus"> <domain domain_ref="FULL" /> <axis axis_ref="zoom_plev7h_hus" />

        # cas d'une variable definie grace a 2 axes verticaux (zoom+union)
        # Must first create grid for levels union, e.g.:
        # <grid id="FULL_klev_union_plevs_hus"> <domain domain_ref="FULL" /> <axis axis_ref="union_plevs_hus" />
        grid_id = create_grid_def(grid_defs, axis_defs[sd.is_zoom_of], sd.out_name, src_grid_id)
        #
        union_alias = prefix + lwps + "_union"  # e.g. 'CMIP6_hus_union'
        # Ss e.g.: <field id="CMIP6_hus_union" field_ref="CMIP6_hus_sampled_3h" grid_ref="FULL_klev_union_plevs_hus"/>
        field_defs[union_alias] = DR2XMLField(id=union_alias, field_ref=alias_sample, grid_ref=grid_id)

        # SS : first create grid for levels subset zoom, e.g.:
        # <grid id="FULL_klev_zoom_plev7h_hus"> <domain domain_ref="FULL" /> <axis axis_ref="zoom_plev7h_hus" /
        # e.g. zoom_label : 'zoom_plev7h_hus'
        grid_id = create_grid_def(grid_defs, axis_defs[sd.zoom_label], sd.out_name, src_grid_id)
        # SS: e.g.: <field id="CMIP6_hus7h_plev7h" field_ref="CMIP6_hus_union" grid_ref="FULL_klev_zoom_plev7h_hus"
        field_defs[alias_with_levels] = DR2XMLField(id=alias_with_levels, field_ref=union_alias, grid_ref=grid_id)

    else:  # cas d'une variable definie grace a seul axis_def (non union+zoom)
        # Construct a grid using variable's grid and target vertical axis
        union_alias = False
        axis_key = sd.label  # e.g. 'plev7h'
        grid_id = create_grid_def(grid_defs, axis_defs[axis_key], sd.out_name, src_grid_id)
        field_defs[alias_with_levels] = DR2XMLField(id=alias_with_levels, field_ref=alias_sample, grid_ref=grid_id)
        # if "hus" in alias :
        #    print "--->",alias, alias_with_levels,sd
        #    print "field_def=",field_defs[alias_with_levels]

    #
    return grid_id, alias_with_levels


def process_zonal_mean(field_id, grid_id, target_hgrid_id, zgrid_id, field_defs, axis_defs, grid_defs, domain_defs,
                       operation, frequency):
    """
    Based on a field FIELD_ID defined on some grid GRID_ID, build all XIOS constructs
    needed to derive the zonal mean of the field, by chaining the definition of
    successive derived fields:
    field1 which sets the relevant 'operation' on input field
    field2 which applies the time operation
    field3 which applies a regriding to an intermediate horizontal grid  TARGET_HGRID_ID
    field4 which regrids to the relevant zonal grid ZGRID_ID

    Returns field_id and  grid_id for the 4th, final, field
    Intermediate constructs are stored in dics field_defs, grid_defs, axis_defs

    For fields 1 and 2, we adopt the same naming conventions than when
    the same operations are done outside the zonal grid context; this
    is for optimzation when both contexts occur

    """
    logger = get_logger()

    # e.g. <field id="CMIP6_ua_plev39_average" field_ref="CMIP6_ua_plev39" operation="average" />
    xios_freq = cmip6_freq_to_xios_freq(frequency, None)
    field1_id = "_".join([field_id, operation])  # e.g. CMIP6_hus_plev7h_instant
    field_defs[field1_id] = DR2XMLField(id=field1_id, field_ref=field_id, operation=operation)
    logger.debug("+++ field1 %s\n%s" % (field1_id, field_defs[field1_id]))
    #
    # e.g. <field id="CMIP6_ua_plev39_average_1d" field_ref="CMIP6_ua_plev39_average" freq_op="1d" >
    #              @CMIP6_ua_plev39_average </field>
    field2_id = "_".join([field1_id, xios_freq])
    field_defs[field2_id] = DR2XMLField(id=field2_id, field_ref=field1_id, freq_op=xios_freq)
    logger.debug("+++ field2 %s\n%s" % (field2_id, field_defs[field2_id]))

    if target_hgrid_id:  # case where an intermediate grid is needed
        # e.g. <field id="CMIP6_ua_plev39_average_1d_complete" field_ref="CMIP6_ua_plev39_average_1d"
        #             grid_ref="FULL_klev_plev39_complete" />
        field3_id = "_".join([field2_id, target_hgrid_id])
        # Must create and a use a grid similar to the last one defined
        # for that variable, except for a change in the hgrid/domain (=> complete)
        grid_id3 = change_domain_in_grid(target_hgrid_id, grid_defs, src_grid_id=grid_id)
        logger.debug("+++ grid3 %s\n%s" % (grid_id3, grid_defs[grid_id3]))
        field_defs[field3_id] = DR2XMLField(id=field3_id, field_ref=field2_id, grid_ref=grid_id3)
        logger.debug("+++ field3 %s\n%s" % (field3_id, field_defs[field3_id]))
    else:
        # Case where the input field is already on a rectangular grid
        logger.info("~~~~> no target_hgrid_id for field=%s grid=%s" % (field_id, grid_id))
        field3_id = field2_id
        grid_id3 = grid_id

    if not zgrid_id:
        raise Dr2xmlError("Must provide zgrid_id in lab_settings, the id of a latitude axis which has (initialized) "
                           "latitude values equals to those of the rectangular grid used")

    # And then regrid to final grid
    # e.g. <field id="CMIP6_ua_plev39_average_1d_glat" field_ref="CMIP6_ua_plev39_average_1d_complete"
    #             grid_ref="FULL_klev_plev39_complete_glat" />
    field4_id = "_".join([field2_id, zgrid_id])
    grid4_id = change_domain_in_grid(zgrid_id, grid_defs, src_grid_id=grid_id3, turn_into_axis=True)
    logger.debug("+++ grid4 %s\n%s" % (grid4_id, grid_defs[grid4_id]))

    field_defs[field4_id] = DR2XMLField(id=field4_id, field_ref=field3_id, grid_ref=grid4_id)
    logger.debug("+++ field4 %s\n%s" % (field4_id, field_defs[field4_id]))

    return field4_id, grid4_id


def process_diurnal_cycle(alias, field_defs, grid_defs, axis_defs):
    """
    Based on a field id ALIAS, and gobal CONTEXT_INDEX, creates and
    stores Xios xml constructs for defining a derived variable which
    is the diurnal cycle of ALIAS

    All objects are stored in the corresponding dict (grid_defs, field_defs, axis_defs)

    Returns the field id for the derived variable, and its grid_id

    Steps :
    0- create a construct for averaging ALIAS on 1h periods
    1- create a grid composed of ALIAS's original grid extended by a scalar;
    2- create a construct for re-gridding 1h-averaged ALIAS on that first grid;
    3- create an axis of 24 values having sub-construct 'time splitting';
    4- create a grid composed of ALIAS's original grid extended by that axis;
    5- create a construct for re-gridding ALIAS_SCALAR on that second grid; and returns it id


    """
    logger = get_logger()
    # 0- create a clone of ALIAS with operation=average
    field_for_average_id = alias + "_for_average"
    field_defs[field_for_average_id] = DR2XMLField(id=field_for_average_id, field_ref=alias, operation="average")

    logger.debug("***> %s" % field_defs[field_for_average_id])

    # 1- create a grid composed of ALIAS's original grid extended by a scalar; id is <grid_id>_scalar_grid
    context_index = get_config_variable("context_index")
    base_grid = id2grid(alias, context_index)
    grid_scalar = base_grid.copy()
    grid_id = base_grid.attrib['id']

    grid_scalar_id = grid_id + "_plus_scalar"
    grid_scalar.attrib["id"] = grid_scalar_id
    grid_scalar.append(DR2XMLScalar())
    logger.debug("***> %s" % grid_scalar)
    grid_defs[grid_scalar_id] = grid_scalar

    # 2- create a construct for re-gridding the field with operation average on that ,
    # first grid, and also averaging over 1h ; id is ALIAS_1h_average_scalar
    averaged_field_id = alias + "_1h_average_scalar"
    field_defs[averaged_field_id] = DR2XMLField(id=averaged_field_id, freq_op="1h", grid_ref=grid_scalar_id,
                                                text="@{}".format(field_for_average_id))
    logger.debug("***> %s" % field_defs[averaged_field_id])

    # 3- create an axis of 24 values having sub-construct 'time splitting'; axis id is "24h_axis"
    axis_24h_id = "hour_in_diurnal_cycle"
    axis_24h = DR2XMLAxis(id=axis_24h_id, n_glo="24", name="time3", unit="days since ?", standard_name="time",
                          value="(0,23)[{}]".format(" ".join([str(i + 0.5) for i in range(0,24)])), axis_type="T")
    axis_24h.append(DR2XMLTemporalSplitting())
    axis_defs[axis_24h_id] = axis_24h
    logger.debug("***> %s" % axis_24h)

    # 4- create a grid composed of ALIAS's original grid extended by that axis; id is <grid_id>_24h_grid
    grid_24h_id = grid_id + "_plus_axis24h"
    grid_24h = base_grid.copy()
    grid_24h.attrib["id"] = grid_24h_id
    grid_24h.append(DR2XMLAxis(axis_ref=axis_24h_id, name="time3", unit="days since ?", standard_name="time",
                               axis_type="T"))
    grid_defs[grid_24h_id] = grid_24h
    logger.debug("***> %s" % grid_24h)

    # 5- create a construct for re-gridding ALIAS_SCALAR on that second grid; id is ALIAS_24hcycle, which is returned
    #        <field id="field_B"  grid_ref="grid_B" field_ref="field_As" />
    alias_24h_id = alias + "_split24h"
    alias_24h = DR2XMLField(id=alias_24h_id, grid_ref=grid_24h_id, field_ref=averaged_field_id)
    field_defs[alias_24h_id] = alias_24h
    logger.debug("***> %s\n" % alias_24h)

    return alias_24h_id, grid_24h_id


def process_levels_over_orog(sv, alias, pingvars, src_grid_id, field_defs, axis_defs, grid_defs, domain_defs,
                             scalar_defs, table):
    logger = get_logger()
    vdims = [sd for sd in sv.sdims.values() if is_vert_dim(sd)]
    if len(vdims) == 1:
        sd = vdims[0]
    elif len(vdims) > 1:
        raise Dr2xmlError("Too many vertical dims for %s (%s)" % (sv.label, repr(vdims)))
    if len(vdims) == 0:
        # Analyze if there is a singleton vertical dimension for the variable
        # sd=scalar_vertical_dimension(sv)
        # if sd is not None :
        #    print "Single level %s for %s"%(sv,sv.label),vdims
        # else:
        raise Dr2xmlError(
            "Not enough vertical dims for %s (%s)" % (sv.label, [(s.label, s.out_name) for s in sv.sdims.values()]))

    field_id = "_".join([alias, sd.label])
    if field_id in pingvars:
        logger.warning("No computing on height level other the ground needed, found %s in pingvars." % field_id)
        grid_id = src_grid_id
    else:
        context_index = get_config_variable("context_index")
        if "height_over_orog" not in context_index:
            raise KeyError("height_over_orog must have been define in field_def")
        alias_in_ping = get_variable_from_lset_without_default("ping_variables_prefix") + sv.label_without_psuffix
        if alias_in_ping not in pingvars:  # e.g. alias_in_ping='CMIP6_hus'
            raise Dr2xmlError("Field id " + alias_in_ping + " expected in pingfile but not found.")
        if sd.requested:
            glo_list = sd.requested.strip(" ").split()
        else:
            glo_list = sd.value.strip(" ").split()
        glo_list_num = [float(v) for v in glo_list]
        glo_list_num.sort(reverse=True)
        n_glo = len(glo_list)
        axis_id = "_".join([sd.out_name, "hglev%s" % "-".join(sd.values)])
        if n_glo > 1:
            # Case of a non-degenerated vertical dimension (not a singleton)
            value = "(0,{})[ {} ]".format(n_glo - 1, sd.requested)
        else:
            if n_glo != 1:
                print("Warning: axis for %s is singleton but has %d values" % (sd.label, n_glo))
                return None
            # Singleton case (degenerated vertical dimension)
            value = '(0,0)[ {} ]'.format(sd.value)
        axis = DR2XMLAxis(id=axis_id, axis_ref="height_over_orog", n_glo=str(n_glo), value=value)
        axis_defs[axis_id] = axis

        grid_id = create_grid_def(grid_defs, axis_defs[axis_id], sd.out_name, src_grid_id)

        field = DR2XMLField(id=field_id, field_ref=alias_in_ping, grid_ref=grid_id)
        field_defs[field_id] = field
    return field_id, grid_id
