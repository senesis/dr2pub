#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for xml_writer module
"""

from __future__ import division, print_function, unicode_literals, absolute_import

import unittest
from collections import OrderedDict
from copy import copy

from xml_writer.pre_treatment import _pre_xml_string_format, replace_char_at_pos_by_string, \
    iterate_on_characters_to_check
from xml_writer.element import _find_one_part_element, is_xml_element
from xml_writer.comment import _find_xml_comment
from xml_writer.header import _find_xml_header
from xml_writer.beacon import Beacon
from xml_writer.utils import _build_dict_attrib, _find_text, iterate_on_string
from xml_writer.parser import generate_xml_tree_from_list, find_next_element, generate_list_from_xml_string, \
    parse_xml_string_rewrite
from xml_writer import Comment, Header, Element


class TestNonSpecificMethods(unittest.TestCase):

    def setUp(self):
        self.my_beacon = Beacon()
        self.my_comment = Comment("A new comment !")
        self.my_header = Header("A header", OrderedDict(an_attrib="a_value", an_other_attrib=6))
        self.my_element = Element("An element", text="A text",
                                  attrib=OrderedDict(an_attrib="a_value", an_other_attrib=6))
        self.my_element.append(self.my_comment)

    def test_is_xml_element(self):
        # Test is_xml_element
        self.assertTrue(is_xml_element(self.my_beacon))
        self.assertTrue(is_xml_element(self.my_comment))
        self.assertTrue(is_xml_element(self.my_header))
        self.assertTrue(is_xml_element(self.my_element))
        self.assertFalse(is_xml_element("an_element"))

    def test_update_level(self):
        # Test update_level
        self.assertEqual(self.my_beacon.level, 0)
        self.my_beacon.update_level(0)
        self.assertEqual(self.my_beacon.level, 0)
        self.my_comment.update_level(2)
        self.assertEqual(self.my_comment.level, 2)

    def test_correct_attrib(self):
        # Test correct_attrib
        attrib = None
        with self.assertRaises(TypeError):
            self.my_beacon.correct_attrib(attrib)
        attrib = ["a_value", "an_other_value"]
        with self.assertRaises(TypeError):
            self.my_beacon.correct_attrib(attrib)
        attrib = dict(a_key="a_value", an_other_key=0)
        self.assertDictEqual(self.my_beacon.correct_attrib(attrib), dict(a_key="a_value", an_other_key="0"))
        attrib = OrderedDict(a_key="a_value", an_other_key=0)
        self.assertDictEqual(self.my_beacon.correct_attrib(attrib), OrderedDict(a_key="a_value", an_other_key="0"))

    def test_dict_equality(self):
        a = dict(a_key="a_value", an_other_key="an_other_value")
        b = OrderedDict(a_key="a_value", an_other_key="an_other_different_value")
        self.assertFalse(self.my_beacon._test_dict_equality(a, b))
        b["an_other_key"] = "an_other_value"
        self.assertTrue(self.my_beacon._test_dict_equality(a, b))
        del b["a_key"]
        self.assertFalse(self.my_beacon._test_dict_equality(a, b))
        self.assertFalse(self.my_beacon._test_dict_equality(a, "a_string"))

    def test_attrib_equality(self):
        an_other_beacon = Beacon()
        an_other_beacon.update_level(5)
        an_other_beacon.an_attrib = "my_attrib"
        self.assertFalse(an_other_beacon._test_attribute_equality("level", self.my_beacon))
        self.assertFalse(an_other_beacon._test_attribute_equality("an_attrib", self.my_beacon))
        an_other_beacon.update_level(self.my_beacon.level)
        self.assertTrue(an_other_beacon._test_attribute_equality("level", self.my_beacon))

    def test_dump_dict(self):
        # Test _dump_dict
        attrib = OrderedDict()
        self.assertIsNone(self.my_beacon.dump_dict(attrib))
        attrib["some_key"] = "é_value"
        attrib["other_key_à"] = "0"
        self.assertEqual(self.my_beacon.dump_dict(attrib), 'some_key="\xe9_value" other_key_\xe0="0"')
        self.assertEqual(self.my_beacon.dump_dict(attrib, sort=True), 'other_key_\xe0="0" some_key="\xe9_value"')


class TestsBeacon(unittest.TestCase):

    def setUp(self):
        self.my_beacon = Beacon()

    def test_create_beacon(self):
        a = Beacon()
        self.assertEqual(a.level, 0)

    def test_equality(self):
        # Test __eq__
        a_beacon = Beacon()
        self.assertTrue(self.my_beacon == a_beacon)
        self.my_beacon.update_level(5)
        self.assertFalse(self.my_beacon == a_beacon)
        self.my_beacon.update_level(0)

    def test_representation(self):
        # Test __str__ and __repr__
        with self.assertRaises(NotImplementedError):
            str(self.my_beacon)
        with self.assertRaises(NotImplementedError):
            repr(self.my_beacon)

    def test_length(self):
        # Test __len__
        with self.assertRaises(NotImplementedError):
            len(self.my_beacon)

    def test_dump(self):
        # Test dump
        with self.assertRaises(NotImplementedError):
            self.my_beacon.dump()

    def test_copy(self):
        # Test __copy__
        an_other_beacon = copy(self.my_beacon)
        self.assertTrue(isinstance(an_other_beacon, Beacon))
        self.assertEqual(an_other_beacon.level, self.my_beacon.level)
        a_third_beacon = self.my_beacon.copy()
        self.assertTrue(isinstance(a_third_beacon, Beacon))
        self.assertEqual(a_third_beacon.level, self.my_beacon.level)

    def test_dump_attrib(self):
        # Test _dump_attrib
        with self.assertRaises(NotImplementedError):
            self.my_beacon._dump_attrib()
        with self.assertRaises(NotImplementedError):
            self.my_beacon._dump_attrib(sort=True)


class TestsComments(unittest.TestCase):

    def setUp(self):
        self.my_comment = Comment("a very long comment")

    def test_create_comment(self):
        a = Comment("a comment !")
        self.assertEqual(a.level, 0)
        self.assertEqual(a.comment, "a comment !")
        with self.assertRaises(TypeError):
            Comment()

    def test_equality(self):
        # Test __eq__
        a_comment = Comment("some comment")
        a_comment.update_level(6)
        self.assertFalse(a_comment == self.my_comment)
        an_other_comment = Comment("some comment")
        self.assertFalse(a_comment == an_other_comment)
        an_other_comment.update_level(6)
        self.assertTrue(a_comment == an_other_comment)

    def test_representation(self):
        # Test __str__ and __repr__
        self.assertEqual(str(self.my_comment), "<!--a very long comment-->")
        self.assertEqual(repr(self.my_comment), "<!--a very long comment-->")

    def test_length(self):
        # Test __len__
        self.assertEqual(len(self.my_comment), 26)

    def test_dump(self):
        # Test dump
        self.assertEqual(self.my_comment.dump(), "<!--a very long comment-->")

    def test_copy(self):
        # Test __copy__
        an_other_comment = copy(self.my_comment)
        self.assertTrue(isinstance(an_other_comment, Comment))
        self.assertEqual(an_other_comment.level, self.my_comment.level)
        self.assertEqual(an_other_comment.comment, self.my_comment.comment)

    def test_dump_attrib(self):
        # Test _dump_attrib
        with self.assertRaises(NotImplementedError):
            self.my_comment._dump_attrib()
        with self.assertRaises(NotImplementedError):
            self.my_comment._dump_attrib(sort=True)


class TestsHeader(unittest.TestCase):

    def setUp(self):
        a_dict = OrderedDict()
        a_dict["an_other_key"] = "a value"
        a_dict["a_key"] = 5
        self.my_header = Header("some tag", a_dict)

    def test_create_header(self):
        a = Header("a tag")
        self.assertEqual(a.level, 0)
        self.assertEqual(a.tag, "a tag")
        b = Header("an other tag", OrderedDict(my_attrib=["a value", 6]))
        self.assertEqual(b.level, 0)
        self.assertEqual(b.tag, "an other tag")
        self.assertDictEqual(b.attrib, OrderedDict(my_attrib=["a value", 6]))
        with self.assertRaises(TypeError):
            Header()

    def test_equality(self):
        # Test __eq__
        a_header = Header("some tag")
        self.assertFalse(a_header == self.my_header)
        a_header = Header("some tag", dict(a_key=4, an_other = "a value"))
        self.assertFalse(a_header == self.my_header)
        a_dict = OrderedDict()
        a_dict["an_other_key"] = "a value"
        a_dict["a_key"] = 5
        a_header.attrib = a_dict
        self.assertTrue(a_header == self.my_header)

    def test_representation(self):
        # Test __str__ and __repr__
        self.assertEqual(str(self.my_header), '<?some tag an_other_key="a value" a_key="5"?>')
        self.assertEqual(repr(self.my_header), '<?some tag an_other_key="a value" a_key="5"?>')
        an_other_header = Header("a tag")
        self.assertEqual(str(an_other_header), "<?a tag?>")
        self.assertEqual(repr(an_other_header), "<?a tag?>")

    def test_length(self):
        # Test __len__
        self.assertEqual(len(self.my_header), 45)

    def test_dump(self):
        # Test dump
        self.assertEqual(self.my_header.dump(), '<?some tag an_other_key="a value" a_key="5"?>')

    def test_copy(self):
        # Test __copy__
        an_other_header = copy(self.my_header)
        self.assertTrue(isinstance(an_other_header, Header))
        self.assertEqual(an_other_header.level, self.my_header.level)
        self.assertEqual(an_other_header.tag, self.my_header.tag)
        self.assertDictEqual(an_other_header.attrib, self.my_header.attrib)

    def test_dump_attrib(self):
        # Test _dump_attrib
        self.assertEqual(self.my_header._dump_attrib(), 'an_other_key="a value" a_key="5"')
        self.assertEqual(self.my_header._dump_attrib(sort=True), 'a_key="5" an_other_key="a value"')


class TestElement(unittest.TestCase):

    def setUp(self):
        a_dict = OrderedDict()
        a_dict["an_other_key"] = "a value"
        a_dict["a_key"] = 5
        self.my_element = Element("some tag", attrib=a_dict)
        self.my_other_element = Element("an other tag", text="some text", attrib=a_dict)
        self.my_other_element.append(Comment("a comment"))
        self.my_other_element.append(copy(self.my_element))

    def test_create_element(self):
        with self.assertRaises(TypeError):
            Element()
        a = Element("a tag")
        self.assertEqual(a.level, 0)
        self.assertEqual(a.tag, "a tag")
        self.assertDictEqual(a.attrib, OrderedDict())
        self.assertIsNone(a.text)
        self.assertEqual(a.children, list())
        b = Element("an other tag", text="a text", attrib=OrderedDict(my_attrib=["a value", 6]))
        self.assertEqual(b.level, 0)
        self.assertEqual(b.tag, "an other tag")
        self.assertEqual(b.text, "a text")
        self.assertEqual(b.children, list())
        self.assertDictEqual(b.attrib, OrderedDict(my_attrib=["a value", 6]))
        b.append(a)
        self.assertEqual(b.children, [a])

    def test_equality(self):
        # Test __eq__
        an_element = Element("some tag")
        self.assertFalse(an_element == self.my_element)
        an_element = Element("some tag", attrib=dict(a_key=4, an_other = "a value"))
        self.assertFalse(an_element == self.my_element)
        a_dict = OrderedDict()
        a_dict["an_other_key"] = "a value"
        a_dict["a_key"] = 5
        an_element.attrib = a_dict
        self.assertTrue(an_element == self.my_element)

    def test_representation(self):
        # Test __str__ and __repr__
        self.assertEqual(str(self.my_element), '<some tag an_other_key="a value" a_key="5"/>')
        self.assertEqual(repr(self.my_element), '<some tag an_other_key="a value" a_key="5"/>')
        an_other_header = Header("a tag")
        self.assertEqual(str(self.my_other_element), '<an other tag an_other_key="a value" a_key="5">\tsome text\n\t<!--a comment-->\n\t<some tag an_other_key="a value" a_key="5"/>\n</an other tag>')
        self.assertEqual(repr(self.my_other_element), '<an other tag an_other_key="a value" a_key="5">\tsome text\n\t<!--a comment-->\n\t<some tag an_other_key="a value" a_key="5"/>\n</an other tag>')

    def test_length(self):
        # Test __len__
        self.assertEqual(len(self.my_element), 0)
        self.assertEqual(len(self.my_other_element), 2)

    def test_set_text(self):
        # Test set_text
        my_element = Element("a tag")
        text1 = "some text"
        text2 = "an other set of text"
        self.assertIsNone(my_element.text)
        my_element.set_text(text1)
        self.assertEqual(my_element.text, text1)
        my_element.set_text(text2)
        self.assertEqual(my_element.text, "\n".join([text1, text2]))

    def test_dump(self):
        # Test dump
        self.assertEqual(Element("a tag").dump(), '<a tag/>')
        an_element = Element("a tag")
        an_element.append(Comment("a comment"))
        self.assertEqual(an_element.dump(), '<a tag>\n\t<!--a comment-->\n</a tag>')
        self.assertEqual(Element("a tag", text="a text").dump(), '<a tag> a text </a tag>')
        self.assertEqual(self.my_element.dump(), '<some tag an_other_key="a value" a_key="5"/>')
        self.assertEqual(self.my_other_element.dump(), '<an other tag an_other_key="a value" a_key="5">\tsome text\n\t<!--a comment-->\n\t<some tag an_other_key="a value" a_key="5"/>\n</an other tag>')

    def test_copy(self):
        # Test __copy__
        an_other_element = copy(self.my_other_element)
        self.assertTrue(isinstance(an_other_element, Element))
        self.assertEqual(an_other_element.level, self.my_other_element.level)
        self.assertEqual(an_other_element.tag, self.my_other_element.tag)
        self.assertDictEqual(an_other_element.attrib, self.my_other_element.attrib)
        self.assertEqual(an_other_element.text, self.my_other_element.text)
        self.assertEqual(an_other_element.children, self.my_other_element.children)

    def test_dump_attrib(self):
        # Test _dump_attrib
        self.assertEqual(self.my_element._dump_attrib(), 'an_other_key="a value" a_key="5"')
        self.assertEqual(self.my_element._dump_attrib(sort=True), 'a_key="5" an_other_key="a value"')

    def test_children_management(self):
        # Test append, extend, insert, remove
        my_element = Element("a tag")
        my_comment = Comment("a comment")
        my_other_element = Element("an other tag", text="my value is 5")
        self.assertEqual(len(my_element), 0)
        my_element.extend([my_comment, my_other_element])
        self.assertEqual(len(my_element), 2)
        self.assertEqual(my_element.children, [my_comment, my_other_element])
        with self.assertRaises(ValueError):
            my_element.remove(self.my_element)
        my_element.remove(my_comment)
        self.assertEqual(len(my_element), 1)
        self.assertEqual(my_element.children, [my_other_element])
        my_element.append(self.my_element)
        self.assertEqual(len(my_element), 2)
        self.assertEqual(my_element.children, [my_other_element, self.my_element])
        my_element.insert(1, my_comment)
        self.assertEqual(len(my_element), 3)
        self.assertEqual(my_element.children, [my_other_element, my_comment, self.my_element])
        self.assertTrue(my_element[0] == my_other_element)
        my_element[0] = my_comment
        self.assertTrue(my_element[0] == my_comment)
        del my_element[0]
        self.assertEqual(my_element.children, [my_comment, self.my_element])
        with self.assertRaises(TypeError):
            my_element.append("a string")
        with self.assertRaises(TypeError):
            my_element.insert(2, "a string")
        with self.assertRaises(TypeError):
            my_element.remove("a string")
        with self.assertRaises(TypeError):
            my_element.extend(["an element", my_comment, dict(a_key="a_value")])

    def test_update_level(self):
        # Test update_level
        self.assertEqual(self.my_other_element.level, 0)
        for elt in self.my_other_element.children:
            self.assertEqual(elt.level, 1)
        self.my_other_element.update_level(0)
        self.assertEqual(self.my_other_element.level, 0)
        for elt in self.my_other_element.children:
            self.assertEqual(elt.level, 1)
        self.my_other_element.update_level(5)
        self.assertEqual(self.my_other_element.level, 5)
        for elt in self.my_other_element.children:
            self.assertEqual(elt.level, 6)
        self.my_other_element.update_level(0)
        self.assertEqual(self.my_other_element.level, 0)
        for elt in self.my_other_element.children:
            self.assertEqual(elt.level, 1)

    def test_dump_children(self):
        self.assertEqual(self.my_element._dump_children(), "")
        self.assertEqual(self.my_other_element._dump_children(), '\t<!--a comment-->\n\t<some tag an_other_key="a value" a_key="5"/>')


class TestBuildDictAttrib(unittest.TestCase):

    def test_build_dict_attrib(self):
        str_1 = 'a_key = "5 " test4key="etc-7 "'
        test_1 = _build_dict_attrib(str_1)
        str_2 = ' a_key ="5" test4key="etc-7" '
        test_2 = _build_dict_attrib(str_2)
        str_3 = ' a_key= " 5 " test4key= "etc-7"'
        test_3 = _build_dict_attrib(str_3)
        test_dict = OrderedDict()
        test_dict["a_key"] = "5"
        test_dict["test4key"] = "etc-7"
        self.assertTrue(isinstance(test_1, OrderedDict))
        self.assertTrue(isinstance(test_2, OrderedDict))
        self.assertTrue(isinstance(test_3, OrderedDict))
        self.assertEqual(list(test_1), list(test_dict))
        self.assertEqual(list(test_2), list(test_dict))
        self.assertEqual(list(test_3), list(test_dict))
        self.assertDictEqual(test_1, test_dict)
        self.assertDictEqual(test_2, test_dict)
        self.assertDictEqual(test_3, test_dict)


class TestFindXMLHeader(unittest.TestCase):

    def test_several_header(self):
        str_1 = '<? xml encoding="utf-8"?> <my_beacon>a test value</my_beacon><-- a comment --><? ?><a_beacon/>'
        with self.assertRaises(Exception):
            _find_xml_header(str_1)
        with self.assertRaises(Exception):
            _find_xml_header(str_1, verbose=True)

    def test_no_header(self):
        str_1 = '<my_beacon>a test value</my_beacon> <-- a comment --><a_beacon/>'
        rep_1 = _find_xml_header(str_1)
        rep_2 = _find_xml_header(str_1, verbose=True)
        self.assertTrue(isinstance(rep_1, tuple))
        self.assertTrue(isinstance(rep_2, tuple))
        self.assertIsNone(rep_1[1])
        self.assertIsNone(rep_2[1])
        self.assertEqual(rep_1[0], str_1)
        self.assertEqual(rep_2[0], str_1)

    def test_not_beginning_header(self):
        str_1 = '<my_beacon>a test value</my_beacon><-- a comment --><? ?><a_beacon/>'
        with self.assertRaises(Exception):
            _find_xml_header(str_1, verbose=True)

    def test_correct_header(self):
        str_1 = '<? xml encoding="utf-8"?> <my_beacon>a test value</my_beacon><-- a comment --><a_beacon/>'
        str_2 = '<my_beacon>a test value</my_beacon><-- a comment --><a_beacon/>'
        rep_str, rep_header = _find_xml_header(str_1)
        self.assertEqual(rep_str, str_2)
        self.assertTrue(rep_header == Header(tag="xml", attrib=OrderedDict(encoding="utf-8")))


class TestFindXMLComment(unittest.TestCase):

    def test_comments(self):
        str_1 = '<my_beacon>a test value</my_beacon><-!- a comment --><a_beacon/>'
        str_2 = '<!-- a comment --><my_beacon>a test value</my_beacon><a_beacon/>'
        str_3 = '<!-- a comment --><!-- an other comment --><my_beacon>a test value</my_beacon><a_beacon/>'
        str_4 = '<!-- a comment --><my_beacon>a test value</my_beacon><!-- an other comment --><a_beacon/>'
        str_5 = '<beacon/>'
        a_comment = Comment("a comment")
        an_other_comment = Comment("an other comment")
        rep_str_1, rep_comment_1 = _find_xml_comment(str_1)
        self.assertEqual(rep_str_1, str_1)
        self.assertIsNone(rep_comment_1)
        rep_str_2, rep_comment_2 = _find_xml_comment(str_2)
        self.assertEqual(rep_str_2, '<my_beacon>a test value</my_beacon><a_beacon/>')
        self.assertTrue(rep_comment_2 == a_comment)
        rep_str_3, rep_comment_3 = _find_xml_comment(str_3)
        self.assertEqual(rep_str_3, '<!-- an other comment --><my_beacon>a test value</my_beacon><a_beacon/>')
        self.assertTrue(rep_comment_3 == a_comment)
        rep_str_4, rep_comment_4 = _find_xml_comment(str_4,verbose=True)
        self.assertEqual(rep_str_4, '<my_beacon>a test value</my_beacon><!-- an other comment --><a_beacon/>')
        self.assertTrue(rep_comment_4 == a_comment)
        rep_str_5, rep_comment_5 = _find_xml_comment(str_5, verbose=True)
        self.assertEqual(rep_str_5, str_5)
        self.assertIsNone(rep_comment_5)


class TestFindOnePartElement(unittest.TestCase):

    def test_no_one_element(self):
        str_1 = "<my_beacon>a test value</my_beacon>"
        rep_str_1, rep_element_1 = _find_one_part_element(str_1)
        self.assertEqual(str_1, rep_str_1)
        self.assertIsNone(rep_element_1)
        str_2 = "<!-- a comment element -->"
        rep_str_2, rep_element_2 = _find_one_part_element(str_2, verbose=True)
        self.assertEqual(str_2, rep_str_2)
        self.assertIsNone(rep_element_2)

    def test_one_part_element(self):
        str_1 = ' < an_element attr ="5" attr2="3>=2"/> <an_element /> '
        str_2 = ' <an_element />'
        test_dict = OrderedDict()
        test_dict["attr"] = "5"
        test_dict["attr2"] = "3>=2"
        rep_str_1, rep_element_1 = _find_one_part_element(str_1, verbose=True)
        self.assertEqual(rep_str_1, str_2)
        self.assertTrue(rep_element_1 == Element(tag="an_element", attrib=test_dict))
        rep_str_2, rep_element_2 = _find_one_part_element(str_2)
        self.assertEqual(rep_str_2, "")
        self.assertTrue(rep_element_2 == Element(tag="an_element"))


class TestFindInitTwoPartsElement(unittest.TestCase):

    @unittest.skipUnless(False, "Not yet implemented")
    def test_no_init_two_parts_element(self):
        pass

    @unittest.skipUnless(False, "Not yet implemented")
    def test_init_two_parts_element(self):
        pass


class TestFindText(unittest.TestCase):

    def test_find_text(self):
        str_1 = "a text "
        with self.assertRaises(Exception):
            _find_text(str_1, fatal_sep=True)
        test_1 = _find_text(str_1, verbose=True)
        self.assertEqual(test_1[1], str_1.strip())
        self.assertEqual(test_1[0], "")
        str_2 = "a text </ a beacon>"
        test_2 = _find_text(str_2, verbose=True)
        self.assertEqual(test_2[0], "</ a beacon>")
        self.assertEqual(test_2[1], "a text")
        str_3 = "a text </ a beacon"
        with self.assertRaises(Exception):
            _find_text(str_3)
        str_4 = "a text / a beacon>"
        with self.assertRaises(Exception):
            _find_text(str_4)
        str_5 = "<beacon> a text"
        test_5 = _find_text(str_5, verbose=True)
        self.assertEqual(test_5[0], "<beacon>")
        self.assertEqual(test_5[1], "a text")
        str_6 = "<beacon> a text"
        test_6 = _find_text(str_5, verbose=True)
        self.assertEqual(test_5[0], "<beacon>")
        self.assertEqual(test_5[1], "a text")
        str_7 = ">a text "
        with self.assertRaises(Exception):
            _find_text(str_7)
        test_7 = _find_text(str_7, fatal=False)
        self.assertEqual(test_7[0], str_7.strip())
        self.assertEqual(test_7[1], "")
        str_8 = "a text< "
        with self.assertRaises(Exception):
            _find_text(str_8)
        test_8 = _find_text(str_8, fatal=False)
        self.assertEqual(test_8[0], str_8.strip())
        self.assertEqual(test_8[1], "")


class TestPreTreatment(unittest.TestCase):

    @unittest.skipUnless(False, "Check why it doesn't work...")
    def test_iterate_on_characters_to_check(self):
        str_1 = "<? a header ?>< a_beacon /><!-- some comments --> some text with special ' > \" characters < < an_other_beacon> <!-- with a comment --> </ an_other_beacon >"
        test_1 = iterate_on_characters_to_check(str_1)
        rep_1 = [(0, "begin_header"), (12, "end_header"), (14, "lower_than"), (26, "greater_than"),
                 (27, "begin_comment"), (46, "end_comment"), (73, "single_quote"), (75, "greater_than"),
                 (77, "double_quote"), (90, "lower_than"), (92, "lower_than"), (109, "greater_than"),
                 (111, "begin_comment"), (131, "end_comment"), (135, "lower_than"), (154, "greater_than")]
        self.assertListEqual(list(test_1), rep_1)
        str_2 = "<? a header ?><!-- comment with  pb?> -->"
        with self.assertRaises(Exception):
            iterate_on_characters_to_check(str_2, verbose=True)
        str_3 = "<? a header ?><? an other header ?>"
        with self.assertRaises(Exception):
            iterate_on_characters_to_check(str_3, verbose=True)

    def test_iterate_on_string(self):
        str_1 = "a long \n string with several \n separator\n"
        test_1 = iterate_on_string(str_1, verbose=True)
        rep_1 = [("a long \n", 0), (" string with several \n", 8), (" separator\n", 30)]
        self.assertListEqual(list(test_1), rep_1)
        str_2 = "a long \n string with several \n separator\n "
        test_2 = iterate_on_string(str_2, verbose=True)
        rep_2 = [("a long \n", 0), (" string with several \n", 8), (" separator\n", 30), (" \n", 41)]
        self.assertListEqual(list(test_2), rep_2)

    def test_pre_xml_string_format(self):
        # TODO: add a test with a header
        str_1 = '<my_beacon>\n\n<!-- a comment element <=> -->a test value < an element attr ="><5" attr2="3>=2"/>     <a beacon>\t</a beacon>\n \t</my_beacon attr=">">'
        test_str_1 = '<my_beacon> <!-- a comment element &lt=&gt -->a test value < an element attr ="&gt&lt5" attr2="3&gt=2"/> <a beacon> </a beacon> </my_beacon attr="&gt">'
        str_2 = '<my_beacon> a test <value </my_beacon>'
        str_3 = '<my_beacon> a test "value </my_beacon>'
        str_4 = '><my_beacon> a test >value </my_beacon>'
        str_5 = '<my_beacon> a test -->value </my_beacon>'
        str_6 = '<my_beacon> a test <!--value </my_beacon>'
        str_7 = '<my_beacon> a test value </my_beacon>>'
        str_8 = '<my_beacon> a test value </my_beacon'
        str_9 = "<my_beacon attr='1<2'/>"
        str_10 = '<!-- a comment with special " \' characters -->' \
                 '<my_beacon \nattr=\'toto\' attr2="\'"> a test value \' with special character " </my_beacon>'
        str_11 = '<my_beacon> a test >value </my_beacon>'
        str_12 = "<? a_header key='value>' ?>"
        str_13 = "<? a_header key='value>' <? an other header ?> ?>"
        str_14 = "<!-- a comment <!-- in a comment --> should run out -->"
        str_15 = "<!-- a comment follow by an odd beacon--><<abecon/>"
        test_str_9 = '<my_beacon attr="1&lt2"/>'
        test_str_10 = '<!-- a comment with special " \' characters -->' \
                      '<my_beacon attr="toto" attr2="\'"> a test value \' with special character " </my_beacon>'
        test_str_11 = '<my_beacon> a test &gtvalue </my_beacon>'
        test_str_12 = "<? a_header key='value&gt' ?>"
        with self.assertRaises(TypeError):
            _pre_xml_string_format(2019, verbose=True)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_2, verbose=True)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_4, verbose=True)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_5)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_6)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_7)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_8)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_13)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_14)
        with self.assertRaises(Exception):
            _pre_xml_string_format(str_15)
        self.assertEqual(_pre_xml_string_format(str_1, verbose=True), test_str_1)
        self.assertEqual(_pre_xml_string_format(str_3, verbose=True), str_3)
        self.assertEqual(_pre_xml_string_format(str_9, verbose=True), test_str_9)
        self.assertEqual(_pre_xml_string_format(str_10, verbose=True), test_str_10)
        self.assertEqual(_pre_xml_string_format(str_11, verbose=True), test_str_11)
        self.assertEqual(_pre_xml_string_format(str_12, verbose=True), test_str_12)

    def test_replace_char_at_pos_by_string(self):
        test_string = '<my_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3>=2"/> <a beacon></a beacon> </my_beacon>'
        with self.assertRaises(Exception):
            replace_char_at_pos_by_string(test_string, "t", "test", 5, 5)
        with self.assertRaises(Exception):
            replace_char_at_pos_by_string(test_string,  "test", "more_test", 5, 9, verbose=True)
        with self.assertRaises(Exception):
            replace_char_at_pos_by_string(test_string, "t", "test", -8, -8)
        with self.assertRaises(Exception):
            replace_char_at_pos_by_string(test_string, "t", "test", 582, 582)
        test_1 = replace_char_at_pos_by_string(test_string, "<", "&gt", 0, 0)
        self.assertEqual(test_1, '&gtmy_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3>=2"/> <a beacon></a beacon> </my_beacon>')
        test_2 = replace_char_at_pos_by_string(test_string, "<my_b", "<some_test_beacons /> <my_b", 0, 5)
        self.assertEqual(test_2, '<some_test_beacons /> <my_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3>=2"/> <a beacon></a beacon> </my_beacon>')
        test_3 = replace_char_at_pos_by_string(test_string, "</a beacon> </my_beacon>", "</my_beacon>", 98, 122)
        self.assertEqual(test_3, '<my_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3>=2"/> <a beacon></my_beacon>')
        test_4 = replace_char_at_pos_by_string(test_string, "an element a", "", 52, 64)
        self.assertEqual(test_4, '<my_beacon><!-- a comment element -->a test value < ttr ="5" attr2="3>=2"/> <a beacon></a beacon> </my_beacon>')
        test_5 = replace_char_at_pos_by_string(test_string, ">", "&lt", 121, 121)
        self.assertEqual(test_5, '<my_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3>=2"/> <a beacon></a beacon> </my_beacon&lt')
        test_6 = replace_char_at_pos_by_string(test_string, ">", "&lt", 81, 81, verbose=True)
        self.assertEqual(test_6, '<my_beacon><!-- a comment element -->a test value < an element attr ="5" attr2="3&lt=2"/> <a beacon></a beacon> </my_beacon>')


class TestParser(unittest.TestCase):

    def test_find_next_element(self):
        str_1 = '<? a_header key="value" ?><!--some comments-->  '
        rep_1 = find_next_element(str_1, level=5, verbose=True)
        self.assertEqual(len(rep_1), 2)
        self.assertEqual(rep_1[0], "<!--some comments-->")
        self.assertTrue(isinstance(rep_1[1], tuple))
        self.assertEqual(len(rep_1[1]), 3)
        self.assertEqual(rep_1[1][0], 5)
        self.assertEqual(rep_1[1][1], "header")
        rep_elt_1 = Header("a_header", attrib=dict(key="value"))
        self.assertTrue(rep_1[1][2] == rep_elt_1)
        str_2 = " <!-- a comment with \" ' special characters < > --><? a header ?>"
        rep_2 = find_next_element(str_2, tag="a_tag")
        self.assertEqual(len(rep_2), 2)
        self.assertEqual(rep_2[0], "<? a header ?>")
        self.assertTrue(isinstance(rep_2[1], tuple))
        self.assertEqual(len(rep_2[1]), 3)
        self.assertEqual(rep_2[1][0], 0)
        self.assertEqual(rep_2[1][1], "comment")
        self.assertTrue(rep_2[1][2] == Comment("a comment with \" ' special characters < >"))
        str_3 = "Some text with &lt special characters &gt to be skip < a_beacon/>"
        rep_3 = find_next_element(str_3)
        self.assertEqual(len(rep_3), 2)
        self.assertEqual(rep_3[0], "< a_beacon/>")
        self.assertTrue(isinstance(rep_3[1], tuple))
        self.assertEqual(len(rep_3[1]), 3)
        self.assertEqual(rep_3[1][0], 0)
        self.assertEqual(rep_3[1][1], "text")
        self.assertEqual(rep_3[1][2], "Some text with &lt special characters &gt to be skip")
        str_4 = ' < a_beacon key1="5" key2="value2" />'
        rep_4 = find_next_element(str_4)
        self.assertEqual(len(rep_4), 2)
        self.assertEqual(rep_4[0], "")
        self.assertTrue(isinstance(rep_4[1], tuple))
        self.assertEqual(len(rep_4[1]), 3)
        self.assertEqual(rep_4[1][0], 0)
        self.assertEqual(rep_4[1][1], "single_part_element")
        rep_elt_4 = Element("a_beacon", attrib=OrderedDict(key1="5"))
        rep_elt_4.attrib["key2"] = "value2"
        self.assertTrue(rep_4[1][2] == rep_elt_4)
        str_5 = ' < a_beacon key1="5" key2="value2" >'
        rep_5 = find_next_element(str_5)
        self.assertEqual(len(rep_5), 2)
        self.assertEqual(rep_5[0], "")
        self.assertTrue(isinstance(rep_5[1], tuple))
        self.assertEqual(len(rep_5[1]), 3)
        self.assertEqual(rep_5[1][0], 0)
        self.assertEqual(rep_5[1][1], "start_two_parts_element")
        rep_elt_5 = Element("a_beacon", attrib=OrderedDict(key1="5"))
        rep_elt_5.attrib["key2"] = "value2"
        self.assertTrue(rep_5[1][2] == rep_elt_5)
        str_6 = ' </ a_beacon >'
        rep_6 = find_next_element(str_6)
        self.assertEqual(len(rep_6), 2)
        self.assertEqual(rep_6[0], str_6.strip())
        self.assertTrue(isinstance(rep_6[1], tuple))
        self.assertEqual(len(rep_6[1]), 3)
        self.assertEqual(rep_6[1][0], 0)
        self.assertIsNone(rep_6[1][1])
        self.assertIsNone(rep_6[1][2])
        rep_7 = find_next_element(str_6, level=5)
        self.assertEqual(len(rep_7), 2)
        self.assertEqual(rep_7[0], str_6.strip())
        self.assertTrue(isinstance(rep_7[1], tuple))
        self.assertEqual(len(rep_7[1]), 3)
        self.assertEqual(rep_7[1][0], 5)
        self.assertIsNone(rep_7[1][1])
        self.assertIsNone(rep_7[1][2])
        rep_8 = find_next_element(str_6, tag="a_beacon")
        self.assertEqual(len(rep_8), 2)
        self.assertEqual(rep_8[0], str_6.strip())
        self.assertTrue(isinstance(rep_8[1], tuple))
        self.assertEqual(len(rep_8[1]), 3)
        self.assertEqual(rep_8[1][0], 0)
        self.assertIsNone(rep_8[1][1])
        self.assertIsNone(rep_8[1][2])
        rep_9 = find_next_element(str_6, level=5, tag="a_beacon")
        self.assertEqual(len(rep_9), 2)
        self.assertEqual(rep_9[0], "")
        self.assertTrue(isinstance(rep_9[1], tuple))
        self.assertEqual(len(rep_9[1]), 3)
        self.assertEqual(rep_9[1][0], 4)
        self.assertEqual(rep_9[1][1], "end_two_parts_element")
        self.assertIsNone(rep_9[1][2])
        str_10 = "<!-- toto"
        rep_10 = find_next_element(str_10)
        self.assertEqual(len(rep_10), 2)
        self.assertEqual(rep_10[0], str_10)
        self.assertTrue(isinstance(rep_10[1], tuple))
        self.assertEqual(len(rep_10[1]), 3)
        self.assertEqual(rep_10[1][0], 0)
        self.assertIsNone(rep_10[1][1])
        self.assertIsNone(rep_10[1][2])
        str_11 = "<!-- tag"
        rep_11 = find_next_element(str_11, tag="a_beacon", level=6)
        self.assertEqual(len(rep_11), 2)
        self.assertEqual(rep_11[0], str_11)
        self.assertTrue(isinstance(rep_11[1], tuple))
        self.assertEqual(len(rep_11[1]), 3)
        self.assertEqual(rep_11[1][0], 6)
        self.assertIsNone(rep_11[1][1])
        self.assertIsNone(rep_11[1][2])

    def test_parse_string_rewrite(self):
        str_1 = "<? a_header ?>some introducing text<!-- a very long comment -->< a_tag> some text< an_other_beacon /></a_tag>"
        rep_text_1 = "some introducing text"
        rep_comments_1 = [Comment("a very long comment"), ]
        rep_headers_1 = Header("a_header")
        rep_root_element_1 = Element("a_tag", text="some text")
        rep_root_element_1.append(Element("an_other_beacon"))
        test_1 = parse_xml_string_rewrite(str_1, verbose=True)
        self.assertEqual(len(test_1), 4)
        self.assertEqual(test_1[0], rep_text_1)
        self.assertTrue(isinstance(test_1[1], list))
        for (test, ref) in zip(test_1[1], rep_comments_1):
            self.assertTrue(test == ref)
        self.assertTrue(test_1[2] == rep_headers_1)
        self.assertTrue(test_1[3] == rep_root_element_1)
        str_2 = "<!-- a very long comment -->"
        test_2 = parse_xml_string_rewrite(str_2)
        self.assertEqual(len(test_2), 4)
        self.assertEqual(test_2[0], "")
        for (test, ref) in zip(test_2[1], rep_comments_1):
            self.assertTrue(test == ref)
        self.assertIsNone(test_2[2])
        self.assertIsNone(test_2[3])
        str_3 = "< a_tag> some text< an_other_beacon /></a_tag>< a_third_beacon />"
        with self.assertRaises(Exception):
            parse_xml_string_rewrite(str_3)

    def test_generate_list_from_xml_string(self):
        str_1 = "<!-- a very long comment -->< a_tag> some text< an_other_beacon /></a_tag>"
        rep_1 = [(0, "comment", Comment("a very long comment")), (0, "start_two_parts_element", Element("a_tag")),
                 (1, "text", "some text"), (1, "single_part_element", Element("an_other_beacon")),
                 (0, "end_two_parts_element", None)]
        test_1 = generate_list_from_xml_string(str_1, verbose=True)
        for (test, ref) in zip(test_1, rep_1):
            self.assertTrue(test == ref)
        str_2 = "<!-- toto"
        with self.assertRaises(Exception):
            generate_list_from_xml_string(str_2)

    def test_generate_xml_tree_from_list(self):
        list_1 = [(0, "comment", Comment("a comment")), (0, "header", Header("a header")), (0, "text", "some text"),
                  (0, "single_part_element", Element("an element"))]
        test_1 = generate_xml_tree_from_list(list_1)
        self.assertTrue(isinstance(test_1[0], list))
        self.assertListEqual(test_1[0], list())
        self.assertTrue(isinstance(test_1[1], list))
        self.assertTrue(len(test_1[1]), 1)
        self.assertTrue(test_1[1][0] == Element("an element"))
        self.assertTrue(isinstance(test_1[2], list))
        self.assertTrue(len(test_1[2]), 1)
        self.assertTrue(test_1[2][0] == "some text")
        self.assertTrue(isinstance(test_1[3], list))
        self.assertTrue(len(test_1[3]), 1)
        self.assertTrue(test_1[3][0] == Comment("a comment"))
        self.assertTrue(isinstance(test_1[4], list))
        self.assertTrue(len(test_1[4]), 1)
        self.assertTrue(test_1[4][0] == Header("a header"))
        list_2 = [(1, "start_two_parts_element", Element("an element")), (1, "header", Header("a header")),
                  (0, "end_two_parts_element", None)]
        with self.assertRaises(Exception):
            generate_xml_tree_from_list(list_2, verbose=True)
        list_3 = [(0, "start_two_parts_element", Element("a double element")),
                  (1, "single_part_element", Element("an element")), (1, "comment", Comment("a comment")),
                  (1, "text", "some text"), (1, "single_part_element", Element("an other element")),
                  (0, "end_two_parts_element", None)]
        test_3 = generate_xml_tree_from_list(list_3)
        rep_3 = Element("a double element")
        rep_3.text = "some text"
        rep_3.append(Element("an element"))
        rep_3.append(Comment("a comment"))
        rep_3.append(Element("an other element"))
        self.assertTrue(isinstance(test_3[0], list))
        self.assertListEqual(test_3[0], list())
        self.assertTrue(isinstance(test_3[1], list))
        self.assertTrue(len(test_3[1]), 1)
        self.assertTrue(test_3[1][0] == rep_3)
        self.assertTrue(isinstance(test_3[2], list))
        self.assertListEqual(test_3[2], list())
        self.assertTrue(isinstance(test_3[3], list))
        self.assertListEqual(test_3[3], list())
        self.assertTrue(isinstance(test_3[4], list))
        self.assertListEqual(test_3[4], list())


if __name__ == '__main__':
    unittest.main()
