#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prototype of xml writer to keep order.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

import os

from xml_writer.beacon import Beacon
from xml_writer.element import Element
from xml_writer.header import Header
from xml_writer.comment import Comment
from xml_writer.parser import xml_file_parser, parse_xml_string_rewrite
from xml_writer.utils import encode_if_needed, decode_if_needed

if __name__ == "__main__":
    dr2xml_tests_dir = os.sep.join([os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1]), "tests"])
    for my_xml_file in [
        os.sep.join([dr2xml_tests_dir, "tests_xml_writer.xml"]),
    ]:
        print(my_xml_file)
        text, comments, header, root_element = xml_file_parser(my_xml_file, verbose=False)
        print(text)
        print(comments)
        print(header)
        print(root_element)
