#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grids general tools.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from functools import reduce
from collections import OrderedDict

import re

# Utilities
from utils import Dr2xmlError

# Logger
from logger import get_logger

# Global variables and configuration tools
from config import get_config_variable

# Interface to settings dictionaries
from settings_interface import get_variable_from_lset_without_default, get_variable_from_lset_with_default, \
    is_key_in_lset
# Interface to Data Request
from dr_interface import get_collection, get_uid
# Interface to xml tools
from xml_interface import remove_subelement_in_xml_element

# CFsites tools
from cfsites import cfsites_grid_id, add_cfsites_in_defs, cfsites_domain_id

# Project tools
from projects import DR2XMLGrid, DR2XMLDomain, DR2XMLAxis, DR2XMLField, DR2XMLInterpolateAxis, DR2XMLZoomAxis, \
    DR2XMLGenerateRectilinearDomain, DR2XMLInterpolateDomain, DR2XMLScalar


# Next variable is used to circumvent an Xios 1270 shortcoming. Xios
# should read that value in the datafile. Actually, it did, in some
# earlier version ...
axis_count = 0


def get_grid_def(grid_id, grid_defs):
    """
    Get the grid definition corresponding to grid_id from the context_index or the list of grid definitions.
    """
    context_index = get_config_variable("context_index")
    if grid_id in grid_defs:
        # Simple case : already stored
        grid_def = grid_defs[grid_id]
    else:
        if grid_id in context_index:
            # Grid defined through xml
            grid_def = context_index[grid_id]
        else:
            raise Dr2xmlError("Cannot guess a grid def for %s" % grid_id)
    return grid_def


def guess_simple_domain_grid_def(grid_id):
    """
    dr2xml sometimes must be able to reconstruct the grid def for a grid which has
    just a domain, from the grid_id, using a regexp with a numbered group that matches
    domain_name in grid_id. Second item is group number
    """
    logger = get_logger()
    regexp = get_variable_from_lset_without_default("simple_domain_grid_regexp")
    domain_id, n = re.subn(regexp[0], r'\%d' % regexp[1], grid_id)
    if n != 1:
        raise Dr2xmlError("Cannot identify domain name in grid_id %s using regexp %s" % (grid_id, regexp[0]))
    grid_def = DR2XMLGrid(id=grid_id)
    grid_def.append(DR2XMLDomain(domain_ref=domain_id))
    logger.warning("Warning: Guess that structure for grid %s is : %s" % (grid_id, grid_def))
    # raise dr2xml_error("Warning: Guess that structure for grid %s is : %s"%(grid_id,grid_def))
    return grid_def


def create_grid_def(grid_defs, axis_def, axis_name, src_grid_id):
    """
    Create and store a grid definition by changing in SRC_GRID_ID grid def
    its only axis member (either def or ref) with AXIS_DEF (where any id
    has been removed)

    Returned grid_id = input grid_id + suffix '_AXIS_NAME'

    raises error if there is not exactly one axis def or reg in input grid

    """
    src_grid_def = get_grid_def(src_grid_id, grid_defs)
    #
    # Retrieve axis key and remove id= from axis definition
    new_axis_def = axis_def.copy()
    axis_key = new_axis_def.attrib.pop("id")
    target_grid_id = src_grid_id + "_" + axis_key
    #
    # Change only first instance of axis_ref, which is assumed to match the vertical dimension
    # Enforce axis_name in axis_def :  TBD
    target_grid_def = src_grid_def.copy()
    target_grid_def.children = list()
    is_axis_changed = False
    for grid_child in src_grid_def:
        if not is_axis_changed and grid_child.tag == "axis":
            target_grid_def.append(new_axis_def)
            is_axis_changed = True
        else:
            target_grid_def.append(grid_child)
    if not is_axis_changed:
        raise Dr2xmlError("Fatal: cannot find an axis ref in grid %s : %s " % (src_grid_id, src_grid_def))
    target_grid_def.attrib["id"] = target_grid_id
    grid_defs[target_grid_id] = target_grid_def
    return target_grid_id


def create_axis_def(sdim, axis_defs, field_defs, pingvars):
    """

    From a simplified Dim object SDIM representing a vertical dimension,
    creates and stores an Xios axis definition in AXIS_DEFS

    If the dimension implies vertical interpolation (on air_pressure
    or altitude levels), creates and stores (in FIELD_DEFS) two
    intermediate fields for the sampling of that coordinate field at
    the vert_frequency and with the type of operation indicated by LSET

    If the dimension is a zoom of another one, analyzes its 'requested'
    field against the list of values declared for the other one, for
    defining the zoom in XIOS syntax

    """
    logger = get_logger()
    prefix = get_variable_from_lset_without_default("ping_variables_prefix")
    # nbre de valeurs de l'axe determine aussi si on est en dim singleton
    if sdim.requested:
        glo_list = sdim.requested.strip(" ").split()
    else:
        glo_list = sdim.value.strip(" ").split()
    glo_list_num = [float(v) for v in glo_list]
    glo_list_num.sort(reverse=True)
    n_glo = len(glo_list)

    if not sdim.is_zoom_of:  # pure interpolation
        # Axis is not a zoom of another, write axis_def normally (with value, interpolate_axis,etc.)
        if n_glo > 1:
            # Case of a non-degenerated vertical dimension (not a singleton)
            value = "(0,{})[ {} ]".format(n_glo - 1, sdim.requested)
        elif n_glo != 1:
            logger.warning("Warning: axis for %s is singleton but has %d values" % (sdim.label, n_glo))
            return None
        else:
            # Singleton case (degenerated vertical dimension)
            value = '(0,0)[ {} ]'.format(sdim.value)
        axis_xml = DR2XMLAxis(id=sdim.label, name=sdim.out_name, standard_name=sdim.stdname, long_name=sdim.long_name,
                              unit=sdim.units, positive=sdim.positive, axis_type=sdim.axis, n_glo=str(n_glo),
                              value=value)
        # Define some other values
        if sdim.stdname in ["air_pressure", ]:
            coordname = prefix + "pfull"
        elif sdim.stdname in ["altitude", ]:
            coordname = prefix + "zg"
        else:
            coordname = prefix + sdim.label
        if coordname not in pingvars:
            raise Dr2xmlError("Could not find coordinate variable %s in pingfile." % coordname)
        #
        # Create an intermediate field for coordinate , just adding time sampling
        operation = get_variable_from_lset_with_default("vertical_interpolation_operation", "instant")
        coordname_with_op = coordname + "_" + operation  # e.g. CMIP6_pfull_instant
        coorddef_op = DR2XMLField(id=coordname_with_op, field_ref=coordname, operation=operation,
                                  detect_missing_value="true")
        field_defs[coordname_with_op] = coorddef_op
        #
        # Create and store a definition for time-sampled field for the vertical coordinate
        vert_frequency = get_variable_from_lset_without_default("vertical_interpolation_sample_freq")
        coordname_sampled = coordname_with_op + "_sampled_" + vert_frequency  # e.g. CMIP6_pfull_instant_sampled_3h
        axis_xml.append(DR2XMLInterpolateAxis(type="polynomial", order="1", coordinate=coordname_sampled))
        # Store definition for the new axis
        axis_defs[sdim.label] = axis_xml
        coorddef = DR2XMLField(id=coordname_sampled, field_ref=coordname_with_op, freq_op=vert_frequency,
                               detect_missing_value="true", text="@{}".format(coordname))
        field_defs[coordname_sampled] = coorddef
    else:  # zoom case
        # Axis is subset of another, write it as a zoom_axis
        axis_xml = DR2XMLAxis(id=sdim.zoom_label, axis_ref=sdim.zoom_of, name="plev", axis_type=sdim.axis)
        values = re.sub(r'.*\[ *(.*) *\].*', r'\1', axis_defs[sdim.is_zoom_of].attrib["value"])
        values = values.split("\n")[0]
        union_vals = values.strip(" ").split()
        union_vals_num = [float(v) for v in union_vals]
        index_values = "(0, {})[ {} ]".format(n_glo - 1,
                                              " ".join([str(union_vals_num.index(val)) for val in glo_list_num]))
        axis_xml.append(DR2XMLZoomAxis(index_values=index_values))
        # Store definition for the new axis
        axis_defs[sdim.zoom_label] = axis_xml
    return axis_xml


def change_domain_in_grid(domain_id, grid_defs, ping_alias=None, src_grid_id=None, turn_into_axis=False):
    """
    Provided with a grid id SRC_GRID_ID or alternatively a variable name (ALIAS),
    (SRC_GRID)
     - creates and stores a grid_definition where the domain_id has been changed to DOMAIN_ID
    -  returns its id, which is
    """
    if src_grid_id is None:
        raise Dr2xmlError("deprecated")
    else:
        src_grid = get_grid_def_with_lset(src_grid_id, grid_defs)
    target_grid_id = src_grid_id + "_" + domain_id
    # print("<<<DEBUG>>> src_grid_id, domain_id, target_grid_id", src_grid_id, domain_id, target_grid_id)
    # sequence below was too permissive re. assumption that all grid definition use refs rather than ids
    # (target_grid_string,count)=re.subn('domain *id= *.([\w_])*.','%s id="%s" %s'% \
    # (domain_or_axis,domain_id,axis_name), src_grid_string,1)
    # if count != 1 :
    target_grid_xml = src_grid.copy()
    is_domain_found = False
    for (rank, grid_child) in enumerate(src_grid):
        # print("<<<DEBUG>>> rank, tag, domain_ref in", rank, grid_child.tag, "domain_ref" in grid_child.attrib)
        if not is_domain_found and grid_child.tag == "domain" and "domain_ref" in grid_child.attrib:
            if turn_into_axis:
                target_grid_xml[rank].tag = "axis"
                del target_grid_xml[rank].attrib["domain_ref"]
                target_grid_xml[rank].attrib["axis_ref"] = domain_id
                target_grid_xml[rank].attrib["name"] = "lat"
            else:
                target_grid_xml[rank].attrib["domain_ref"] = domain_id
            is_domain_found = True
    if not is_domain_found:
        raise Dr2xmlError("Fatal: cannot find a domain to replace by %s in src_grid_string %s" % (domain_id, src_grid))
    target_grid_xml.attrib["id"] = target_grid_id
    grid_defs[target_grid_id] = target_grid_xml
    # print "target_grid_id=%s : %s"%(target_grid_id,target_grid_string)
    return target_grid_id


def get_grid_def_with_lset(grid_id, grid_defs):
    """
    Get the grid definition corresponding to grid_id.
    """
    try:
        grid_def = get_grid_def(grid_id, grid_defs)
    except:
        grid_def = guess_simple_domain_grid_def(grid_id)
        grid_defs[grid_id] = grid_def
    return grid_def


def change_axes_in_grid(grid_id, grid_defs, axis_defs):
    """
    Create a new grid based on GRID_ID def by changing all its axis references to newly created
    axis which implement CMIP6 axis attributes
    Works only on axes which id match the labels of DR dimensions (e.g. sdepth, landUSe ...)
    Stores the definitions in GRID_DEFS and AXIS_DEFS
    Returns the new grid_id
    """
    global axis_count
    grid_def_init = get_grid_def(grid_id, grid_defs)
    grid_def = grid_def_init.copy()
    output_grid_id = grid_id
    axes_to_change = []
    # print "in change_axis for %s "%(grid_id)

    # Get settings info about axes normalization
    aliases = get_variable_from_lset_with_default('non_standard_axes', OrderedDict())

    # Add cases where dim name 'sector' should be used,if needed
    # sectors = dims which have type charcter and are not scalar
    if is_key_in_lset('sectors'):
        sectors = get_variable_from_lset_without_default('sectors')
    else:
        sectors = [dim.label for dim in get_collection('grids').items if dim.type == 'character' and dim.value == '']
    if 'typewetla' in sectors:
        sectors.remove('typewetla')  # Error in DR 01.00.21
    # print "sectors=",sectors
    for sector in sectors:
        found = False
        for aid in aliases:
            if aliases[aid] == sector:
                found = True
                continue
            if isinstance(aliases[aid], tuple) and aliases[aid][0] == sector:
                found = True
                continue
        if not found:
            # print "\nadding sector : %s"%sector
            aliases[sector] = sector

    for sub in grid_def:
        if sub.tag in ['axis', ]:
            # print "checking grid %s"%grid_def
            if 'axis_ref' not in sub.attrib:
                # Definitely don't want to change an unnamed axis. Such an axis is
                # generated by vertical interpolation
                if any([ssub.tag in ['interpolate_axis', ] for ssub in sub]):
                    continue
                else:
                    print("Cannot normalize an axis in grid %s : no axis_ref for axis %s" % (grid_id, sub))
                    continue
                    # raise dr2xml_error("Grid %s has an axis without axis_ref : %s"%(grid_id,grid_def))
            axis_ref = sub.attrib['axis_ref']
            #

            # Just quit if axis doesn't have to be processed
            if axis_ref not in aliases:
                # print "for grid ",grid_id,"axis ",axis_ref, " is not in aliases"
                continue
            #
            dr_axis_id = aliases[axis_ref]
            alt_labels = None
            if isinstance(dr_axis_id, tuple):
                dr_axis_id, alt_labels = dr_axis_id
            dr_axis_id = dr_axis_id.replace('axis_', '')  # For toy_cnrmcm, atmosphere part
            # print ">>> axis_ref=%s, dr_axis_id=%s,alt_labels=%s"%(axis_ref,dr_axis_id,alt_labels),aliases[axis_ref]
            #
            dim_id = 'dim:{}'.format(dr_axis_id)
            # print "in change_axis for %s %s"%(grid_id,dim_id)
            if dim_id not in get_uid():  # This should be a dimension !
                raise Dr2xmlError("Value %s in 'non_standard_axes' is not a DR dimension id" % dr_axis_id)
            dim = get_uid(dim_id)
            # We don't process scalars here
            if dim.value in ['', ] or dim.label in ["scatratio", ]:
                axis_id, axis_name = create_axis_from_dim(dim, alt_labels, axis_ref, axis_defs)
                # cannot use ET library which does not guarantee the ordering of axes
                axes_to_change.append((axis_ref, axis_id, axis_name))
                output_grid_id += "_" + dim.label
            else:
                raise Dr2xmlError("Dimension %s is scalar and shouldn't be quoted in 'non_standard_axes'" % dr_axis_id)
    if len(axes_to_change) == 0:
        return grid_id
    grid_def_rep = grid_def.copy()
    for (rank, grid_child) in enumerate(grid_def):
        axes_to_change_new = list()
        for old, new, name in axes_to_change:
            if grid_child.tag in ["axis", ] and "axis_ref" in grid_child.attrib and \
                    grid_child.attrib["axis_ref"] == old:
                axis_count += 1
                grid_def_dict = OrderedDict()
                grid_def_dict["axis_ref"] = new
                grid_def_dict["name"] = name
                grid_def_dict["id"] = "ref_to_{}_{}".format(new, axis_count)
                grid_def_rep[rank].attrib = grid_def_dict
            else:
                axes_to_change_new.append((old, new, name))
        axes_to_change = axes_to_change_new
    grid_def_rep.attrib["id"] = output_grid_id
    grid_defs[output_grid_id] = grid_def_rep
    return output_grid_id


def create_axis_from_dim(dim, labels, axis_ref, axis_defs):
    """
    Create an axis definition by translating all DR dimension attributes to XIos
    constructs generating CMIP6 requested attributes
    """
    axis_id = "DR_" + dim.label + "_" + axis_ref
    if dim.type == "character":
        axis_name = "sector"
    else:
        axis_name = dim.altLabel
    if axis_id in axis_defs:
        return axis_id, axis_name

    #
    prec_dict = dict(double="8", integer="2", int="2", prec="4")
    value = None
    bounds = None
    dim_name = None
    label = None
    if dim.type not in ["character", ]:
        if dim.requested != "":
            nb = len(dim.requested.split())
            value = "(0,{})[ {} ]".format(nb, dim.requested.strip())
        if isinstance(dim.boundsRequested, list):
            vals = " ".join([str(v) for v in dim.boundsRequested])
            valsr = reduce(lambda x, y: x + y, vals)
            bounds = "(0,1)x(0,{})[ {} ]".format(nb - 1, valsr)
    else:
        dim_name = dim.altLabel
        if labels is None:
            labels = dim.requested
        if dim.label == "oline" and get_variable_from_lset_with_default('add_Gibraltar', False):
            labels += " gibraltar"
        labels = labels.replace(', ', ' ').replace(',', ' ')
        length = len(labels.split())
        # print 'labels=',labels.split()
        strings = " "
        for s in labels.split():
            strings += "%s " % s
        if length > 0:
            label = "(0,{})[ {} ]".format(length - 1, strings)
    rep = DR2XMLAxis(id=axis_id, name=axis_name, axis_ref=axis_ref, standard_name=dim.standardName,
                     long_name=dim.title, prec=prec_dict.get(dim.type), unit=dim.units, value=value, bounds=bounds,
                     dim_name=dim_name, label=label, axis_type=dim.axis)
    axis_defs[axis_id] = rep
    # print "new DR_axis :  %s "%rep
    return axis_id, axis_name


def is_vert_dim(sdim):
    """
    Returns True if dim represents a dimension for which we want
    an Xios interpolation.
    For now, a very simple logics for interpolated vertical
    dimension identification:
    """
    # SS : p840, p220 sont des couches de pression.  On les detecte par l'attribut value
    # test=(sdim.stdname=='air_pressure' or sdim.stdname=='altitude') and (sdim.value == "")
    test = (sdim.axis == 'Z')
    return test


def scalar_vertical_dimension(sv):
    """
    Return the altLabel attribute if it is a vertical dimension, else None.
    """
    if 'cids' in sv.struct.__dict__:
        cid = get_uid(sv.struct.cids[0])
        if cid.axis in ['Z', ]:
            return cid.altLabel
    return None


def create_output_grid(ssh, grid_defs, domain_defs, target_hgrid_id, margs):
    """
    Build output grid (stored in grid_defs) by analyzing the spatial shape
    Including horizontal operations. Can include horiz re-gridding specification
    """
    grid_ref = None

    # Compute domain name, define it if needed
    if ssh[0:2] in ['Y-', ]:  # zonal mean and atm zonal mean on pressure levels
        # Grid normally has already been created upstream
        grid_ref = margs['src_grid_id']
    elif ssh in ['S-na', ]:
        # COSP sites. Input field may have a singleton dimension (XIOS scalar component)
        grid_ref = cfsites_grid_id
        add_cfsites_in_defs(grid_defs, domain_defs)
        #
    elif ssh[0:3] in ['XY-', 'S-A']:
        # this includes 'XY-AH' and 'S-AH' : model half-levels
        if ssh[0:3] in ['S-A', ]:
            add_cfsites_in_defs(grid_defs, domain_defs)
            target_hgrid_id = cfsites_domain_id
        if target_hgrid_id:
            # Must create and a use a grid similar to the last one defined
            # for that variable, except for a change in the hgrid/domain
            grid_ref = change_domain_in_grid(target_hgrid_id, grid_defs)
            if grid_ref is False or grid_ref is None:
                raise Dr2xmlError("Fatal: cannot create grid_def for %s with hgrid=%s" % (alias, target_hgrid_id))
    elif ssh in ['TR-na', 'TRS-na']:  # transects,   oce or SI
        pass
    elif ssh[0:3] in ['YB-', ]:  # basin zonal mean or section
        pass
    elif ssh in ['na-na', ]:  # TBD ? global means or constants - spatial integration is not handled
        pass
    elif ssh in ['na-A', ]:  # only used for rlu, rsd, rsu ... in Efx ????
        pass
    else:
        raise Dr2xmlError(
            "Fatal: Issue with un-managed spatial shape %s for variable %s in table %s" % (ssh, sv.label, table))
    return grid_ref


def create_standard_domains(domain_defs):
    """
    Add to dictionnary domain_defs the Xios string representation for DR-standard horizontal grids, such as '1deg'

    """
    # Next definition is just for letting the workflow work when using option dummy='include'
    # Actually, ping_files for production run at CNRM do not activate variables on that grid (IceSheet vars)
    domain_defs['25km'] = create_standard_domain('25km', 1440, 720)
    domain_defs['50km'] = create_standard_domain('50km', 720, 360)
    domain_defs['100km'] = create_standard_domain('100km', 360, 180)
    domain_defs['1deg'] = create_standard_domain('1deg', 360, 180)
    domain_defs['2deg'] = create_standard_domain('2deg', 180, 90)


def create_standard_domain(resol, ni, nj):
    """
    Create a xml like string corresponding to the domain using resol, ni and nj.
    """
    rep = DR2XMLDomain(id="CMIP6_{}".format(resol), ni_glo=str(ni), nj_glo=str(nj), type="rectilinear", prec="8")
    rep.append(DR2XMLGenerateRectilinearDomain())
    rep.append(DR2XMLInterpolateDomain(order="1", renormalize="true", mode="read_or_compute", write_weight="true"))
    return rep


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
        if child.tag in ["scalar", ]:
            if "scalar_ref" in child.attrib and child.attrib["scalar_ref"] in [scalar_id, ]:
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
            if child.tag in ["scalar", ]:
                if any([scalar_child.tag in ["extract_axis", ] for scalar_child in child]):
                    test_child = True
            if test_child:
                count += 1
                children_to_remove.append(child)
        for child_to_remove in children_to_remove:
            rep.remove(child_to_remove)
    if "id" in rep.attrib:
        rep.attrib["id"] = gridout_id
        rep.append(DR2XMLScalar(scalar_ref=scalar_id, name=scalar_name))
    else:
        raise Dr2xmlError("No way to add scalar '%s' in grid '%s'" % (scalar_id, gridin_def))
    # Remove any axis if asked for
    if remove_axis:
        remove_subelement_in_xml_element(xml_element=rep, tag="axis")
        # if count==1 :
        #    print "Info: axis has been removed for scalar %s (%s)"%(scalar_name,scalar_id)
        #    print "grid_def="+rep
    return rep