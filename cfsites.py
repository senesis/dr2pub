#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CFsites-related elements (CFMIP)
A file named cfsites_grid_file_name must be provided at runtime, which
includes a field named cfsites_grid_field_id, defined on an unstructured
grid which is composed of CF sites
"""

from __future__ import print_function, division, absolute_import, unicode_literals


from projects import DR2XMLFile, DR2XMLField, DR2XMLDomain, DR2XMLInterpolateDomain, DR2XMLGenerateRectilinearDomain, \
    DR2XMLGrid


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
    file_xml = DR2XMLFile(id=cfsites_grid_file_id, name=cfsites_grid_file_name, output_freq="1y")
    field_xml = DR2XMLField(id=cfsites_grid_field_id, grid_ref=cfsites_grid_id)
    file_xml.append(field_xml)
    return file_xml


def add_cfsites_in_defs(grid_defs, domain_defs):
    """
    Add grid_definition and domain_definition for cfsites in relevant dicts
    """
    grid_xml = DR2XMLGrid(id=cfsites_grid_id)
    domain_xml = DR2XMLDomain(domain_ref=cfsites_domain_id)
    grid_xml.append(domain_xml)
    grid_defs[cfsites_grid_id] = grid_xml

    domain_xml = DR2XMLDomain(id=cfsites_domain_id, type="unstructured", lat_name="latitude", lon_name="longitude",
                              dim_i_name="site", prec="8")
    domain_xml.append(DR2XMLGenerateRectilinearDomain())
    interpolate_domain = DR2XMLInterpolateDomain(order=1, renormalize="true", mode="read_or_compute",
                                                 write_weight="true")
    domain_xml.append(interpolate_domain)
    domain_defs[cfsites_radix] = domain_xml
