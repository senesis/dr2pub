#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, division, absolute_import, unicode_literals

from settings_interface import get_variable_from_lset_with_default
from logger import get_logger

logger = get_logger()


project = get_variable_from_lset_with_default("project", "CMIP6")


if project in ["CMIP6", ]:
    from projects.cmip6 import DR2XMLFileDefinition, DR2XMLContext, DR2XMLFieldGroup, DR2XMLFieldDefinition, \
        DR2XMLAxisDefinition, DR2XMLAxisGroup, DR2XMLDomainDefinition, DR2XMLDomainGroup, DR2XMLGridDefinition, \
        DR2XMLScalarDefinition, DR2XMLFile, DR2XMLOutputFile, DR2XMLField, DR2XMLDomain, DR2XMLInterpolateDomain, \
        DR2XMLGenerateRectilinearDomain, DR2XMLGrid, DR2XMLAxis, DR2XMLInterpolateAxis, DR2XMLZoomAxis, DR2XMLScalar, \
        DR2XMLTemporalSplitting, DR2XMLVariable
else:
    logger.error("Unknown project %s" % project)
    raise ValueError("Unknown project %s" % project)
