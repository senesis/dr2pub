#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Several tools used in dr2xml.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import sys
from collections import OrderedDict

from logger import get_logger


class Dr2xmlError(Exception):
    """
    dr2xml generic exceptions.
    """
    def __init__(self, valeur):
        self.valeur = valeur

    def __str__(self):
        logger = get_logger()
        logger.error(repr(self.valeur))
        return "\n\n" + repr(self.valeur) + "\n\n"
    # """ just for test"""


class Dr2xmlGridError(Exception):
    """
    Dr2xml grids specific exceptions.
    """
    def __init__(self, valeur):
        self.valeur = valeur

    def __str__(self):
        logger = get_logger()
        logger.error(repr(self.valeur))
        return repr(self.valeur)


class VarsError(Exception):
    """
    Vars specific exceptions.
    """
    def __init__(self, valeur):
        self.valeur = valeur

    def __str__(self):
        logger = get_logger()
        logger.error(repr(self.valeur))
        return "\n\n" + repr(self.valeur) + "\n\n"


def encode_if_needed(a_string, encoding="utf-8"):
    """

    :param a_string:
    :param encoding:
    :return:
    """
    logger = get_logger()
    if sys.version.startswith("2."):
        return a_string.encode(encoding)
    elif sys.version.startswith("3."):
        return a_string
    else:
        logger.error("Unknown Python version %s" % sys.version.split()[0])
        raise OSError("Unknown Python version %s" % sys.version.split()[0])


def decode_if_needed(a_string, encoding="utf-8"):
    """

    :param a_string:
    :param encoding:
    :return:
    """
    logger = get_logger()
    if sys.version.startswith("2."):
        return a_string.decode(encoding)
    elif sys.version.startswith("3."):
        return a_string
    else:
        logger.error("Unknown Python version %s" % sys.version.split()[0])
        raise OSError("Unknown Python version %s", sys.version.split()[0])


def print_struct(struct, skip_sep=False, sort=False, back_line=False):
    """

    :param struct:
    :param skip_sep:
    :param sort:
    :param back_line:
    :return:
    """
    if isinstance(struct, list):
        list_elt = [print_struct(elt) for elt in struct]
        if sort:
            list_elt = sorted(list_elt)
        rep = ", ".join(list_elt)
        if not skip_sep:
            rep = "[" + rep + "]"
        return rep
    elif isinstance(struct, tuple):
        rep = ", ".join([print_struct(elt) for elt in struct])
        if not skip_sep:
            rep = "(" + rep + ")"
        return rep
    elif isinstance(struct, (dict, OrderedDict)):
        list_keys = list(struct)
        if sort:
            list_keys = sorted(list_keys)
        if back_line:
            elements_sep = ",\n"
        else:
            elements_sep = ", "
        rep = elements_sep.join(["{} = {}".format(print_struct(key), print_struct(struct[key])) for key in list_keys])
        if not skip_sep:
            rep = "{" + rep + "}"
        return rep
    elif isinstance(struct, set):
        list_items = sorted(list(struct))
        rep = ", ".join([print_struct(elt) for elt in list_items])
        if not skip_sep:
            rep = "{" + rep + "}"
        return rep
    else:
        return "'{}'".format(struct)
