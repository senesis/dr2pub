DR2XML key features
===================

Dr2xml is a Python package for translating the CMIP6 Data Request to XIOS file_def XML files. It also
produces complementary field_def and axis_def XML files [-not yet available-]; these will
complement hand-written XML files: the native field_def of the model and what we call, in dr2xml
jargon, the “ping file”.

Dr2xml generates one file_def XML file per XIOS context (i.e. per realm or group of realms). That
file_def sets the file structure and name in conformance with the Data Reference Syntax (DRS, see
the WIP position paper: https://drive.google.com/file/d/0B-X2uY_FGt7XNWI2TzBsUXdCVkE/view ),
includes the global attributes (metadata about the experiment, the model, the producing laboratory,
etc.) and local attributes (metadata about the output CMOR variables) imposed by CMOR. Temporal
and spatial operations consistent with the specified DR cell_methods, to be performed on the
instantaneous and global variables of the native field_def, are automatically coded by dr2xml with
appropriate XIOS filters in a complementary field_def [-not yet available-], possibly referring to
complementary axis_def [-not yet available-].

Complementary field_def files aggregate XIOS temporal and spatial operations required to produce
CMOR Variables from model outputs (for e.g.: axis reduction to compute zonal means, temporal
averages for global indices computation).

The ping file establishes the correspondence between model variable names listed in the native
model field_def and the variables names referenced in the file_def produced by dr2xml (dr2xml being
agnostic of the native model variable names, this ping file represents the interface between model
and dr2xml). Given the long list of variables requested by the DR, a tool, provided along with dr2xml
sources, enables to generate a template for an exhaustive ping file. The “only” modeller work is to
scan each line of this skeleton and associate (when it exists) a native model variable name to each of
the expected output variable. This work is to be done once for all, once the Data Request is stabilized
(see section 4 for details).

Dr2xml also offers two functionalities allowing the user to deviate/modulate the variable list that
comes from the official Data Request, giving the possibility to the user to define:

- a list of excluded variables: among the DR variables list, these ones will be excluded from
  the resulting file_def (because they do not apply to the model or for any good reason the
  modeller decide not to output them); an alternate way to exclude variables is through ping
  file syntax (see section 4 - not yet implemented)
- a list of home variables: a list of variables that the lab intends to produce in some case. This
  covers both purely “home” variables (i.e. which have no CMOR equivalent), and CMOR
  Variables that are not requested by the DR for this MIP/experiment but the lab decides to
  output anyway; these ones will be added in the file_def.

Excluded-variables usage is described in section 2; home-variables list functionality is described in
section 3.