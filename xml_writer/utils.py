#!/usr/bin/env python
# coding: utf-8

"""
Utilities used by xml_writer.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import re
import sys
from collections import OrderedDict


python_version = sys.version[0]


def encode_if_needed(a_string, encoding="utf-8"):
    """
    If needed, encode the python string ``a_string`` into the encoding specify by ``encoding``.

    :param six.string_types a_string: the string to encode
    :param six.string_types encoding: the encoding to be used
    :return: a string encoded if needed
    """
    if python_version in ["2", ]:
        return a_string.encode(encoding)
    elif python_version in ["3", ]:
        return a_string
    else:
        raise OSError("Unknown Python version %s", python_version)


def decode_if_needed(a_string, encoding="utf-8"):
    """
    If needed, decode the python string ``a_string`` into the encoding specify by ``encoding``.

    :param six.string_types a_string: the string to decode
    :param six.string_types encoding: the encoding to be used
    :return: a string decoded if needed
    """
    if python_version == "2":
        return a_string.decode(encoding)
    elif python_version == "3":
        return a_string
    else:
        raise OSError("Unknown Python version %s", sys.version.split()[0])


#: XML dict regexp
_generic_dict_regexp = r'(?P<attrib>(\s(\w+\s?=\s?"([^"])*"\s?))*)'
#: XML key-value regexp
_dict_regexp = r'(?P<key>\w+)\s?=\s?"(?P<value>[^"]*)"'
_compiled_dict_regexp = re.compile(_dict_regexp)


def _build_dict_attrib(dict_string):
    """
    Transform ``dict_string``, which contains key-value pairs formatted as in ``_dict_regexp`` into a ordered dictionary
    keeping the order of the attributes read

    :param six.string_types dict_string: a string containing the key values pairs.
    :return: an OrderedDict containing the values provided by ``dict_string``
    """
    attrib = OrderedDict()
    if dict_string and len(dict_string) > 0:
        dict_string = dict_string.strip()
        for match in _compiled_dict_regexp.finditer(dict_string):
            (key, value) = match.groups()
            attrib[key] = value.strip().replace('"', '')
    return attrib


def _find_text(xml_string, fatal_sep=False, verbose=False, fatal=True):
    """
    Look for text elements in an XML string

    :param six.string_types xml_string: input xml string
    :param bool fatal_sep: should an error be raised if separators do not begin ``xml_string``?
    :param bool verbose: should verbose mode be active?
    :param bool fatal: should an error be raised in case of anomaly?
    :return: A couple (``xml_string``, ``xml_text``) where ``xml_string`` is the xml_string from which the text has been removed and ``xml_text`` is the text removed
    """
    xml_string = xml_string.strip()
    print_if_needed("<<<find_text: XML_STRING before>>>", len(xml_string), xml_string, verbose=verbose)
    rank_start_init_element = xml_string.find("<")
    rank_end_last_element = xml_string.rfind(">")
    if rank_start_init_element < 0 and rank_end_last_element < 0:
        if fatal_sep:
            raise Exception("Could not find initial and final beacons.")
        else:
            xml_text = xml_string
            xml_string = ""
    elif rank_start_init_element < 0 or rank_end_last_element < 0:
        if fatal:
            raise Exception("It seems that there is a problem in the XML file...")
        else:
            xml_text = ""
    else:
        end_text = xml_string[rank_end_last_element + 1:]
        init_text = xml_string[0:rank_start_init_element]
        xml_string = xml_string[rank_start_init_element:rank_end_last_element + 1]
        xml_text = " ".join([init_text, end_text])
    xml_text = xml_text.strip()
    print_if_needed("<<<find_text: TEXT after>>>", len(xml_text), xml_text, verbose=verbose)
    xml_string = xml_string.strip()
    print_if_needed("<<<find_text: XML_STRING after>>>", len(xml_string), xml_string, verbose=verbose)
    return xml_string, xml_text


def print_if_needed(*args, **kwargs):
    """
    Print the input ``args`` if verbose mode is active.

    :param args: list of elements to be printed
    :param bool verbose: should verbose mode be activated?
    """
    verbose = kwargs.get("verbose", False)
    if verbose:
        print(*args)


def iterate_on_string(xml_string, separator="\n", verbose=False):
    """
    Build an iterator by splitting ``xml_string`` at each ``separator`` and returning each one.

    :param six.string_types xml_string: an xml string that must be split
    :param six.string_types separator: the separator used to split the string
    :param bool verbose: should verbose mode be activate?
    :return: iterator on the string split at the position of each instance of operator.
    """
    new_xml_string = xml_string.split(separator)
    if len(new_xml_string) > 0 and len(new_xml_string[-1]) == 0:
        new_xml_string.pop()
    pos_init = 0
    for substring in new_xml_string:
        substring += separator
        yield (substring, pos_init)
        pos_init += len(substring)
