#!/usr/bin/env python
# coding: utf-8

"""
Beacon
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict


class Beacon(object):
    """
    Generic class to deal with XML beacons.
    """
    def __init__(self):
        self.level = 0

    def __str__(self):
        return self.dump()

    def __repr__(self):
        return self.dump()

    def __len__(self):
        return len(self.dump())

    def __eq__(self, other):
        test = isinstance(other, type(self))
        if test:
            test = self._test_attribute_equality("level", other)
        return test

    def __copy__(self):
        element = Beacon()
        element.update_level(self.level)
        return element

    def __getitem__(self, item):
        pass

    def __setitem__(self, key, value):
        pass

    def __delitem__(self, key):
        pass

    def copy(self):
        return self.__copy__()

    def dump(self):
        raise NotImplementedError()

    @staticmethod
    def _test_dict_equality(a_dict, an_other_dict):
        test = isinstance(a_dict, (dict, OrderedDict)) and isinstance(an_other_dict, (dict, OrderedDict))
        if test:
            test = len(a_dict) == len(an_other_dict)
        if test:
            test = all([key in an_other_dict and value == an_other_dict[key] for (key, value) in a_dict.items()])
        return test

    def _test_attribute_equality(self, attrib, other):
        if attrib == "text":
            default = ""
        else:
            default = None
        self_attrib = getattr(self, attrib, default)
        other_attrib = getattr(other, attrib, default)
        test = isinstance(other_attrib, type(self_attrib))
        if test and self_attrib != default and other_attrib != default and self_attrib == other_attrib:
            return True
        else:
            return False

    @staticmethod
    def correct_attrib(attrib):
        if not isinstance(attrib, (dict, OrderedDict)):
            raise TypeError("attrib must be a dict or an OrderDict.")
        corrected_attrib = OrderedDict()
        for (key, value) in attrib.items():
            corrected_attrib[str(key)] = str(value)
        return corrected_attrib

    @staticmethod
    def dump_dict(a_dict, sort=False):
        if len(a_dict) > 0:
            list_key_value = [(key, value) for (key, value) in a_dict.items()]
            if sort:
                list_key_value = sorted(list_key_value, key=lambda t: t[0])
            return " ".join(['{}={}'.format(key, '"{}"'.format(value)) for (key, value) in list_key_value])
        else:
            return None

    def _dump_attrib(self, sort=False):
        raise NotImplementedError()

    def update_level(self, new_level):
        if self.level != new_level:
            self.level = new_level
