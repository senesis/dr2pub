#!/usr/bin/env python
# coding: utf-8

"""

"""

from __future__ import print_function, division, absolute_import, unicode_literals

from config import get_config_variable
from settings_interface import get_variable_from_sset_else_lset_with_default, get_variable_from_lset_with_default
from xml_interface import DR2XMLElement


class DR2XMLContext(DR2XMLElement):

    tag = "context"
    attrs_list = ["id", ]


class DR2XMLFileDefinition(DR2XMLElement):

    tag = "file_definition"
    attrs_list = ["type", "enabled"]

    def populate_attrs_default_values(self):
        super(DR2XMLFileDefinition, self).populate_attrs_default_values()
        self.attrs_default_values["type"] = "one_file"
        self.attrs_default_values["enabled"] = "true"


class DR2XMLFile(DR2XMLElement):

    tag = "file"
    attrs_list = ["id", "name", "mode", "output_freq", "enabled"]
    fatal_missing_attr = False

    def populate_attrs_default_values(self):
        super(DR2XMLFile, self).populate_attrs_default_values()
        self.attrs_default_values["mode"] = "read"


class DR2XMLOutputFile(DR2XMLFile):

    attrs_list = ["id", "name", "output_freq", "append", "output_level", "compression_level", "split_freq",
                  "split_freq_format", "split_start_offset", "split_end_offset", "split_last_date", "time_units",
                  "time_counter_name", "time_counter", "time_stamp_name", "time_stamp_format", "uuid_name",
                  "uuid_format", "convention_str"]

    def populate_attrs_default_values(self):
        super(DR2XMLOutputFile, self).populate_attrs_default_values()
        self.attrs_default_values["append"] = "true"
        self.attrs_default_values["output_level"] = str(get_variable_from_lset_with_default("output_level", 10))
        self.attrs_default_values["compression_level"] = str(get_variable_from_lset_with_default("compression_level", 0))
        self.attrs_default_values["time_units"] = "days"
        self.attrs_default_values["time_counter_name"] = "time"
        self.attrs_default_values["time_counter"] = "exclusive"
        self.attrs_default_values["time_stamp_name"] = "creation_date"
        self.attrs_default_values["time_stamp_format"] = "%Y-%m-%dT%H:%M:%SZ"
        self.attrs_default_values["uuid_name"] = "tracking_id"
        self.attrs_default_values["uuid_format"] = "hdl:{}/%uuid%".format(get_variable_from_sset_else_lset_with_default("HDL", "21.14100"))
        self.attrs_default_values["convention_str"] = get_config_variable("conventions")

    def populate_attrs_skip_values(self):
        super(DR2XMLOutputFile, self).populate_attrs_skip_values()
        self.attrs_skip_values["split_start_offset"] = [False, ]
        self.attrs_skip_values["split_end_offset"] = [False, ]


class DR2XMLFieldDefinition(DR2XMLElement):

    tag = "field_definition"


class DR2XMLFieldGroup(DR2XMLElement):

    tag = "field_group"
    attrs_list = ["freq_op", "frq_offset"]

    def populate_attrs_default_values(self):
        super(DR2XMLFieldGroup, self).populate_attrs_default_values()
        self.attrs_default_values["freq_op"] = "_reset_"
        self.attrs_default_values["freq_offset"] = "_reset_"


class DR2XMLField(DR2XMLElement):

    tag = "field"
    attrs_list = ["id", "name", "long_name", "standard_name", "unit", "grid_ref", "field_ref", "operation", "freq_op",
                  "freq_offset", "detect_missing_value", "default_value", "prec", "cell_methods", "cell_methods_mode",
                  "expr"]
    fatal_missing_attr = False

    # def populate_attrs_default_values(self):
    #     super(DR2XMLField, self).populate_attrs_default_values()
    #     self.attrs_default_values["operation"] = "instant"

    def populate_attrs_skip_values(self):
        super(DR2XMLField, self).populate_attrs_skip_values()
        self.attrs_skip_values["grid_ref"] = ["native", None]
        self.attrs_skip_values["freq_offset"] = [None, ]
        self.attrs_skip_values["freq_op"] = [None, ]
        self.attrs_skip_values["expr"] = [None, ]


class DR2XMLAxisDefinition(DR2XMLElement):

    tag = "axis_definition"


class DR2XMLAxisGroup(DR2XMLElement):

    tag = "axis_group"
    attrs_list = ["prec", ]

    def populate_attrs_default_values(self):
        super(DR2XMLAxisGroup, self).populate_attrs_default_values()
        self.attrs_default_values["prec"] = "8"


class DR2XMLAxis(DR2XMLElement):

    tag = "axis"
    attrs_list = ["id", "name", "axis_ref", "standard_name", "long_name", "prec", "unit", "positive", "n_glo", "value",
                  "bounds", "dim_name", "label", "axis_type"]
    fatal_missing_attr = False

    def populate_attrs_skip_values(self):
        super(DR2XMLAxis, self).populate_attrs_skip_values()
        self.attrs_skip_values["positive"] = [None, ""]
        self.attrs_skip_values["axis_type"] = [None, ""]
        self.attrs_skip_values["standard_name"] = [None, ]
        self.attrs_skip_values["prec"] = [None, ]
        self.attrs_skip_values["unit"] = ["", ]
        self.attrs_skip_values["value"] = [None, ]
        self.attrs_skip_values["bounds"] = [None, ]
        self.attrs_skip_values["dim_name"] = [None, ]
        self.attrs_skip_values["label"] = [None, ]


class DR2XMLTemporalSplitting(DR2XMLElement):

    tag = "temporal_splitting"


class DR2XMLInterpolateAxis(DR2XMLElement):

    tag = "interpolate_axis"
    attrs_list = ["type", "order", "coordinate"]


class DR2XMLZoomAxis(DR2XMLElement):
    tag = "zoom_axis"
    attrs_list = ["index", ]


class DR2XMLDomainDefinition(DR2XMLElement):

    tag = "domain_definition"


class DR2XMLDomainGroup(DR2XMLElement):

    tag = "domain_group"
    attrs_list = ["prec", ]

    def populate_attrs_default_values(self):
        super(DR2XMLDomainGroup, self).populate_attrs_default_values()
        self.attrs_default_values["prec"] = "8"


class DR2XMLDomain(DR2XMLElement):

    tag = "domain"
    attrs_list = ["id", "ni_glo", "nj_glo", "type", "prec", 'domain_ref', "lat_name", "lon_name", "dim_i_name"]
    fatal_missing_attr = False


class DR2XMLInterpolateDomain(DR2XMLElement):

    tag = "interpolate_domain"
    attrs_list = ["order", "renormalize", "mode", "write_weight"]


class DR2XMLGenerateRectilinearDomain(DR2XMLElement):

    tag = "generate_rectilinear_domain"


class DR2XMLGridDefinition(DR2XMLElement):

    tag = "grid_definition"


class DR2XMLGrid(DR2XMLElement):

    tag = "grid"
    attrs_list = ["id", ]


class DR2XMLScalarDefinition(DR2XMLElement):

    tag = "scalar_definition"


class DR2XMLScalar(DR2XMLElement):

    tag = "scalar"
    attrs_list = ["id", "scalar_ref", "name", "standard_name", "long_name", "label", "prec", "value", "bounds",
                  "bounds_name", "axis_type", "positive", "unit"]
    fatal_missing_attr = False

    def populate_attrs_skip_values(self):
        super(DR2XMLScalar, self).populate_attrs_skip_values()
        self.attrs_skip_values["standard_name"] = [None, ]
        self.attrs_skip_values["label"] = [None, ]
        self.attrs_skip_values["prec"] = [None, ]
        self.attrs_skip_values["value"] = [None, ]
        self.attrs_skip_values["bounds"] = [None, ]
        self.attrs_skip_values["bounds_name"] = [None, ]
        self.attrs_skip_values["axis_type"] = [None, ]
        self.attrs_skip_values["positive"] = [None, ]
        self.attrs_skip_values["unit"] = [None, ""]


class DR2XMLVariable(DR2XMLElement):

    tag = "variable"
    attrs_list = ["name", "type"]
