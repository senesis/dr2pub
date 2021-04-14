#!/usr/bin/env python
# coding: utf-8

"""
Elements
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import re
from collections import OrderedDict
from copy import deepcopy, copy

from xml_writer.beacon import Beacon
from xml_writer.header import Header
from xml_writer.comment import Comment
from xml_writer.utils import encode_if_needed, decode_if_needed, _generic_dict_regexp, \
    _build_dict_attrib, print_if_needed


class Element(Beacon):
    """
    Class to deal with xml elements.
    """
    def __init__(self, tag, text=None, attrib=OrderedDict()):
        """

        :param tag:
        :param text:
        :param attrib:
        """
        super(Element, self).__init__()
        self.tag = tag.strip()
        self.text = text
        self.attrib = deepcopy(attrib)
        self.children = list()

    def __eq__(self, other):
        """

        :param other:
        :return:
        """
        test = super(Element, self).__eq__(other)
        if test:
            test = self._test_attribute_equality("tag", other)
        if test:
            test = self._test_attribute_equality("text", other)
        if test:
            test = self._test_dict_equality(self.attrib, other.attrib)
        if test:
            test = self._test_attribute_equality("children", other)
        return test

    def __len__(self):
        """

        :return:
        """
        return len(self.children)

    def __copy__(self):
        """

        :return:
        """
        element = Element(tag=self.tag, text=self.text, attrib=deepcopy(self.attrib))
        element.update_level(self.level)
        for child in self.children:
            element.children.append(copy(child))
        return element

    def dump(self):
        """

        :return:
        """
        offset = "\t" * self.level
        # Deal with header
        if len(self.attrib) > 0:
            header = " ".join([self.tag, self._dump_attrib()])
        else:
            header = self.tag
        # Deal with content
        if len(self) == 0:
            if self.text is None:
                content = None
            else:
                content = " {} ".format(self.text)
        else:
            if self.text is None:
                content = "\n{}\n{}".format(self._dump_children(), offset)
            else:
                content = "{}\t{}\n{}\n{}".format(offset, self.text, self._dump_children(), offset)
        # Build the string
        if content is None:
            rep = "{}<{}/>".format(offset, header)
        else:
            rep = "{}<{}>{}</{}>".format(offset, header, content, self.tag)
        return encode_if_needed(rep)

    def set_text(self, text):
        """

        :param text:
        :return:
        """
        if len(text) > 0:
            if self.text is None:
                self.text = text
            else:
                self.text = "\n".join([self.text, text])

    def __getitem__(self, item):
        """

        :param item:
        :return:
        """
        return self.children[item]

    def __setitem__(self, key, value):
        """

        :param key:
        :param value:
        :return:
        """
        self.children[key] = value

    def __delitem__(self, key):
        """

        :param key:
        :return:
        """
        self.remove(self[key])

    def append(self, element):
        """

        :param element:
        :return:
        """
        if element is not None:
            if not is_xml_element(element):
                raise TypeError("Could not append an element of type %s to an XML element." % type(element))
            element.update_level(self.level + 1)
            self.children.append(element)

    def extend(self, elements):
        """

        :param elements:
        :return:
        """
        if elements is not None:
            for (rank, element) in enumerate(elements):
                if not is_xml_element(element):
                    raise TypeError("Could not extend an XML element with elements of type %s." % type(element))
                else:
                    elements[rank].update_level(self.level + 1)
            self.children.extend(elements)

    def insert(self, index, element):
        """

        :param index:
        :param element:
        :return:
        """
        if element is not None:
            if not is_xml_element(element):
                raise TypeError("Could not insert an element of type %s to an XML element." % type(element))
            element.update_level(self.level + 1)
            self.children.insert(index, element)

    def replace(self, index, element):
        """

        :param index:
        :param element:
        :return:
        """
        if element is not None:
            if not is_xml_element(element):
                raise TypeError("Could not replace and XML element by an element of type %s to an XML element." %
                                type(element))
            element.update_level(self.level + 1)
            self.children[index] = element

    def remove(self, element):
        """

        :param element:
        :return:
        """
        if element is not None:
            if not is_xml_element(element):
                raise TypeError("Could not append an remove of type %s to an XML element." % type(element))
            self.children.remove(element)

    def update_level(self, new_level):
        """

        :param new_level:
        :return:
        """
        super(Element, self).update_level(new_level)
        if len(self.children) > 0:
            for i in range(len(self.children)):
                self.children[i].update_level(new_level + 1)

    def _dump_children(self):
        """

        :return:
        """
        if len(self.children) > 0:
            return "\n".join([decode_if_needed(child.dump()) for child in self.children])
        else:
            return ""

    def _dump_attrib(self, sort=False):
        """

        :param sort:
        :return:
        """
        return self.dump_dict(deepcopy(self.attrib), sort=sort)


#: XML single part regexp
_xml_single_part_element_regexp = re.compile(r'^\s?(?P<all><\s?(?P<tag>\w+)\s?{}\s?/>)\s?'.format(
    _generic_dict_regexp))


def _find_one_part_element(xml_string, verbose=False):
    """

    :param xml_string:
    :param verbose:
    :return:
    """
    print_if_needed("<<<find_one_part_element BEFORE>>>", len(xml_string), xml_string, verbose=verbose)
    xml_string = xml_string.strip()
    match_single_part = _xml_single_part_element_regexp.match(xml_string)
    if match_single_part:
        match_single_part = match_single_part.groupdict()
        tag = match_single_part["tag"].strip()
        attrib = _build_dict_attrib(match_single_part["attrib"])
        element = Element(tag=tag, attrib=attrib)
        xml_string = xml_string.replace(match_single_part["all"], "", 1)
        print_if_needed("<<<find_one_part_element AFTER>>>", len(xml_string), xml_string, verbose=verbose)
        return xml_string, element
    else:
        return xml_string, None


#: XML two parts regexp
_xml_string_first_element_replace = \
    r'(?P<all_begin>\s?(?P<begin><\s?(?P<tag>{}){}\s?>)\s?)'.format('{}', _generic_dict_regexp)
_xml_string_init_element_replace = r'^'+_xml_string_first_element_replace
_xml_init_two_parts_element_regexp = re.compile(_xml_string_init_element_replace.format(r"\w+\s?"))
_xml_string_end_element_replace = r'(?P<all_end>\s?(?P<end></\s?{}\s?>)\s?)'


def _find_two_parts_element_init(xml_string, verbose=False):
    """

    :param xml_string:
    :param verbose:
    :return:
    """
    xml_string = xml_string.strip()
    match = _xml_init_two_parts_element_regexp.match(xml_string)
    if not match:
        return xml_string, None
    else:
        match_group_dict = match.groupdict()
        begin = match_group_dict["begin"]
        tag = match_group_dict["tag"]
        attrib = match_group_dict["attrib"]
        attrib = _build_dict_attrib(attrib)
        xml_string = xml_string.replace(begin, "", 1).strip()
        elt = Element(tag=tag, attrib=attrib)
        return xml_string, elt


def _find_two_parts_element_end(xml_string, tag, verbose=False):
    """

    :param xml_string:
    :param tag:
    :param verbose:
    :return:
    """
    xml_string = xml_string.strip()
    match = re.compile(r"^" + _xml_string_end_element_replace.format(tag)).match(xml_string)
    if not match:
        return xml_string, None
    else:
        match_group_dict = match.groupdict()
        end = match_group_dict["end"]
        xml_string = xml_string.replace(end, "", 1).strip()
        return xml_string, True


def is_xml_element(element):
    """

    :param element:
    :return:
    """
    try:
        return element.is_xml_element()
    except:
        return False
