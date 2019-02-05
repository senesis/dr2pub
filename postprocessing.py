#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Postprocessing functions
"""
import re
import xml.etree.ElementTree as ET


from Xparse import id2grid
from config import get_config_variable
from settings_interface import get_variable_from_lset_without_default, get_variable_from_lset_with_default
from grids import isVertDim, create_axis_def, create_grid_def, change_domain_in_grid
from analyzer import Cmip6Freq2XiosFreq
from utils import dr2xml_error


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
    vdims = [sd for sd in sv.sdims.values() if isVertDim(sd)]
    if len(vdims) == 1:
        sd = vdims[0]
    elif len(vdims) > 1:
        raise dr2xml_error("Too many vertical dims for %s (%s)" % (sv.label, `vdims`))
    if len(vdims) == 0:
        # Analyze if there is a singleton vertical dimension for the variable
        # sd=scalar_vertical_dimension(sv)
        # if sd is not None :
        #    print "Single level %s for %s"%(sv,sv.label),vdims
        # else:
        raise dr2xml_error(
            "Not enough vertical dims for %s (%s)" % (sv.label, [(s.label, s.out_name) for s in sv.sdims.values()]))
    #
    #
    # sd=vdims[0]
    alias_with_levels = alias + "_" + sd.label  # e.g. 'CMIP6_hus7h_plev7h'
    if alias_with_levels in pingvars:
        print "No vertical interpolation for %s because the pingfile provides it" % alias_with_levels
        return src_grid_id, alias_with_levels
        # raise dr2xml_error("Finding an alias with levels (%s) in pingfile is unexpected")
    #
    prefix = get_variable_from_lset_without_default("ping_variables_prefix")
    lwps = sv.label_without_psuffix
    alias_in_ping = prefix + lwps  # e.g. 'CMIP6_hus' and not 'CMIP6_hus7h'; 'CMIP6_co2' and not 'CMIP6_co2Clim'
    if alias_in_ping not in pingvars:  # e.g. alias_in_ping='CMIP6_hus'
        raise dr2xml_error("Field id " + alias_in_ping + " expected in pingfile but not found.")
    #
    # Create field alias_for_sampling for enforcing the operation before time sampling
    operation = get_variable_from_lset_with_default("vertical_interpolation_operation", "instant")
    alias_for_sampling = alias_in_ping + "_with_" + operation
    # <field id="CMIP6_hus_instant" field_ref="CMIP6_hus" operation="instant" />
    field_defs[alias_for_sampling] = \
        '<field id="%-25s field_ref="%-25s operation="%s" />' \
        % (alias_for_sampling + '"', alias_in_ping + '"', operation)
    #
    vert_freq = get_variable_from_lset_without_default("vertical_interpolation_sample_freq")
    #
    # Construct an axis for interpolating to this vertical dimension
    # e.g. for zoom_case :
    #    <axis id="zoom_plev7h_hus" axis_ref="union_plevs_hus"> <zoom_axis index="(0,6)[  3 6 11 13 15 20 28 ]"/>
    create_axis_def(sd, axis_defs, field_defs)

    # Create field 'alias_sample' which time-samples the field at required freq
    # before vertical interpolation
    alias_sample = alias_in_ping + "_sampled_" + vert_freq  # e.g.  CMIP6_zg_sampled_3h
    # <field id="CMIP6_hus_sampled_3h" field_ref="CMIP6_hus_instant" freq_op="3h" expr="@CMIP6_hus_instant"/>
    field_defs[alias_sample] = \
        '<field id="%-25s field_ref="%-25s freq_op="%-10s detect_missing_value="true" > @%s </field>' \
        % (alias_sample + '"', alias_for_sampling + '"', vert_freq + '"', alias_for_sampling)

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
        field_defs[union_alias] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                  % (union_alias + '"', alias_sample + '"', grid_id + '"')

        # SS : first create grid for levels subset zoom, e.g.:
        # <grid id="FULL_klev_zoom_plev7h_hus"> <domain domain_ref="FULL" /> <axis axis_ref="zoom_plev7h_hus" /
        # e.g. zoom_label : 'zoom_plev7h_hus'
        grid_id = create_grid_def(grid_defs, axis_defs[sd.zoom_label], sd.out_name, src_grid_id)
        # SS: e.g.: <field id="CMIP6_hus7h_plev7h" field_ref="CMIP6_hus_union" grid_ref="FULL_klev_zoom_plev7h_hus"
        field_defs[alias_with_levels] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                        % (alias_with_levels + '"', union_alias + '"', grid_id + '"')

    else:  # cas d'une variable definie grace a seul axis_def (non union+zoom)
        # Construct a grid using variable's grid and target vertical axis
        union_alias = False
        axis_key = sd.label  # e.g. 'plev7h'
        grid_id = create_grid_def(grid_defs, axis_defs[axis_key], sd.out_name, src_grid_id)
        field_defs[alias_with_levels] = '<field id="%-25s field_ref="%-25s grid_ref="%-10s/>' \
                                        % (alias_with_levels + '"', alias_sample + '"', grid_id + '"')
        # if "hus" in alias :
        #    print "--->",alias, alias_with_levels,sd
        #    print "field_def=",field_defs[alias_with_levels]

    #
    return grid_id, alias_with_levels


def process_zonal_mean(field_id, grid_id, target_hgrid_id, zgrid_id, field_defs, axis_defs, grid_defs, domain_defs,
                       operation, frequency, printout=False):
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
    printout = False
    global nlonz

    # e.g. <field id="CMIP6_ua_plev39_average" field_ref="CMIP6_ua_plev39" operation="average" />
    xios_freq = Cmip6Freq2XiosFreq(frequency, None)
    field1_id = field_id + "_" + operation  # e.g. CMIP6_hus_plev7h_instant
    field_defs[field1_id] = '<field id="%-s field_ref="%-s operation="%s />' \
                            % (field1_id + '"', field_id + '"', operation + '"')
    if printout:
        print "+++ field1 ", field1_id, "\n", field_defs[field1_id]
    #
    # e.g. <field id="CMIP6_ua_plev39_average_1d" field_ref="CMIP6_ua_plev39_average" freq_op="1d" >
    #              @CMIP6_ua_plev39_average </field>
    field2_id = field1_id + "_" + xios_freq
    field_defs[field2_id] = '<field id="%-s field_ref="%-s freq_op="%s > @%s </field>' \
                            % (field2_id + '"', field1_id + '"', xios_freq + '"', field1_id)
    if printout:
        print "+++ field2 ", field2_id, "\n", field_defs[field2_id]

    if target_hgrid_id:  # case where an intermediate grid is needed
        # e.g. <field id="CMIP6_ua_plev39_average_1d_complete" field_ref="CMIP6_ua_plev39_average_1d"
        #             grid_ref="FULL_klev_plev39_complete" />
        field3_id = field2_id + "_" + target_hgrid_id
        # Must create and a use a grid similar to the last one defined
        # for that variable, except for a change in the hgrid/domain (=> complete)
        grid_id3 = change_domain_in_grid(target_hgrid_id, grid_defs, src_grid_id=grid_id)
        if printout:
            print "+++ grid3 ", grid_id3, "\n", grid_defs[grid_id3]
        field_defs[field3_id] = '<field id="%s field_ref="%s grid_ref="%s /> ' \
                                % (field3_id + '"', field2_id + '"', grid_id3 + '"')
        if printout:
            print "+++ field3 ", field3_id, "\n", field_defs[field3_id]
    else:
        # Case where the input field is already on a rectangular grid
        print '~~~~>', "no target_hgrid_id for field=", field_id, " grid=", grid_id
        field3_id = field2_id
        grid_id3 = grid_id

    if not zgrid_id:
        raise dr2xml_error("Must provide zgrid_id in lab_settings, the id of a latitude axis which has (initialized) "
                           "latitude values equals to those of the rectangular grid used")

    # And then regrid to final grid
    # e.g. <field id="CMIP6_ua_plev39_average_1d_glat" field_ref="CMIP6_ua_plev39_average_1d_complete"
    #             grid_ref="FULL_klev_plev39_complete_glat" />
    field4_id = field2_id + "_" + zgrid_id
    grid4_id = change_domain_in_grid(zgrid_id, grid_defs, src_grid_id=grid_id3, turn_into_axis=True)
    if printout:
        print "+++ grid4 ", grid4_id, "\n", grid_defs[grid4_id]

    field_defs[field4_id] = '<field id="%s field_ref="%s grid_ref="%s /> ' \
                            % (field4_id + '"', field3_id + '"', grid4_id + '"')
    if printout:
        print "+++ field4 ", field4_id, "\n", field_defs[field4_id]

    return field4_id, grid4_id


def process_diurnal_cycle(alias, field_defs, grid_defs, axis_defs, printout=False):
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

    printout = False
    # 0- create a clone of ALIAS with operation=average
    field_for_average_id = alias + "_for_average"
    field_defs[field_for_average_id] = '<field id="%s" field_ref="%s" operation="average" />' % \
                                       (field_for_average_id, alias)
    if printout:
        print "***>", field_defs[field_for_average_id]

    # 1- create a grid composed of ALIAS's original grid extended by a scalar; id is <grid_id>_scalar_grid
    context_index = get_config_variable("context_index")
    base_grid = id2grid(alias, context_index)
    base_grid_string = ET.tostring(base_grid)
    grid_id = base_grid.attrib['id']

    grid_scalar_id = grid_id + "_plus_scalar"
    grid_scalar = re.sub(r'(.*)grid  *id *= *"[^"]*"(.*)', r'\1grid id="%s"\2' % grid_scalar_id, base_grid_string)
    grid_scalar = re.sub("(.*)</ *grid *>(.*)", r'\1<scalar /> </grid>\2', grid_scalar)
    if printout:
        print "***>", grid_scalar
    grid_defs[grid_scalar_id] = grid_scalar

    # 2- create a construct for re-gridding the field with operation average on that ,
    # first grid, and also averaging over 1h ; id is ALIAS_1h_average_scalar
    averaged_field_id = alias + "_1h_average_scalar"
    field_defs[averaged_field_id] = '<field id="%s" freq_op="1h" grid_ref="%s"> @%s </field>' % \
                                    (averaged_field_id, grid_scalar_id, field_for_average_id)
    if printout:
        print "***>", field_defs[averaged_field_id]

    # 3- create an axis of 24 values having sub-construct 'time splitting'; axis id is "24h_axis"
    axis_24h_id = "hour_in_diurnal_cycle"
    name_and_units = 'name="time3" unit="days since ?" standard_name="time"'
    axis_24h = '<axis id="%s" n_glo="24" %s value="(0,23)[ ' % (axis_24h_id, name_and_units)
    for i in range(0, 24):
        axis_24h += '%g ' % (i + 0.5)
    axis_24h += ']" >\n\t<temporal_splitting /></axis>'
    axis_defs[axis_24h_id] = axis_24h
    if printout:
        print "***>", axis_24h

    # 4- create a grid composed of ALIAS's original grid extended by that axis; id is <grid_id>_24h_grid
    grid_24h_id = grid_id + "_plus_axis24h"
    grid_24h = re.sub(r'(.*)grid  *id *= *"[^"]*"(.*)', r'\1grid id="%s"\2' % grid_24h_id, base_grid_string)
    grid_24h = re.sub("</ *grid *>", '\t<axis axis_ref="%s" %s /></grid>' % (axis_24h_id, name_and_units), grid_24h)
    grid_defs[grid_24h_id] = grid_24h
    if printout:
        print "***>", grid_24h

    # 5- create a construct for re-gridding ALIAS_SCALAR on that second grid; id is ALIAS_24hcycle, which is returned
    #        <field id="field_B"  grid_ref="grid_B" field_ref="field_As" />
    alias_24h_id = alias + "_split24h"
    alias_24h = '<field id="%s"  grid_ref="%s" field_ref="%s" />' % (alias_24h_id, grid_24h_id, averaged_field_id)
    field_defs[alias_24h_id] = alias_24h
    if printout:
        print "***>", alias_24h, "\n"

    return alias_24h_id, grid_24h_id