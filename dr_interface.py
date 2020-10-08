#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface between the CMIP6 Data Request and dr2xml.
# See documentation at: https://c6dreq.dkrz.de/DreqPy_Intro.html
"""

from __future__ import print_function, division, absolute_import, unicode_literals

try:
    import dreq
except ImportError:
    from dreqPy import dreq

try:
    from scope import dreqQuery
except ImportError:
    from dreqPy.scope import dreqQuery


dq = dreq.loadDreq()
print_DR_errors = True
print_DR_stdname_errors = False


def get_uid(id=None):
    """
    Get the uid of an element if precised, else the list of all elements.
    """
    if id is None:
        return dq.inx.uid
    else:
        return dq.inx.uid[id]


def get_request_by_id_by_sect(id, request):
    """
    Get the attribute request of the element id.
    """
    return dq.inx.iref_by_sect[id].a[request]


def get_experiment_label(experiment):
    """
    Get the experiment from its label.
    """
    return dq.inx.experiment.label[experiment][0]


def get_collection(collection):
    """
    Get the collection corresponding to the collection id.
    """
    return dq.coll[collection]


def get_cmor_var_id_by_label(label):
    """
    Get the id of the CMOR var corresponding to label.
    """
    return dq.inx.CMORvar.label[label]


def initialize_sc(tier_max):
    """
    Initialize module sc variable
    """
    return dreqQuery(dq=dq, tierMax=tier_max)


def get_DR_version():
    """
    Get the version of the DR
    """
    return dq.version
