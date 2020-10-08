:mod:`element` --- xml_writer element definition
================================================

.. automodule:: xml_writer.element
   :synopsis: Element definition for xml_writer

.. moduleauthor:: The dr2xml Team
.. sectionauthor:: The dr2xml Team
.. versionadded:: 1.0



.. autoclass:: xml_writer.element.Element

    .. py:classmethod:: __init__

    .. py:classmethod:: __str__

    .. py:classmethod:: __repr__

    .. py:classmethod:: __len__

    .. py:classmethod:: __eq__

    .. py:classmethod:: __copy__

    .. py:classmethod:: __getitem__

    .. py:classmethod:: __setitem__

    .. py:classmethod:: __delitem__

    .. py:classmethod:: copy

    .. py:classmethod:: dump

    .. py:classmethod:: correct_attrib

    .. py:classmethod:: dump_dict

    .. py:classmethod:: update_level

    .. py:classmethod:: _test_dict_equality

    .. py:classmethod::_test_attribute_equality

    .. py:classmethod:: _dump_attrib

    .. py:classmethod:: set_text

    .. py:classmethod:: append

    .. py:classmethod:: extend

    .. py:classmethod:: insert

    .. py:classmethod:: remove

    .. py:classmethod:: update_level

    .. py:classmethod:: _dump_children


.. autodata:: _xml_single_part_element_regexp

.. autofunction:: _find_one_part_element

.. autodata:: _xml_string_first_element_replace

.. autodata:: _xml_string_init_element_replace

.. autodate:: _xml_init_two_parts_element_regexp

.. autodata:: _xml_string_end_element_replace

.. autofunction:: _find_two_parts_element_init

.. autofunction:: _find_two_parts_element_end

.. autofunction:: is_xml_element
