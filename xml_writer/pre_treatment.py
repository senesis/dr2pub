#!/usr/bin/env python
# coding: utf-8

"""
Pre-treatment tools
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import re
import six

from xml_writer.utils import print_if_needed, iterate_on_string


def iterate_on_characters_to_check(xml_string, verbose=False):
    """

    :param xml_string:
    :param verbose:
    :return:
    """
    # Find the special characters' positions
    tmp_characters_to_check = list()
    list_other_greater = list()
    list_other_lower = list()
    for m in re.compile(r"<\?").finditer(xml_string):
        print_if_needed("Find begin header at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "begin_header"))
        list_other_lower.append(m.start())
    if len(tmp_characters_to_check) not in [0, 1]:
        raise Exception("There should be only one header at most...")
    for m in re.compile(r"\?>").finditer(xml_string):
        print_if_needed("Find end header at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "end_header"))
        list_other_greater.append(m.start() + 1)
    if len(tmp_characters_to_check) not in [0, 2]:
        raise Exception("There should be only one header at most...")
    for m in re.compile(r"<!--").finditer(xml_string):
        print_if_needed("Find begin comment at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "begin_comment"))
        list_other_lower.append(m.start())
    for m in re.compile(r"-->").finditer(xml_string):
        print_if_needed("Find end comment at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "end_comment"))
        list_other_greater.append(m.start() + 2)
    for m in re.compile(r"<").finditer(xml_string):
        if m.start() not in list_other_lower:
            tmp_characters_to_check.append((m.start(), "lower_than"))
            print_if_needed("Find lower than at pos", m.start(), verbose=verbose)
    for m in re.compile(r">").finditer(xml_string):
        if m.start() not in list_other_greater:
            tmp_characters_to_check.append((m.start(), "greater_than"))
            print_if_needed("Find greater than at pos", m.start(), verbose=verbose)
    for m in re.compile(r'"').finditer(xml_string):
        print_if_needed("Find double quote at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "double_quote"))
    for m in re.compile(r"'").finditer(xml_string):
        print_if_needed("Find single quote at pos", m.start(), verbose=verbose)
        tmp_characters_to_check.append((m.start(), "single_quote"))
    # Build the iterator
    tmp_characters_to_check = sorted(tmp_characters_to_check, key=lambda t: t[0])
    for (pos, char_type) in tmp_characters_to_check:
        yield pos, char_type


def _pre_xml_string_format(xml_string, verbose=False):
    """

    :param xml_string:
    :param verbose:
    :return:
    """
    if not isinstance(xml_string, six.string_types):
        raise TypeError("Argument must be a string or equivalent, not %s." % type(xml_string))
    # Some other pre-treatments on the string
    xml_string = xml_string.replace("\t", " ")
    xml_string = xml_string.strip()
    xml_string = xml_string.split(" ")
    xml_string = " ".join([m for m in xml_string if len(m) > 0])
    # Initialize the dictionary of strings to be replaced and the len of the xml string
    to_replace = dict()
    xml_string_len = len(xml_string) + 2
    # Initialize booleans and counters
    is_comment_open = False
    is_header_open = False
    is_double_quote_open = False
    is_single_quote_open = False
    nb_beacons_nested = 0
    is_beacon_open = False
    is_beacon_ending = False
    for (sub_xml_string, pos_init) in iterate_on_string(xml_string, separator="\n", verbose=verbose):
        # Loop on the characters' position to be checked
        for (pos, character_type) in iterate_on_characters_to_check(sub_xml_string, verbose=verbose):
            pos += pos_init
            if character_type == "begin_header":
                if not is_header_open:
                    is_header_open = True
                    print_if_needed("<<<pre_xml_string_format: open header>>>", pos, verbose=verbose)
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected open header>>>", pos, verbose=verbose)
                    raise Exception("There should be only one header, second opened at pos %d" % pos)
            elif character_type == "end_header":
                if is_header_open:
                    is_header_open = False
                    print_if_needed("<<<pre_xml_string_format: close header>>>", pos, verbose=verbose)
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected close header>>>", pos, verbose=verbose)
                    raise Exception("Unexpected end of header at pos %d" % pos)
            elif character_type == "begin_comment":
                if not is_comment_open:
                    is_comment_open = True
                    print_if_needed("<<<pre_xml_string_format: open comment>>>", pos, verbose=verbose)
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected open comment>>>", pos, verbose=verbose)
                    raise Exception("Comments should not be nested... "
                                    "Previous comment has not been closed when opening next at pos %d." % pos)
            elif character_type == "end_comment":
                if is_comment_open:
                    is_comment_open = False
                    print_if_needed("<<<pre_xml_string_format: close comment>>>", pos, verbose=verbose)
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected close comment>>>", pos, verbose=verbose)
                    raise Exception("Unexpected end of comment at pos %d" % pos)
            elif character_type == "double_quote":
                if is_comment_open or is_header_open or is_single_quote_open or \
                        (not is_beacon_open and nb_beacons_nested > 0):
                    print_if_needed("<<<pre_xml_string_format: double quote>>>", pos, verbose=verbose)
                elif is_double_quote_open:
                    print_if_needed("<<<pre_xml_string_format: close double quote>>>", pos, verbose=verbose)
                    is_double_quote_open = False
                else:
                    print_if_needed("<<<pre_xml_string_format: open double quote>>>", pos, verbose=verbose)
                    is_double_quote_open = True
            elif character_type == "single_quote":
                if is_comment_open or is_header_open or is_double_quote_open or \
                        (not is_beacon_open and nb_beacons_nested > 0):
                    print_if_needed("<<<pre_xml_string_format: single quote>>>", pos, verbose=verbose)
                elif is_single_quote_open:
                    to_replace[pos] = ("'", '"')
                    is_single_quote_open = False
                    print_if_needed("<<<pre_xml_string_format: close single quote>>>", pos, verbose=verbose)
                else:
                    to_replace[pos] = ("'", '"')
                    is_single_quote_open = True
                    print_if_needed("<<<pre_xml_string_format: open single quote>>>", pos, verbose=verbose)
            elif character_type == "greater_than":
                if is_comment_open or is_header_open or is_single_quote_open or is_double_quote_open:
                    to_replace[pos] = (">", "&gt")
                    print_if_needed("<<<pre_xml_string_format: greater than>>>", pos, verbose=verbose)
                elif is_beacon_open:
                    is_beacon_open = False
                    if is_beacon_ending:
                        nb_beacons_nested -= 1
                        is_beacon_ending = False
                    elif pos > 0 and xml_string[pos - 1] == "/":
                        pass
                    else:
                        nb_beacons_nested += 1
                    print_if_needed("<<<pre_xml_string_format: close beacon>>> %d (remain %d nested)"
                                    % (pos, nb_beacons_nested), verbose=verbose)
                elif nb_beacons_nested > 0:
                    print_if_needed("<<<pre_xml_string_format: greater than>>>", pos, verbose=verbose)
                    to_replace[pos] = (">", "&gt")
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected close beacon>>>", pos, verbose=verbose)
                    raise Exception("Unexpected '>' symbol", pos)
            elif character_type == "lower_than":
                if is_comment_open or is_header_open or is_single_quote_open or is_double_quote_open:
                    to_replace[pos] = ("<", "&lt")
                    print_if_needed("<<<pre_xml_string_format: lower than>>>", pos, verbose=verbose)
                elif not is_beacon_open:
                    print_if_needed("<<<pre_xml_string_format: open beacon>>>", pos, verbose=verbose)
                    is_beacon_open = True
                    if xml_string_len > pos + 1 and xml_string[pos + 1] == "/":
                        is_beacon_ending = True
                elif nb_beacons_nested > 0:
                    to_replace[pos] = ("<", "&lt")
                    print_if_needed("<<<pre_xml_string_format: lower than>>>", pos, verbose=verbose)
                else:
                    print_if_needed("<<<pre_xml_string_format: unexpected open beacon>>>", pos, verbose=verbose)
                    raise Exception("Unexpected '<' symbol", pos)
            else:
                raise ValueError("Unknown type %s for position %d" % (character_type, pos))
    # Check that all opened structure has been closed
    if verbose:
        print("<<<pre_xml_string_format: end treatment is_header_open>>>", is_header_open)
        print("<<<pre_xml_string_format: end treatment is_comment_open>>>", is_comment_open)
        print("<<<pre_xml_string_format: end treatment is_double_quote_open>>>", is_double_quote_open)
        print("<<<pre_xml_string_format: end treatment is_single_quote_open>>>", is_single_quote_open)
        print("<<<pre_xml_string_format: end treatment is_beacon_open>>>", is_beacon_open)
        print("<<<pre_xml_string_format: end treatment is_beacon_ending>>>", is_beacon_ending)
        print("<<<pre_xml_string_format: end treatment nb_beacons_nested>>>", nb_beacons_nested)
    if is_comment_open or is_header_open or is_double_quote_open or is_single_quote_open or is_beacon_open or \
            is_beacon_ending or nb_beacons_nested > 0:
        raise Exception("There is issues with beacons or quotes opening and ending...")
    # Replace all that needs to be replaced
    new_xml_string = xml_string
    for i in sorted(list(to_replace), reverse=True):
        new_xml_string = replace_char_at_pos_by_string(new_xml_string, to_replace[i][0],
                                                       to_replace[i][1], i, i + len(to_replace[i][0]) - 1,
                                                       verbose=verbose)
    # Last statistics and return result
    new_xml_string = new_xml_string.replace("\n", " ")
    new_xml_string = new_xml_string.split(" ")
    return " ".join([m for m in new_xml_string if len(m) > 0])


def replace_char_at_pos_by_string(complete_string, string_in, replace_out, pos_init, pos_end, verbose=False):
    """

    :param complete_string:
    :param string_in:
    :param replace_out:
    :param pos_init:
    :param pos_end:
    :param verbose:
    :return:
    """
    if verbose:
        print("<<<replace_char_at_pos_by_string>>> len of input string", len(complete_string))
    single_char = pos_init == pos_end
    if pos_init < 0 or (not single_char and pos_end > len(complete_string)) or \
            (single_char and pos_end >= len(complete_string)):
        raise Exception("The string to be replaced is not in the complete string")
    if (single_char and complete_string[pos_init] != string_in) or \
            (not single_char and complete_string[pos_init:pos_end] != string_in):
        raise Exception("The string to be replaced is not the one present: %s / %s" %
                        (string_in, complete_string[pos_init:pos_end]))
    if single_char:
        if pos_init == 0:
            return replace_out + complete_string[pos_end + 1:]
        elif pos_end == len(complete_string) - 1:
            return complete_string[:pos_init] + replace_out
        else:
            return complete_string[:pos_init] + replace_out + complete_string[pos_end + 1:]
    else:
        if pos_init == 0:
            return replace_out + complete_string[pos_end:]
        elif pos_end == len(complete_string):
            return complete_string[:pos_init] + replace_out
        else:
            return complete_string[:pos_init] + replace_out + complete_string[pos_end:]
