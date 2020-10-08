#!/usr/bin/python
# -*- coding: utf-8 -*-

# # Create ping files based on lab choices

from __future__ import print_function, division, absolute_import, unicode_literals

# from dr2xml import select_cmor_vars_for_lab, ping_file_for_realms_list
from pingfiles_interface import ping_file_for_realms_list
from vars_selection import gather_all_simple_vars

# In[ ]:

# Select your laboratory among: 'cnrm', 'cerfacs', 'ipsl'
lab = 'cerfacs'

# ## Lab settings

# In[ ]:

if lab == 'cnrm' or lab == 'cerfacs':
    # This dictionnary should be the same as the one used for creating file_defs.
    # Here , we quoted only those entries useful for creating ping files
    settings = {
        # 'mips' : {'AerChemMIP','C4MIP','CFMIP','DAMIP', 'FAFMIP' , 'GeoMIP','GMMIP','ISMIP6',\
        #                  'LS3MIP','LUMIP','OMIP','PMIP','RFMIP','ScenarioMIP','CORDEX','SIMIP'},
        # If you want to get comprehensive ping files; use :
        'mips': {"CMIP6", "AerChemMIP", "C4MIP", "CFMIP", "DAMIP", "DCPP", "FAFMIP", "GeoMIP", "GMMIP",
                 "HighResMIP", "ISMIP6", "LS3MIP", "LUMIP", "OMIP", "PDRMIP", "PMIP", "RFMIP", "ScenarioMIP",
                 "SolarMIP", "VolMIP", "CORDEX", "DynVar", "SIMIP", "VIACSAB", "SPECS", "CCMI", "CMIP5",
                 "CMIP", "DECK"},
        'max_priority': 3,
        'tierMax': 3,
        # Each XIOS  context does adress a number of realms
        'realms_per_context': {'nemo': ['seaIce', 'ocean', 'ocean seaIce', 'ocnBgchem', 'seaIce ocean'],
                               'arpsfx': ['atmos', 'atmos atmosChem', 'aerosol', 'atmos land', 'land',
                                          'landIce land', 'aerosol land', 'land landIce', 'landIce', ],
                               },
        "ping_variables_prefix": "CMIP6_",
        # We account for a file listing the variables which the lab does not want to produce
        # Format : MIP varname as first column, comment lines begin with '#'
        # "excluded_vars_file":"/cnrm/est/USERS/senesi/public/CMIP6/data_request/cnrm/excluded_vars.txt",
        "excluded_vars_file": None,
        "excluded_vars": None,
        # We account for a list of variables which the lab wants to produce in some cases
        "listof_home_vars": None,
        # "listof_home_vars": None,
        "path_extra_tables": None,
        # mpmoine_correction: Path for special XIOS defs files
        "path_special_defs": "./input/special_defs"
    }

# In[ ]:

if lab == 'cerfacs':
    # settings["mips"]={'HighResMIP','DCPP'}
    settings["listof_home_vars"] = "./input_labs/cerfacs/home_vars/listof_primavera_extra_vars.txt"
    settings["path_extra_tables"] = "./input_labs/cerfacs/extra_Tables"

# In[ ]:

if lab == 'ipsl':
    # This dictionnary should be the same as the one used for creating file_defs.
    # Here , we quoted only those entries useful for creating ping files
    settings = {
        # 'mips' : {'AerChemMIP','C4MIP','CFMIP','DAMIP', 'FAFMIP' , 'GeoMIP','GMMIP','ISMIP6',\
        #                  'LS3MIP','LUMIP','OMIP','PMIP','RFMIP','ScenarioMIP','CORDEX','SIMIP'},
        # If you want to get comprehensive ping files; use :
        'mips': {"CMIP6", "AerChemMIP", "C4MIP", "CFMIP", "DAMIP", "DCPP", "FAFMIP", "GeoMIP", "GMMIP",
                 "HighResMIP", "ISMIP6", "LS3MIP", "LUMIP", "OMIP", "PDRMIP", "PMIP", "RFMIP", "ScenarioMIP",
                 "SolarMIP", "VolMIP", "CORDEX", "DynVar", "SIMIP", "VIACSAB", "SPECS", "CCMI", "CMIP5",
                 "CMIP", "DECK"},
        'max_priority': 3,
        'tierMax': 3,
        # Each XIOS  context does adress a number of realms
        'realms_per_context': {
            'nemo': ['seaIce', 'ocean', 'ocean seaIce', 'ocnBgchem', 'seaIce ocean'],
            'lmdz': ['atmos', 'atmos land'],
            'orchidee': ['land', 'landIce land', 'land landIce', 'landIce'],
        },
        "ping_variables_prefix": "CMIP6_",
        # We account for a file listing the variables which the lab does not want to produce
        # Format : MIP varname as first column, comment lines begin with '#'
        "excluded_vars_file": None,
        "excluded_vars": None,
        # We account for a list of variables which the lab wants to produce in some cases
        "listof_home_vars": None,
        "path_extra_tables": None,
        # mpmoine_correction: Path for special XIOS defs files
        "path_special_defs": None
    }

# ### Read excluded variables list - you may skip that

# In[ ]:

l = []
if settings["excluded_vars"] is None and settings["excluded_vars_file"] is not None:
    with open(settings["excluded_vars_file"], 'r') as fv:
        varlines = fv.readlines()
    for line in varlines:
        fields = line.split()
        if len(fields) > 0:
            first = fields[0]
            if first[0] != '#':
                l.append(first)
settings["excluded_vars"] = l

# ## For getting a comprehensive ping file, one can (re)set the excluded_var list to an empty list

# In[ ]:

settings["excluded_vars"] = []

# In[ ]:

# ## Select all variables to consider, based on lab settings

# In[ ]:

# svars=select_cmor_vars_for_lab(settings, printout=True)
svars = gather_all_simple_vars(printout=True)

# ## Doc for ping files create function

# In[ ]:

help(ping_file_for_realms_list)

# When using function create_ping_files with argument exact=False, each ping file will adress all variables which
# realm includes or is included in one of the strings in a realms set  <br><br> e.g for set ['ocean','seaIce'],
# ping file 'ping_ocean_seaIce.xml' will includes variables which realm is either 'ocean' or 'seaIce' or 'ocean seaIce'

# ## Create various ping files for various sets of realms

# In[ ]:

# In/Out directory
my_dir = "output_labs/" + lab + "/"

# In[ ]:

# Generate one ping file per context:
for my_context in settings["realms_per_context"].keys():
    print("=== CREATING PINGFILE FOR CONTEXT", my_context)
    realms = settings['realms_per_context'][my_context]
    ping_file_for_realms_list(my_context, realms, svars, settings["path_special_defs"],
                              comments=" ", exact=False, dummy=True,
                              prefix=settings['ping_variables_prefix'],
                              filename=my_dir + 'ping_' + my_context + '.xml', dummy_with_shape=True)

# In[ ]:

# ! head -n 5 output_sample/ping_nemo.xml


# In[ ]:

# Generate one ping file per realm:
single_realms = [['ocean'], ['seaIce'], ['ocnBgchem'], ['atmos'], ['land'], ['landIce'], ['atmosChem'], ['aerosol']]
for rs in single_realms:
    # print rs[0]
    print("=== CREATING PINGFILE FOR SINGLE REALM", rs)
    ping_file_for_realms_list(rs[0], rs, svars, settings["path_special_defs"], prefix=settings['ping_variables_prefix'],
                              comments=" ", exact=False, dummy=True, dummy_with_shape=True,
                              filename=my_dir + 'ping_%s.xml' % rs[0])

# In[ ]:
