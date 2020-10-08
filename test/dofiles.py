#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals


from settings import lab_and_model_settings, simulation_settings, my_cvspath
from dr2xml import generate_file_defs
from pingfiles_interface import ping_file_for_realms_list
from vars_selection import select_cmor_vars_for_lab
from settings_interface import initialize_dict

#
lab_and_model_settings["excluded_vars"] = []
#


if True:
    context = 'arpsfx'
    realms = lab_and_model_settings['realms_per_context'][context]
    initialize_dict(lab_and_model_settings)
    svars = select_cmor_vars_for_lab(printout=True)
    # ping_file_for_realms_list(context,realms,svars,comments=False,exact=False,dummy=True,
    ping_file_for_realms_list(lab_and_model_settings, context, realms, svars,
                              path_special="../input/special_defs",
                              comments=" ", exact=False, dummy=True,
                              prefix=lab_and_model_settings['ping_variables_prefix'],
                              filename='./ping_%s.xml' % context, dummy_with_shape=True)
    generate_file_defs(lab_and_model_settings, simulation_settings, year=2000, enddate="20010101",
                       context=context, pingfile="./ping_%s.xml" % context, printout=False,
                       cvs_path=my_cvspath, dummies='include', dirname="./", prefix="outputs/")

if False:
    context = 'nemo'
    realms = lab_and_model_settings['realms_per_context'][context]
    initialize_dict(lab_and_model_settings)
    svars = select_CMORvars_for_lab(printout=True)
    pingFileForRealmsList(context, realms, svars, comments=" ", exact=False, dummy=True,
                          prefix=lab_and_model_settings['ping_variables_prefix'],
                          filename='./ping_%s.xml' % context, dummy_with_shape=True)
    generate_file_defs(lab_and_model_settings, simulation_settings, year=2000, context=context,
                       pingfile="./ping_%s.xml" % context, printout=True,
                       cvs_path=my_cvspath, dummies='include', dirname="./", prefix="outputs/")
