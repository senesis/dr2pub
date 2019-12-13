#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CFsites-related elements (CFMIP)
A file named cfsites_grid_file_name must be provided at runtime, which
includes a field named cfsites_grid_field_id, defined on an unstructured
grid which is composed of CF sites
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict


from xml_interface import create_xml_element, create_xml_sub_element


cfsites_radix = "cfsites"
cfsites_domain_id = cfsites_radix + "_domain"
cfsites_grid_id = cfsites_radix + "_grid"
cfsites_grid_file_name = cfsites_radix + "_grid"
cfsites_grid_file_id = cfsites_radix + "_file"
cfsites_grid_field_id = cfsites_radix + "_field"


def cfsites_input_filedef():
    """
    Returns a file definition for defining a COSP site grid by reading a field named
    'cfsites_grid_field' in a file named 'cfsites_grid.nc'
    """
    # rep='<file id="%s" name="%s" mode="read" >\n'%\
    file_dict = OrderedDict()
    file_dict["id"] = cfsites_grid_file_id
    file_dict["name"] = cfsites_grid_file_name
    file_dict["mode"] = "read"
    file_dict["output_freq"] = "1y"
    file_xml = create_xml_element(tag="file", attrib=file_dict)
    field_dict = OrderedDict()
    field_dict["id"] = cfsites_grid_field_id
    field_dict["operation"] = "instant"
    field_dict["grid_ref"] = cfsites_grid_id
    create_xml_sub_element(xml_element=file_xml, tag="field", attrib=field_dict)
    return file_xml


def add_cfsites_in_defs(grid_defs, domain_defs):
    """
    Add grid_definition and domain_definition for cfsites in relevant dicts
    """
    grid_xml = create_xml_element(tag="grid", attrib=OrderedDict(id=cfsites_grid_id))
    create_xml_sub_element(xml_element=grid_xml, tag="domain", attrib=OrderedDict(domain_ref=cfsites_domain_id))
    grid_defs[cfsites_grid_id] = grid_xml

    domain_dict = OrderedDict()
    domain_dict["id"] = cfsites_domain_id
    domain_dict["type"] = "unstructured"
    domain_dict["prec"] = "8"
    domain_dict["lat_name"] = "latitude"
    domain_dict["lon_name"] = "longitude"
    domain_dict["dim_i_name"] = "site"
    domain_xml = create_xml_element(tag="domain", attrib=domain_dict)
    create_xml_sub_element(xml_element=domain_xml, tag="generate_rectilinear_domain")
    interpolate_domain_dict = OrderedDict()
    interpolate_domain_dict["order"] = 1
    interpolate_domain_dict["renormalize"] = "true"
    interpolate_domain_dict["mode"] = "read_or_compute"
    interpolate_domain_dict["write_weight"] = "true"
    create_xml_sub_element(xml_element=domain_xml, tag="interpolate_domain", attrib=interpolate_domain_dict)
    domain_defs[cfsites_radix] = domain_xml
