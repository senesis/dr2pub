#!/usr/bin/env python
# coding: utf-8

"""
Whats' necessary for reading XIOS xml file and process attribute's inheritance for
being able to request the grid_ref for any valid XIOS 'field' object

Main useful functions :
  <opaque>    context = init_context(context_name,printout=False)
  <ET object>    grid = id2grid(field_id,context,printout=False)
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict

import os
import os.path
import sys
import six

# Interface to xml tools
from xml_interface import get_root_of_xml_file, is_xml_element_to_parse

# Logger
from logger import get_logger


# Define for each object kind those attributes useful for grid inheritance
attributes = OrderedDict()
attributes['field'] = ['grid_ref', 'field_ref']
attributes['field_definition'] = attributes['field']
attributes['field_group'] = attributes['field']
attributes['grid'] = ['axis_ref', 'domain_ref', 'grid_ref']
attributes['grid_group'] = attributes['grid']
attributes['context'] = []
attributes['axis'] = ['axis_ref']


# attributes['axis_definition'] = []  # attributes['domain_definition'] = []
# attributes['grid_definition'] = []  # attributes['calendar'] = []


def read_src(elt, path_parse, level=0, dont_read=list()):
    """
    Recursively reads the subfiles indicated by tag 'src' in childs of ELT
    """
    logger = get_logger()
    nb_remove_child = 0
    for i in range(len(elt)):
        child = elt[i - nb_remove_child]
        if not is_xml_element_to_parse(child):
            elt.remove(child)
            nb_remove_child += 1
        elif 'src' in child.attrib:
            src = child.attrib['src']
            if not src.startswith(os.path.sep) and path_parse not in ["./", ]:
                filen = os.path.sep.join([path_parse, src])
            else:
                filen = src
            if not any([os.path.basename(filen).startswith(prefix) for prefix in dont_read]):
                logger.debug(level * "\t" + "Reading %s" % filen)
                et = get_root_of_xml_file(filen)
                logger.debug(level * "\t" + "Reading %s, %s=%s" % (filen, et.tag, gattrib(et, 'id', 'no_id')))
                for el in [el for el in et if getattr(el, "tag", None) is not None]:
                    # Skip comments and header
                    logger.debug((level + 1) * "\t" + "Storing %s in %s id=%s" % (el.tag, child.tag,
                                                                                  gattrib(child, 'id', 'no_id')))
                    child.append(el)
            elt.replace(i - nb_remove_child, read_src(child, path_parse, level + 1, dont_read))
        else:
            elt.replace(i - nb_remove_child, read_src(child, path_parse, level + 1, dont_read))
    return elt


def gattrib(e, attrib_name, default=None):
    """
    Get the value of an attribute of an element.
    :param e: xml element
    :param attrib_name: name of the attribute
    :param default: default value if attribute is missing
    :return: the value of the attribute or default
    """
    if attrib_name in e.attrib:
        return e.attrib[attrib_name]
    else:
        return default


def merge_sons(elt, level=0):
    """
    Merge all mergeable childs of  ELT based on tag, or
    on tag+id when tag is 'context' or 'field' or '..._group'
    """
    logger = get_logger()
    # Using a dict with first instance of an elt for each tag (or tag+id)
    bytag = OrderedDict()
    tags_to_merge = ['context', 'file_definition', 'field_definition',
                     'axis_definition', 'grid_definition', 'calendar', 'field',
                     'field_group', 'file_group']
    nb_child_remove = 0
    for i in range(len(elt)):
        child = elt[i - nb_child_remove]
        if child.tag in tags_to_merge:
            if child.tag not in ['context', 'field'] and '_group' not in child.tag:
                tag = child.tag
            elif 'id' in child.attrib:
                tag = child.tag + "_" + child.attrib['id']
            else:
                # do not merge attributes for anonymous fields
                logger.debug(level * "\t" + "%s %s" % (child.tag, child.attrib.get('id', 'no_id')))
                elt.replace(i - nb_child_remove, merge_sons(child, level + 1))
                continue
            if tag not in bytag:
                bytag[tag] = child
                logger.debug(level * "\t" + "%s %s" % (child.tag, child.attrib.get('id', 'no_id')))
                elt.replace(i - nb_child_remove, merge_sons(child, level + 1))
            elif child != bytag[tag]:
                if 'src' in child.attrib:
                    name = child.attrib['src']
                else:
                    if 'id' in child.attrib:
                        name = child.attrib['id']
                    else:
                        name = 'no_id'
                logger.debug(level * "\t" + "Moving %s %s content to %s" % (child.tag, name, tag))
                #
                # Move childs from secondary entry to first entry (brother)
                for sub in child:
                    bytag[tag].append(sub)
                # Update attributes, too
                for a in child.attrib:
                    bytag[tag].attrib[a] = child.attrib[a]
                logger.debug("removing one %s child : %s" % (elt.tag, child.tag))
                elt.remove(child)
                nb_child_remove += 1
        else:
            logger.debug(level * "\t" + "%s %s" % (child.tag, child.attrib.get('id', 'no_id')))
            elt.replace(i - nb_child_remove, merge_sons(child, level + 1))
    return elt


def solve_downward(attrib, elt, value=None, level=0):
    """ propagate attribute ATTRIB 's VALUE downward of ELT,
    setting recursively it for all childs to the parent value or
    to the value encountered in an intermediate node
    """
    logger = get_logger()
    for i in range(len(elt)):
        child = elt[i]
        value_down = value
        logger.debug(level * "\t" + " solving on " + repr(child),)
        if attrib in attributes.get(child.tag, list()):
            if attrib in child.attrib:
                value_down = child.attrib[attrib]
                logger.debug(" get :" + value_down)
            elif attrib not in child.attrib and value is not None:
                child.attrib[attrib] = value
                logger.debug(" set :" + value)
            else:
                logger.debug(" pass")
        else:
            logger.debug("")
        elt.replace(i, solve_downward(attrib, child, value_down, level + 1))
    return elt


def make_index(elt, index=None, level=0):
    """
    Create an index of all elements having an id in ELT childs recursively
    and complement attributes and children of these indexed objects when
    crossing their id multiple times
    """
    logger = get_logger()
    if index is None:
        index = OrderedDict()
    for child in [child for child in elt if "id" in child.attrib]:
        the_id = child.attrib['id']
        logger.debug(level * "\t" + " indexing " + the_id,)
        if the_id in index:
            logger.debug(" (merging)")
            # Update indexed object with current attributes
            index[the_id].attrib.update(child.attrib)
            # Add child chidlren to indexed objects
            index[the_id].extend(child[:])
        else:
            logger.debug(" init index")
            index[the_id] = child
    for child in elt:
        make_index(child, index, level + 1)
    return index


def attrib_by_ref(elt, attrib, index, level):
    """
        Provide ATTRIB value for ELT' id using its references
        and objects's dict INDEX
    """
    logger = get_logger()
    for a in [att for att in elt.attrib if "_ref" in att]:
        refid = elt.attrib[a]
        logger.debug("\n" + (level + 1) * "\t" + a + " -> " + refid,)
        try:
            ref = index[refid]
            if attrib in ref.attrib:
                rep = ref.attrib[attrib]
            else:
                rep = attrib_by_ref(ref, attrib, index, level + 1)
            logger.debug(" ---> !! GOT : %s !!!" % rep)
            if rep:
                return rep
        except:
            if not refid.startswith("dummy_"):
                raise XparseError("Error : reference '%s' is invalid" % refid)


def solve_by_ref(attrib, index, elt, level=0):
    """
    Solve remainig attributes by ref, otherwise by default value
    """
    logger = get_logger()
    got_one = 0
    for child in [child for child in elt if not isinstance(child, six.string_types) and
                                            child.tag not in ["variable", None]]:
        if 'id' in child.attrib:
            name = child.attrib['id']
        else:
            name = child.tag
        logger.debug(level * "\t" + attrib + " by_ref on  " + name,)
        #
        if not(child.tag in attributes and attrib in attributes[child.tag]):
            logger.debug(" : N/A")
        else:
            if attrib in child.attrib:
                logger.debug(", already set : %s" % child.attrib[attrib])
            else:
                byref = attrib_by_ref(child, attrib, index, level)
                if byref:
                    # if printout : print ", setting byref to "+byref,
                    child.attrib[attrib] = byref
                    got_one += 1
                else:
                    logger.debug("")
            got_one += solve_by_ref(attrib, index, child, level + 1)
    return got_one


def select_context(rootel, context_id):
    """
    Find the context corresponding to context_id
    :param rootel: root of xml element
    :param context_id: id of the context to find
    :return: context corresponding to context_id in rootel
    """
    for context in rootel:
        if 'id' in context.attrib and context.attrib['id'] == context_id:
            return context


def init_context(context_id, path_parse="./"):
    """
    Create the index for xml elements
    :param context_id: id of the context of the index
    :param path_parse: directory of the xml iodef
    :param printout: boolean to active verbose log
    :return: the index of the context
    """
    logger = get_logger()
    xmldef = path_parse + "iodef.xml"
    logger.debug("Parsing %s ..." % xmldef,)
    rootel = get_root_of_xml_file(xmldef)
    logger.debug("sourcing files  ...",)
    rootel = read_src(rootel, path_parse, dont_read=["dr2xml_"])
    rootel = merge_sons(rootel)
    rootel = select_context(rootel, context_id)
    if rootel is not None:
        refs = ["grid_ref", "domain_ref", "axis_ref", "field_ref"]
        for ref in refs:
            rootel = solve_downward(ref, rootel, None)
        # ET.dump(rootel)
        index = make_index(rootel, None)
        for ref in refs:
            while True:
                n = solve_by_ref(ref, index, rootel)
                logger.debug("%d refs solved" % n)
                if n == 0:
                    break
        # ET.dump(rootel)
        return index
    else:
        logger.warning("Xparse::init_context : context %s not found in %s" % (context_id, xmldef))


def id2gridid(field_id, index):
    """
    Call to id2grid and get "id" parameter
    :param field_id: id of the field
    :param index: index of the xml elements
    :param printout: boolean to active verbose log
    :return: the id of the grid corresponding to the entry parameters.
    """
    grid = id2grid(field_id, index)
    return grid.attrib['id']


def id2grid(field_id, index):
    """
    Returns the list of Element composing the grid of a field
    """
    logger = get_logger()
    if field_id in index:
        attrib = index[field_id].attrib
        if 'grid_ref' in attrib:
            grid_ref_field_id = attrib['grid_ref']
            if grid_ref_field_id in index:
                logger.debug("grid_ref value for %s is %s" % (grid_ref_field_id, repr(index[grid_ref_field_id])))
                return index[grid_ref_field_id]
            else:
                # if printout: print("field %s grid reference is %s
                # but that field has no grid"%(field_id,grid_ref_field_id))
                raise XparseError(
                    "field %s grid reference is %s but that field no grid" % (field_id, grid_ref_field_id))
        else:
            # if printout: print("field %s has no grid_ref"%(field_id))
            raise XparseError("field %s has no grid_ref" % field_id)
    else:
        # if printout: print("field %s is not known"%field_id)
        raise XparseError("field %s is not known" % field_id)


def id_has_expr_with_at(field_id, index):
    """
    Returns True if field has an expr attribute with includes an @
    """
    logger = get_logger()
    if field_id in index:
        attrib = index[field_id].attrib
        if 'expr' in attrib:
            logger.debug("In withAt, for %s, expr=%s" % (field_id, attrib['expr']))
            return '@' in attrib['expr']
        else:
            # if printout : print "In withAt, for %s, no expr"%(field_id)
            return False
    else:
        return False
        # raise Xparse_error("field %s is not known"%field_id)


if False:

    nemo = init_context('nemo', "./", False)
    # print list(nemo)
    grid = id2grid("CMIP6_O18sw", nemo, True)
    print(grid.attrib['id'])
    print()

    arpsfx = init_context('arpsfx', "./", False)
    grid = id2grid("CMIP6_cdnc", arpsfx, True)
    # grid=None
    if grid is not None:
        # print "Grid id is :"+grid.attrib['id']
        print(create_string_from_xml_element(grid))
        grid_string = create_string_from_xml_element(grid)
        new_grid_string = re.sub(r'axis_ref= *.([\w_])*.', 'axis_ref="axis_autre"', grid_string)
        print(new_grid_string)


class XparseError(Exception):
    """
    Xparse exceptions class.
    """

    def __init__(self, valeur):
        self.valeur = valeur

    def __str__(self):
        logger = get_logger()
        logger.error(self.valeur)
        return repr(self.valeur)
