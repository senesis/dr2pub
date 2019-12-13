#!/usr/bin/env python
# coding: utf-8

"""
Header
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import re
from collections import OrderedDict
from copy import deepcopy

from xml_writer.beacon import Beacon
from xml_writer.utils import encode_if_needed, _generic_dict_regexp, _build_dict_attrib


class Header(Beacon):
    """
    Class to deal with xml header.
    """
    def __init__(self, tag, attrib=OrderedDict()):
        super(Header, self).__init__()
        self.tag = tag
        self.attrib = deepcopy(attrib)

    def __eq__(self, other):
        test = super(Header, self).__eq__(other)
        if test:
            test = self._test_attribute_equality("tag", other)
        if test:
            test = self._test_dict_equality(self.attrib, other.attrib)
        return test

    def __copy__(self):
        element = Header(tag=self.tag, attrib=deepcopy(self.attrib))
        element.update_level(self.level)
        return element

    def dump(self):
        offset = "\t" * self.level
        if len(self.attrib) > 0:
            rep = offset + '<?{} {}?>'.format(self.tag, self._dump_attrib())
        else:
            rep = offset + '<?{}?>'.format(self.tag)
        return encode_if_needed(rep)

    def _dump_attrib(self, sort=False):
        return self.dump_dict(deepcopy(self.attrib), sort=sort)


# XML header regexp
_xml_header_regexp = re.compile(r'(\s?<\s?\?\s?(?P<tag>\w*){}\s?\?>\s?)'.format(_generic_dict_regexp))
_xml_header_regexp_begin = re.compile(r'^<\s?\?\s?(?P<tag>\w*){}\s?\?>'.format(_generic_dict_regexp))


def _find_xml_header(xml_string, verbose=False):
    pattern_findall = _xml_header_regexp.findall(xml_string)
    if len(pattern_findall) > 1:
        raise Exception("There should be only one header in an XML document.")
    elif len(pattern_findall) == 0:
        return xml_string, None
    else:
        pattern_match = _xml_header_regexp_begin.match(xml_string)
        if not pattern_match:
            raise Exception("Header should be at the beginning of the xml document.")
        else:
            match_group_dict = pattern_match.groupdict()
            tag = match_group_dict["tag"]
            attrib = _build_dict_attrib(match_group_dict["attrib"])
            header = Header(tag=tag, attrib=attrib)
            xml_string = xml_string.replace(pattern_findall[0][0], "", 1)
            return xml_string, header
