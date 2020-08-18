How to use home-variable list functionalities
=============================================

Although the Data Request is plethoric, modellers may want to output more or different variables
than the ones planned by the DR, either existing or not as a CMOR variable. They also may simply
want to ensure that a crucial variable will be output, without worrying whether this latter is included
in the DR or not.

In such cases, the user is invited to fill-in a list of home variables; an example is shown below.

..  code-block:: text

    #------------------------------------------------------------------------------------------------------------------------------------------------------
    #TYPE;    VARNAME;         REALM;     FREQUENCY;     TABLE;                     TEMPORAL_SHP;         SPATIAL_SHP;       EXPNAME;            MIP
    #------------------------------------------------------------------------------------------------------------------------------------------------------
    cmor;    areacello;       ocean;      fx;            CMIP_Ofx;                      None;            XY-na;             ANY;                ANY
    cmor;    tos;             ocean;     mon;           CMIP_Omon;                 time-mean;            XY-na;             ANY;                ANY
    cmor;    zos;             ocean;     mon;           CMIP_Omon;                 time-mean;            XY-na;             ANY;                ANY
    cmor;    sos;             ocean;     mon;           CMIP_Omon;                 time-mean;            XY-na;             ANY;                ANY
    extra;   heatc;           ocean;     mon;       CNRM_HOMOImon;                       ANY;              ANY;             ANY;                ANY
    extra;   hc700;           ocean;     mon;       CNRM_HOMOImon;                       ANY;              ANY;             ANY;                ANY
    extra;   hc2000;          ocean;     mon;       CNRM_HOMOImon;                       ANY;              ANY;             ANY;                ANY
    extra;   rhop;            ocean;     mon;       CNRM_HOMOImon;                       ANY;              ANY;             ANY;                ANY
    extra;   somematr;        ocean;     mon;       CNRM_HOMOImon;                       ANY;              ANY;             ANY;                ANY

The expected format and content of this file is detailed in dr2xml/doc/listof_home_vars.help.

The list of home variables is an 8-column file: TYPE, VARNAME, REALM, FREQUENCY, TABLE,
TEMPORAL_SHP, SPATIAL_SHP, EXPNAME, MIP.

‘TYPE=cmor’ means that it is a CMOR variable. In this case, VARNAME must be a CMOR Variable
name and all other parameters (REALM, FREQUENCY, TABLE, TEMPORAL_SHP, SPATIAL_SHP)
much match the ones of the targeted CMOR variable. Requesting for TEMPORAL_SHAPE and
SPATIAL_SHAPE can be seen as excessive, but this duly justify by the presence of ambiguities in the
DR definition of variables (discussed at the end of section 4).

‘TYPE=perso’ means that the variable does not exist in CMOR/CF world. In this case, VARNAME
must differ from existing CMOR Variable names. TABLE, TEMPORAL_SHP and SPATIAL_SHP can
be anything, they are not taken into account (but must be provided, even if ‘dummy’ – keep in mind
that TABLE is part of the DRS). A next version of dr2xml will offer the possibility to read a “home
table” [-not yet implemented-]; it has been considered as non-urgent functionality, since ‘perso’
variables are -a priori- not candidate to ESG publication.

‘MIP’ can be set to one of CMIP6 MIPs or to ‘ ANY’ (which means: output this home variable
whatever the MIP considered).

‘EXPNAME’ can be set to one of CMIP6 experiment name or to ‘ ANY’ (which means: current home
variable will be output for all experiments in the given MIP(s)).
