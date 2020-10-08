#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration variables and associated tools.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import sys

# Utilities
from utils import Dr2xmlError


# Python version
python_version = "python"+sys.version[0]

# General variables
version = "2.2"  # dr2xml version

# CMIP6 variables
conventions = "CF-1.7 CMIP-6.2"
# The current code should comply with this version of spec doc at
# https://docs.google.com/document/d/1h0r8RZr_f3-8egBMMh7aqLwy3snpD6_MrDz1q8n5XUk/edit
CMIP6_conventions_version = "v6.2.4"

# Variable used for storing index of xml files
context_index = None

# Variable used to store cell method warnings
cell_method_warnings = list()


# Functions to deal with those configuration variables
def set_config_variable(variable, value):
    """
    Set the value of the indicated global variable
    """
    if variable == "context_index":
        global context_index
        context_index = value
    elif variable == "cell_method_warnings":
        global cell_method_warnings
        cell_method_warnings = value
    else:
        raise Dr2xmlError("Can not set configuration variable %s." % variable)


def get_config_variable(variable):
    """
    Get the value of the indicated global variable.
    """
    if variable == "context_index":
        return context_index
    elif variable == "conventions":
        return conventions
    elif variable == "version":
        return version
    elif variable == "CMIP6_conventions_version":
        return CMIP6_conventions_version
    elif variable == "cell_method_warnings":
        return cell_method_warnings
    else:
        raise Dr2xmlError("Unknown configuration variable %s." % variable)


def add_value_in_list_config_variable(variable, value):
    """
    Add a value to a list-type configuration variable.
    """
    if variable == "cell_method_warnings":
        global cell_method_warnings
        cell_method_warnings.append(value)
    else:
        raise Dr2xmlError("Could not add a value to configuration variable %s." % variable)
