Parameters available in settings
================================

Legend
------

Requirements
^^^^^^^^^^^^
..  glossary::

    always required
    required when relevant
    never required
    never required but recommended

Parameter type
^^^^^^^^^^^^^^
..  glossary::

    string
    dictionary
    integer
    list
    boolean
    regexp

Location
^^^^^^^^
..  glossary::

    lab_and_model_settings
    simulation_settings

Available parameters
--------------------

..  glossary::
    :sorted:

    institution_id
        [:term:`string`, :term:`always required`, :term:`lab_and_model_settings`]

        Institution identifier.

        .. todo::

            Should be read from Controlled Vocabulary if up-to-date.

    source_types
        [:term:`dictionary`, :term:`always required`, :term:`lab_and_model_settings`]

        A dictionary in which keys are models and values the associated :term:`source_type`.

        .. todo::

            Should be read from Controlled Vocabulary if up-to-date.

    configurations
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary in which keys are configurations and values the associated triplet
        (:term:`model_id`, :term:`source_type`, :term:`unused_contexts`).

    references
        [:term:`string`, :term:`never required`, :term:`lab_and_model_settings`]

        Paper or web based document that describes the data or the way to produce them.

    info_url
        [:term:`string`, :term:`lab_and_model_settings`]

        Location of documentation.

    contact
        [:term:`string`, :term:`never required`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        Email address of the data producer.

    mips
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary in which keys are grid and values a set of strings corresponding to MIPs names.

    comment
        [:term:`string`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        A character string containing additional information about the models.
        Will be complemented with the experiment's specific comment string.

    max_priority
        [:term:`integer`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        Max variable priority level to be output (you may set 3 when creating ping_files while
        being more restrictive at run time).

    tierMax
        [:term:`integer`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        Number indicating the maximum tier to consider for experiments.

    ping_variables_prefix
        [:term:`string`, :term:`lab_and_model_settings`]

        The tag used to prefix the variables in the ‘field id’ namespaces of the ping file;
        may be an empty string.

    excluded_vars
        [:term:`list`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        List of CMOR variables to exclude from the result based on previous Data Request extraction.

    special_timestep_vars
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        This variable is used when some variables are computed with a period which is not the basic timestep.
        A dictionary which keys are non standard timestep and values the list of variables
        which are computed at this timestep.

    excluded_pairs
        [:term:`list`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        You can exclude some (variable, table) pairs from outputs.
        A list of tuple (variable, table) to be exlcuded.

    included_pairs
        [:term:`list`, :term:`lab_and_model_settings`]

        List of the (variable, table) pairs that must be included in outputs.
        This has precedence over :term:`excluded_vars` and :term:`excluded_vars_per_config`

    excluded_vars_per_config
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary which keys are configurations and values the list of variables
        that must be excluded for each configuration.

    excluded_spshapes
        [:term:`list`, :term:`lab_and_model_settings`]

        The list of shapes that should be excluded (all variables in those shapes will be excluded from outputs).

    included_tables
        [:term:`list`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        List of tables that will be processed (all others will not).

    excluded_tables
        [:term:`list`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        List of the tables that will be excluded from outputs.

    excluded_request_links
        [:term:`list`, :term:`lab_and_model_settings`]

        List of links un data request that should not been followed (those request are not taken into account).

    included_request_links
        [:term:`list`, :term:`lab_and_model_settings`]

        List of the request links that will be processed (all others will not).

    listof_home_vars
        [:term:`string`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        Full path to the file which contains the list of home variables to be taken into account,
        in addition to the Data Request.

    path_extra_tables
        [:term:`string`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        Full path of the directory which contains extra tables.

    realms_per_context
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary which keys are context names and values the lists of realms associated with each context

    orphan_variables
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary with (context name, list of variables) as (key,value) pairs,
        where the list indicates the variables to be re-affected to the key-context
        (initially affected to a realm falling in another context)

    comments
        [:term:`dictionary`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        A dictionary which keys are CMOR variable names and values a free comment the user wants to associate
        to the key variable

    grid_choice
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary which keys are models name and values the corresponding resolution.

    filter_on_realization
        [:term:`boolean`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        If you want to produce the same variables set for all members, set this parameter to False.

    sizes
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        A dictionary which keys are resolution and values the associated grid size for atmosphere and ocean grids.
        The grid size looks like : ['nho', 'nlo', 'nha', 'nla', 'nlas', 'nls', 'nh1'].
        Used to compute file split frequency.

    max_split_freq
        [:term:`integer`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        The maximum number of years that should be putted in a single file.

    max_file_size_in_floats
        [:term:`integer`, :term:`lab_and_model_settings`]

        The maximum size of generated files in number of floating values.

    compression_level
        [:term:`integer`, :term:`lab_and_model_settings`]

        The compression level to be applied to NetCDF output files.

    bytes_per_float
        [:term:`integer`, :term:`lab_and_model_settings`]

        Estimate of number of bytes per floating value, given the chosen :term:`compression_level`.

    grid_policy
        [:term:`string`, :term:`lab_and_model_settings`, allowed=None, "DR", "native", "native+DR", "adhoc"]

        The grid choice policy for output files.

    grids
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        Grids : per model resolution and per context :
            - CMIP6 qualifier (i.e. 'gn' or 'gr') for the main grid chosen (because you
              may choose has main production grid a regular one, when the native grid is e.g. unstructured)
            - Xios id for the production grid (if it is not the native grid),
            - Xios id for the latitude axis used for zonal means (mist match latitudes for grid above)
            - resolution of the production grid (using CMIP6 conventions),
            - grid description

    sampling_timestep
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        Basic sampling timestep set in your field definition (used to feed metadata 'interval_operation').
        Should be a dictionary which keys are resolutions and values a context/timestep dictionary.

    CFsubhr_frequency
        [:term:`string`, :term:`lab_and_model_settings`]

        CFMIP has an elaborated requirement for defining subhr frequency; by default, dr2xml uses 1 time step.

    vertical_interpolation_sample_freq
        [:term:`string`, :term:`lab_and_model_settings`]

        Time frequency of vertical interpolation.

    vertical_interpolation_operation
        [:term:`string`, :term:`lab_and_model_settings`]

        Operation done for vertical interpolation.

    use_union_zoom
        [:term:`boolean`, :term:`lab_and_model_settings`]

        Say if you want to use XIOS union/zoom axis to optimize vertical interpolation requested by the DR.

    too_long_periods
        [:term:`list`, :term:`lab_and_model_settings`]

        The CMIP6 frequencies that are unreachable for a single model run. Datafiles will
        be labelled with dates consistent with content (but not with CMIP6 requirements).
        Allowed values are only 'dec' and 'yr'.

    branching
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        Describe the branching scheme for experiments involved in some 'branchedYears type' tslice
        (for details, see: http://clipc-services.ceda.ac.uk/dreq/index/Slice.html ).
        Just put the as key the common start year in child and as value the list of start years in parent
        for all members.
        A dictionary with models name as key and dictionary containing experiment,
        (branch year in child, list of branch year in parent) key values.

    output_level
        [:term:`integer`, :term:`lab_and_model_settings`]

        We can control the max output level set for all output files.

    print_variables
        [:term:`boolean` or :term:`list`, :term:`lab_and_model_settings`]

        If the value is a list, only the file/field variables listed here will be put in output files.
        If boolean, tell if the file/field variables should be put in output files.

    nemo_sources_management_policy_master_of_the_world
        [:term:`boolean`, :term:`lab_and_model_settings`]

        Set that to True if you use a context named 'nemo' and the corresponding model unduly sets
        a general freq_op AT THE FIELD_DEFINITION GROUP LEVEL. Due to Xios rules for inheritance,
        that behavior prevents inheriting specific freq_ops by reference from dr2xml generated field_definitions.

    non_standard_attributes
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        You may add a series of NetCDF attributes in all files for this simulation

    simple_domain_grid_regexp
        [:term:`regexp`, :term:`lab_and_model_settings`]

        If some grid is not defined in xml but by API, and is referenced by a
        field which is considered by the DR as having a singleton dimension, then:

            1) it must be a grid which has only a domain
            2) the domain name must be extractable from the grid_id using a regexp and a group number

        Example: using a pattern that returns full id except for a '_grid' suffix

    non_standard_axes
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        If your model has some axis which does not have all its attributes as in DR, and you want dr2xml to fix that
        it, give here the correspondence from model axis id to DR dim/grid id. For label dimensions you should provide
        the  list of labels, ordered as in your model, as second element of a pair.
        Label-type axes will be processed even if not quoted.
        Scalar dimensions are not concerned by this feature.

        A dictionary with (axis_id, axis_correct_id) or (axis_id, tuple of labels) as key, values.

    dr2xml_manages_enddate
        [:term:`boolean`, :term:`lab_and_model_settings`, default=True]

        A smart workflow will allow you to extend a simulation during it course and to complement the output files
        accordingly, by managing the 'end date' part in filenames.
        You can then set next setting to False.

    fx_from_file
        [:term:`dictionary`, :term:`lab_and_model_settings`]

        You may provide some variables already horizontally remapped to some grid (i.e. Xios domain) in external files.
        The varname in file must match the referenced id in pingfile. Tested only for fixed fields.

        A dictionary with variable id as key and a dictionary as value:
        the key must be the grid id, the value a dictionary with the file for each resolution.

    path_to_parse
        [:term:`string`, :term:`lab_and_model_settings`]

        The path of the directory which, at run time, contains the root XML file (iodef.xml).

    allow_duplicates
        [:term:`boolean`, :term:`lab_and_model_settings`, default=True]

        Should we allow for duplicate vars: two vars with same frequency, shape and realm, which differ only by the
        table. In DR01.00.21, this actually applies to very few fields (ps-Aermon, tas-ImonAnt, areacellg-IfxAnt).

    allow_duplicates_in_same_table
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        Should we allow for another type of duplicate vars : two vars with same name in same table
        (usually with different shapes). This applies to e.g. CMOR vars 'ua' and 'ua7h' in
        6hPlevPt. Default to False, because CMIP6 rules does not allow to name output files differently in that case.
        If set to True, you should also set 'use_cmorvar_label_in_filename' to True to overcome the said rule.

    use_cmorvar_label_in_filename
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        CMIP6 rule is that filenames includes the variable label, and that this variable label is not the CMORvar
        label, but 'MIPvar' label. This may lead to conflicts, e.g. for 'ua' and 'ua7h' in table 6hPlevPt;
        allows to avoid that, if set to True.

    add_Gibraltar
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        DR01.00.21 does not include Gibraltar strait, which is requested by OMIP.
        Can include it, if model provides it as last value of array.

    debug_parsing
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        In order to identify which xml files generates a problem, you can use this flag.

    allow_pseudo_standard_names
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        DR has sn attributes for MIP variables. They can be real,CF-compliant, standard_names or pseudo_standard_names,
        i.e. not yet approved labels. Default is to use only CF ones.

    print_stats_per_var_label
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        For an extended printout of selected CMOR variables, grouped by variable label.

    allow_tos_3hr_1deg
        [:term:`boolean`, :term:`lab_and_model_settings`, default=True]

        When using select='no', Xios may enter an endless loop, which is solved if next setting is False.

    adhoc_policy_do_add_1deg_grid_for_tos
        [:term:`boolean`, :term:`lab_and_model_settings`, default=False]

        Some scenario experiment in DR 01.00.21 do not request tos on 1 degree grid, while other do.
        If you use grid_policy=adhoc and had not changed the mapping of function.
        grids.lab_adhoc_grid_policy to grids.CNRM_grid_policy, next setting can force any tos request
        to also produce tos on a 1 degree grid.

    mip_era
        [:term:`string`, :term:`lab_and_model_settings` and :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter.

    experiment_id
        [:term:`string`, :term:`simulation_settings`, :term:`always required`]

        Root experiment identifier.

    expid_in_filename
        [:term:`string`, :term:`simulation_settings`, default=:term:`experiment_id`]

        Experiment label to use in file names and attribute.

    experiment_for_requests
        [:term:`string`, :term:`simulation_settings`, default=:term:`experiment_id`]

        Experiment id to use for driving the use of the Data Request.

    configuration
        [:term:`string`, :term:`simulation_settings`]

        If there is no configuration in lab_settings which matches you case, please rather
        use next or next two entries: :term:`source_id` and, if needed, :term:`source_type`.

    included_vars
         [:term:`list`, :term:`simulation_settings`]


        It is possible to define the list of included vars in simulation settings.
        If it is done, it replace the list which could be defined in laboratory settings.

    source_id
        [:term:`string`, :term:`simulation_settings`]

        Name of the model used.

    source_type
        [:term:`string`, :term:`simulation_settings`]

        If the default source-type value for your source (:term:`source_types` from :term:`lab_and_model_settings`)
        does not fit, you may change it here.
        "This should describe the model most directly responsible for the output.  Sometimes it is appropriate to list
        two (or more) model types here, among AER, AGCM, AOGCM, BGC, CHEM, ISM, LAND, OGCM, RAD, SLAB "
        e.g. amip , run with CNRM-CM6-1, should quote "AGCM AER".
        Also see note 14 of https://docs.google.com/document/d/1h0r8RZr_f3-8egBMMh7aqLwy3snpD6_MrDz1q8n5XUk/edit

    project
        [:term:`string`, :term:`simulation_settings`, default: "CMIP6"]

        Project associated with the simulation.

    variant_info
        [:term:`string`, :term:`simulation_settings`, :term:`never required but recommended`]

        It is recommended that some description be included to help identify major differences among variants, but care
        should be taken to record correct information.  dr2xml will add in all cases:
        'Information provided by this attribute may in some cases be flawed. Users can find more comprehensive and
        up-to-date documentation via the further_info_url global attribute.'

    realization_index
        [:term:`integer`, :term:`simulation_settings`, :term:`always required`]

        Realization number.

    initialization_index
        [:term:`integer`, :term:`simulation_settings`, :term:`always required`]

        Index for variant of initialization method.

    physics_index
        [:term:`integer`, :term:`simulation_settings`, :term:`always required`]

        Index for model physics variant.

    forcing_index
        [:term:`integer`, :term:`simulation_settings`, :term:`always required`]

        Index for variant of forcing.

    branch_method
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`, default="standard"]

        Branching procedure.

    parent_time_ref_year
        [:term:`integer`, :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter.

    branch_year_in_parent
        [:term:`integer`, :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter.

    branch_month_in_parent
        [:term:`integer`, :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter.

    branch_time_in_parent
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Branch time with respect to parent's time axis.

    parent_time_units
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Time units used in parent.

    branch_year_in_child
        [:term:`integer`, :term:`simulation_settings`]

        In some instances, the experiment start year is not explicit or is doubtful in DR. See
        file doc/some_experiments_starty_in_DR01.00.21. You should then specifiy it, using next setting
        in order that requestItems analysis work in all cases

        In some other cases, DR requestItems which apply to the experiment form its start does not
        cover its whole duration and have a wrong duration (computed based on a wrong start year);
        They necessitate to fix the start year

    end_year
        [:term:`integer`, :term:`simulation_settings`]

        If you want to carry on the experiment beyond the duration set in DR, and that all
        requestItems that apply to DR end year also apply later on, set 'end_year'
        You can also set it if you don't know if DR has a wrong value

    child_time_ref_year
        [:term:`integer`, :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter.

    branch_time_in_child
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Branch time with respect to child's time axis

    parent_variant_label
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Parent variant label

    parent_mip_era
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Parent’s associated MIP cycle

    parent_source_id
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Parent model identifier

    sub_experiment_id
        [:term:`string`, :term:`simulation_settings`, :term:`always required`]

        Sub-experiment identifier

    sub_experiment
        [:term:`string`, :term:`simulation_settings`, :term:`always required`]

    history
        [:term:`string`, :term:`simulation_settings`, :term:`never required`]

        In case of replacement of previously produced data, description of any changes in the production chain.

    bypass_CV_components
        [:term:`boolean`, :term:`simulation_settings`]

        If the CMIP6 Controlled Vocabulary doesn't allow all the components you activate, you can set
        next toggle to True

    unused_contexts
        [:term:`list`, :term:`simulation_settings`]

        .. todo::

           Add a description of the parameter (and check that it is still used).

    model_id
        [:term:`string`, :term:`simulation_settings`]

        Model identifier.

    activity_id
        [:term:`string`, :term:`simulation_settings`, :term:`always required`]

        MIP(s) name(s)

    parent_experiment_id
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Parent experiment identifier.

    parent_activity
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        parent activity identifier (corresponds to :term:`parent_activity_id`)

    parent_activity_id
        [:term:`string`, :term:`simulation_settings`, :term:`required when relevant`]

        Description of sub-experiment

    useAtForInstant
        .. todo::

           Add a description of the parameter (and check that it is still used).

    sectors
        .. todo::

           Add a description of the parameter (and check that it is still used).

    grids_dev
        .. todo::

           Add a description of the parameter (and check that it is still used).

    institution
        .. todo::

           Add a description of the parameter (and check that it is still used).

    source
        .. todo::

           Add a description of the parameter (and check that it is still used).

    CORDEX_data
        .. todo::

           Add a description of the parameter (and check that it is still used).

    perso_sdims_description
        .. todo::

           Add a description of the parameter (and check that it is still used).

    experiment
        .. todo::

           Add a description of the parameter (and check that it is still used).

    description
        .. todo::

           Add a description of the parameter (and check that it is still used).

    driving_model_id
        .. todo::

           Add a description of the parameter (and check that it is still used).

    driving_model_ensemble_member
        .. todo::

           Add a description of the parameter (and check that it is still used).

    driving_experiment
        .. todo::

           Add a description of the parameter (and check that it is still used).

    driving_experiment_name
        .. todo::

           Add a description of the parameter (and check that it is still used).

    Lambert_conformal_longitude_of_central_meridian
        .. todo::

           Add a description of the parameter (and check that it is still used).

    Lambert_conformal_standard_parallel
        .. todo::

           Add a description of the parameter (and check that it is still used).

    Lambert_conformal_latitude_of_projection_origin
        .. todo::

           Add a description of the parameter (and check that it is still used).

    rcm_version_id
        .. todo::

           Add a description of the parameter (and check that it is still used).

    split_frequencies
        .. todo::

           Add a description of the parameter (and check that it is still used).

    HDL
        .. todo::

           Add a description of the parameter (and check that it is still used).
