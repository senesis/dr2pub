#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface to get and set laboratory and simulations dictionaries.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import copy
from collections import OrderedDict
from six import string_types

from utils import dr2xml_error, decode_if_needed, print_struct


# Initial simulation (sset) and laboratory (lset) dictionaries
sset = None
lset = None


def initialize_dict(new_lset=None, new_sset=None):
    global sset, lset
    if new_lset is not None:
        lset = decode_strings_in_dict(new_lset)
    if new_sset is not None:
        sset = decode_strings_in_dict(new_sset)


def decode_strings(struct):
    if isinstance(struct, (int, float)):
        return struct
    elif isinstance(struct, string_types):
        struct = str(struct)
        struct = decode_if_needed(struct)
        return struct
    elif isinstance(struct, (dict, OrderedDict)):
        return decode_strings_in_dict(struct)
    elif isinstance(struct, list):
        return decode_strings_in_list(struct)
    elif isinstance(struct, tuple):
        return decode_strings_in_tuple(struct)
    elif isinstance(struct, set):
        return decode_strings_in_set(struct)
    else:
        raise TypeError("Type of value %s is not handled by dr2xml, please report it the development team."
                        % type(struct))


def decode_strings_in_dict(init_dict):
    new_dictionary = OrderedDict()
    for key in sorted(list(init_dict)):
        value = init_dict[key]
        value = decode_strings(value)
        new_dictionary[key] = value
    return new_dictionary


def decode_strings_in_set(init_set):
    new_set = set(decode_strings_in_list(list(init_set)))
    return new_set


def decode_strings_in_list(init_list):
    new_list = list()
    for value in init_list:
        new_list.append(decode_strings(value))
    return new_list


def decode_strings_in_tuple(init_tuple):
    new_tuple = list()
    for value in init_tuple:
        new_tuple.append(value)
    new_tuple = decode_strings_in_list(new_tuple)
    new_tuple = tuple(new_tuple)
    return new_tuple


def format_dict_for_printing(dictionary):
    if dictionary == "lset":
        dictionary = lset
    elif dictionary == "sset":
        dictionary = sset
    return print_struct(dictionary, back_line=True, sort=True)


def get_variable_from_sset_else_lset_with_default(key_sset, key_lset=None, default=None):
    """
    Find the best value by looking at the different dictionaries
    :param key_sset: a key to be looked for in the simulation dictionary
    :param key_lset: a key to be looked for in the laboratory dictionary
    :param default: the default value to put
    :return: the value associated with the specified key in the sset dictionary if exists,
    else in the lset dictionary, else default
    """
    if key_lset is None:
        key_lset = key_sset
    return sset.get(key_sset, lset.get(key_lset, default))


def get_variable_from_sset_else_lset_without_default(key_sset, key_lset=None):
    if key_lset is None:
        key_lset = key_sset
    if sset and key_sset in sset:
        return sset[key_sset]
    else:
        return lset[key_lset]


def get_variable_from_lset_with_default(key, default=None):
    return lset.get(key, default)


def get_variable_from_lset_without_default(*args):
    return get_variable_from_dict_without_default(dictionary=lset, args=args)


def get_variable_from_dict_without_default(dictionary, args):
    if len(args) > 1:
        newdict = copy.deepcopy(dictionary[args[0]])
        return get_variable_from_dict_without_default(dictionary=newdict, args=args[1:])
    elif len(args) == 1:
        return dictionary[args[0]]
    else:  # Should not happen
        raise dr2xml_error("Could not guess which key to look for.")


def get_variable_from_sset_with_default(key, default=None):
    return sset.get(key, default)


def get_variable_from_sset_with_default_in_sset(key, key_default):
    return sset.get(key, sset[key_default])


def get_variable_from_sset_without_default(*args):
    return get_variable_from_dict_without_default(dictionary=sset, args=args)


def is_key_in_lset(key):
    return lset and (key in lset)


def is_key_in_sset(key):
    return sset and (key in sset)


def is_sset_not_None():
    return sset


def get_lset_iteritems():
    return lset.items()


def get_sset_iteritems():
    return sset.items()


def get_source_id_and_type():
    if "configuration" in sset and "configurations" in lset:
        if sset["configuration"] in lset["configurations"]:
            source_id, source_type, unused = lset["configurations"][sset["configuration"]]
        else:
            raise dr2xml_error("configuration %s is not known (allowed values are :)" %
                               sset["configuration"] + repr(lset["configurations"]))
    else:
        source_id = sset['source_id']
        if 'source_type' in sset:
            source_type = sset['source_type']
        else:
            if 'source_types' in lset:
                source_type = lset['source_types'][source_id]
            else:
                raise dr2xml_error("Fatal: No source-type found - Check inputs")
    return source_id, source_type
