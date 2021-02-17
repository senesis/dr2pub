#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tools for variables selection.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict, namedtuple

# Utilities
from utils import Dr2xmlError, print_struct

# Logger
from logger import get_logger

# Interface to settings dictionaries
from settings_interface import get_variable_from_sset_else_lset_without_default, get_variable_from_lset_with_default, \
    get_variable_from_sset_without_default, get_source_id_and_type, get_variable_from_lset_without_default, \
    is_key_in_sset, is_sset_not_None, get_variable_from_sset_with_default_in_sset, \
    get_variable_from_sset_with_default, is_key_in_lset, get_variable_from_sset_else_lset_with_default
# Interface to Data Request
from dr_interface import get_request_by_id_by_sect, get_uid, get_experiment_label, initialize_sc

# Grids tools
from grids_selection import decide_for_grids

# Variables tools
from vars_home import complement_svar_using_cmorvar, process_home_vars
from vars_cmor import analyze_priority, SimpleCMORVar


print_multiple_grids = False
grid_choice = None


# global variable : the list of Request Links which apply for 'our' MIPS
# and which are not explicitly excluded using settings
# It is set in select_CMORvars_for_lab and used in endyear_for_CMORvar
global_rls = None
rls_for_all_experiments = None
sc = None

sn_issues = OrderedDict()


def get_grid_choice():
    """
    Get the value of global variable grid_choice
    """
    return grid_choice


def initialize_sn_issues(init):
    """
    Initialize global variable sn_issues
    """
    global sn_issues
    sn_issues = init


def get_sc():
    """
    Return the value of global variable sc
    """
    return sc


def endyear_for_CMORvar(cv, expt, year):
    """
    For a CMORvar, returns the largest year in the time slice(s)
    of those requestItems which apply for experiment EXPT and which
    include YEAR. If no time slice applies, returns None
    """
    # 1- Get the RequestItems which apply to CmorVar
    # 2- Select those requestItems which include expt,
    #    and retain their endyear if larger than former one

    global global_rls

    # Some debug material
    logger = get_logger()
    logger.info("In end_year for %s %s" % (cv.label, cv.mipTable))
    pmax = get_variable_from_sset_else_lset_without_default('max_priority')

    # 1- Get the RequestItems which apply to CmorVar
    rVarsUid = get_request_by_id_by_sect(cv.uid, 'requestVar')
    rVars = [get_uid(uid) for uid in rVarsUid if get_uid(uid).priority <= pmax]
    logger.info("les requestVars:", [rVar.title for rVar in rVars])
    VarGroups = [get_uid(rv.vgid) for rv in rVars]
    logger.info("les requestVars groups:", [rVg.label for rVg in VarGroups])
    RequestLinksId = list()
    for vg in VarGroups:
        RequestLinksId.extend(get_request_by_id_by_sect(vg.uid, 'requestLink'))
    FilteredRequestLinks = list()
    for rlid in RequestLinksId:
        rl = get_uid(rlid)
        if rl in global_rls:
            FilteredRequestLinks.append(rl)
    logger.info("les requestlinks:", [get_uid(rlid).label for rlid in RequestLinksId])
    logger.info("les FilteredRequestlinks:", [rl.label for rl in FilteredRequestLinks])
    RequestItems = list()
    for rl in FilteredRequestLinks:
        RequestItems.extend(get_request_by_id_by_sect(rl.uid, 'requestItem'))
    logger.info("les requestItems:", [get_uid(riid).label for riid in RequestItems])

    # 2- Select those request links which include expt and year
    larger = None
    for riid in RequestItems:
        ri = get_uid(riid)
        applies, endyear = RequestItem_applies_for_exp_and_year(ri, expt, year)
        logger.info("For var and freq selected for debug and year %s, for ri %s, applies=%s, endyear=%s" %
                    (str(year), ri.title, str(applies), str(endyear)))
        if applies:
            if endyear is None:
                return None  # One of the timeslices cover the whole expt
            if larger is None:
                larger = endyear
            else:
                larger = max(larger, endyear)
    return larger


def RequestItem_applies_for_exp_and_year(ri, experiment, year=None):
    """
    Returns True if requestItem 'ri' in data request is relevant
    for a given 'experiment' and 'year'. Toggle 'debug' allow some printouts
    """
    # Returns a couple : relevant, endyear.
    # RELEVANT is True if requestItem RI applies to EXPERIMENT and
    #   has a timeslice wich includes YEAR, either implicitly or explicitly
    # ENDYEAR is meaningful if RELEVANT is True, and is the
    #   last year in the timeslice (or None if timeslice ==
    #   the whole experiment duration)

    # Acces experiment or experiment group for the RequestItem
    # if (ri.label=='C4mipC4mipLandt2') : debug=True
    # if ri.title=='AerChemMIP, AERmon-3d, piControl' : debug=True
    # if ri.title=='CFMIP, CFMIP.CFsubhr, amip' : debug=True
    logger = get_logger()
    logger.debug("In RIapplies.. Checking ", "% 15s" % ri.title,)
    item_exp = get_uid(ri.esid)
    ri_applies_to_experiment = False
    endyear = None
    # esid can link to an experiment or an experiment group
    if item_exp._h.label in ['experiment', ]:
        logger.debug("%20s" % "Simple Expt case", item_exp.label,)
        if item_exp.label in [experiment, ]:
            logger.debug(" OK",)
            ri_applies_to_experiment = True
    elif item_exp._h.label in ['exptgroup', ]:
        logger.debug("%20s" % "Expt Group case ", item_exp.label,)
        exps_id = get_request_by_id_by_sect(ri.esid, 'experiment')
        for e in [get_uid(eid) for eid in exps_id]:
            if e.label in [experiment, ]:
                logger.debug(" OK for experiment based on group" + item_exp.label,)
                ri_applies_to_experiment = True
    elif item_exp._h.label in ['mip', ]:
        logger.debug("%20s" % "Mip case ", get_uid(item_exp.label).label,)
        exps_id = get_request_by_id_by_sect(ri.esid, 'experiment')
        for e in [get_uid(eid) for eid in exps_id]:
            logger.debug(e.label, ",",)
            if e.label == experiment:
                logger.debug(" OK for experiment based on mip" + item_exp.label,)
                ri_applies_to_experiment = True
    else:
        logger.debug("Error on esid link for ri : %s uid=%s %s" % (ri.title, ri.uid, item_exp._h.label))
    # print "ri=%s"%ri.title,
    # if year is not None :
    #    print "Filtering for year %d"%year
    filter_on_realization = get_variable_from_sset_else_lset_with_default("filter_on_realization", default=True)
    if filter_on_realization:
        if ri.nenmax != -1 and (get_variable_from_sset_without_default("realization_index") > ri.nenmax):
            ri_applies_to_experiment = False

    if ri_applies_to_experiment:
        logger.debug("Year considered:", year, type(year))
        if year is None:
            rep = True
            endyear = None
            logger.debug(" ..applies because arg year is None")
        else:
            year = int(year)
            exp = get_uid(get_experiment_label(experiment))
            rep, endyear = year_in_ri(ri, exp, year)
            logger.debug(" ..year in ri returns :", rep, endyear)
            # if (ri.label=="AerchemmipAermonthly3d") :
            #    print "reqItem=%s,experiment=%s,year=%d,rep=%s,"%(ri.label,experiment,year,rep)
        # print " rep=",rep
        return rep, endyear
    else:
        # print
        return False, None


def year_in_ri(ri, exp, year):
    """
    :param ri: request item
    :param exp: experiment
    :param year: year to treat
    :return: a tuple which contains a boolean indicated whether the year has to be treated and the last year to treat
    """
    logger = get_logger()
    if ri.label in ["CfmipCf3hrSimNew", ]:
        return (year == 2008), 2008
    if "HighResMIP, HighResMIP-6hrPlevExtr, amip" in ri.title:
        return True, 2018
    if 'tslice' in ri.__dict__:
        logger.debug("calling year_in_ri_tslice")
        rep, endyear = year_in_ri_tslice(ri, exp, year)
        return rep, endyear
    try:
        ny = int(ri.nymax)
    except:
        logger.warning("Cannot tell if reqItem %s applies to year %d  (ny=%s) -> assumes yes" % (ri.title, year,
                                                                                                 repr(ny)))
        return True, None
    #
    # From now, this the case of a RequestItem which starts from experiment's start
    actual_first_year = experiment_start_year(exp)  # The start year, possibly fixed by the user
    actual_end_year = experiment_end_year_from_sset(exp)  # = the end year requested by the user if any
    DR_first_year = experiment_start_year_without_sset(exp, debug=debug)
    DR_end_year = experiment_end_year(exp)
    logger.debug("year_in_ri : start DR : %s actual : %s | end DR : %s actual : %s | ny=%d" %
                 (DR_first_year, actual_first_year, DR_end_year, actual_end_year, ny))
    #
    ri_is_for_all_experiment = False
    if ny <= 0:
        ri_is_for_all_experiment = True
        logger.debug("year_in_ri : RI applies systematically")
    else:
        if DR_first_year and DR_end_year and ny == (DR_end_year - DR_first_year + 1):
            ri_is_for_all_experiment = True
            logger.debug("year_in_ri : RI applies because ny=end-start")
    if ri_is_for_all_experiment:
        return True, None
    #
    # From now, we know that requestItem duration is less than experiment duration, or that
    # experiment duration is not known
    # We may have errors in requestItem duration ny, because of an error in DR for start year
    # So, we add to ny the difference between DR and actual start_years, if the DR value is meaningful
    if DR_first_year:
        ny += DR_first_year - actual_first_year  # Will be 0 if end is defined in DR and not by the user
        logger.debug("year_in_ri : compensating ny for diff in first year")
    RI_end_year = actual_first_year + ny - 1
    # For these kind of requestItem of limited duration, no need to extend it, whatever the actual end date
    applies = (year <= RI_end_year)
    logger.debug("year_in_ri : returning ", applies, RI_end_year)
    return applies, RI_end_year


def year_in_ri_tslice(ri, exp, year):
    """
    Returns a couple : relevant, endyear.
    RELEVANT is True if requestItem RI applies to
      YEAR, either implicitly or explicitly (e.g. timeslice)
    ENDYEAR, which is meaningful if RELEVANT is True, and is the
      last year in the timeslice (or None if timeslice ==
      the whole experiment duration)
    """
    logger = get_logger()
    if 'tslice' not in ri.__dict__:
        logger.debug("No tslice for reqItem %s -> OK for any year" % ri.title)
        return True, None
    if ri.tslice in ['__unset__', ]:
        logger.debug("tslice is unset for reqItem %s " % ri.title)
        return True, None
    #
    relevant = False
    endyear = None
    tslice = get_uid(ri.tslice)
    logger.debug("tslice label/type is %s/%s for reqItem %s " % (tslice.label, tslice.type, ri.title))
    if tslice.type == "relativeRange":  # e.g. _slice_abrupt30
        first_year = experiment_start_year(exp)
        # first_year = sset["branch_year_in_child"]
        relevant = (year >= tslice.start + first_year - 1 and year <= tslice.end + first_year - 1)
        endyear = first_year + tslice.end - 1
    elif tslice.type == "simpleRange":  # e.g. _slice_DAMIP20
        relevant = (year >= tslice.start and year <= tslice.end)
        endyear = tslice.end
    elif tslice.type == "sliceList":  # e.g. _slice_DAMIP40
        for start in range(tslice.start, int(tslice.end - tslice.sliceLen + 2), int(tslice.step)):
            if year >= start and year < start + tslice.sliceLen:
                relevant = True
                endyear = start + tslice.sliceLen - 1
    elif tslice.type == "dayList":  # e.g. _slice_RFMIP2
        # e.g. startList[i]: [1980, 1, 1, 1980, 4, 1, 1980, 7, 1, 1980, 10, 1, 1992, 1, 1, 1992, 4, 1]
        years = [tslice.startList[3 * i] for i in range(len(tslice.startList) / 3)]
        if year in years:
            relevant = True
            endyear = year
    elif tslice.type == "startRange":  # e.g. _slice_VolMIP3
        # used only for VolMIP : _slice_VolMIP3
        start_year = experiment_start_year(exp)
        relevant = (year >= start_year and year < start_year + nyear)
        endyear = start_year + nyear - 1
    elif tslice.type == "monthlyClimatology":  # e.g. _slice_clim20
        relevant = (year >= tslice.start and year <= tslice.end)
        endyear = tslice.end
    elif tslice.type == "branchedYears":  # e.g. _slice_piControl020
        source, source_type = get_source_id_and_type()
        if tslice.child in get_variable_from_lset_without_default("branching", source):
            endyear = False
            (refyear, starts) = get_variable_from_lset_without_default("branching", source, tslice.child)
            for start in starts:
                if ((year - start >= tslice.start - refyear) and
                        (year - start < tslice.start - refyear + tslice.nyears)):
                    relevant = True
                    lastyear = start + tslice.start - refyear + tslice.nyears - 1
                    if endyear is False:
                        endyear = lastyear
                    else:
                        endyear = max(endyear, lastyear)
                    logger.debug("slice OK: year=%d, start=%d tslice.start=%d refyear=%d tslice.nyears=%d lastyear=%d" %
                                 (year, start, tslice.start, refyear, tslice.nyears, lastyear))
        else:
            raise Dr2xmlError("For tslice %s, child %s start year is not documented" % (tslice.title, tslice.child))
    else:
        raise Dr2xmlError("type %s for time slice %s is not handled" % (tslice.type, tslice.title))
    logger.debug("for year %d and experiment %s, relevant is %s for tslice %s of type %s, endyear=%s" %
                 (year, exp.label, repr(relevant), ri.title, tslice.type, repr(endyear)))
    return relevant, endyear


def experiment_start_year_without_sset(exp):
    """
    Find start year of an experiment
    :param exp: experiment
    :param debug: boolean to activate debug log
    :return: start year of the experiment
    """
    logger = get_logger()
    try:
        return int(float(exp.starty))
    except:
        logger.debug("start_year : starty=", exp.starty)
        return None


def experiment_start_year(exp):
    """
    Find star year of an experiment
    :param exp: experiment
    :param debug: boolean for debug verbose level activation
    :return: start year of an experiment
    """
    if is_key_in_sset("branch_year_in_child"):
        return get_variable_from_sset_without_default("branch_year_in_child")
    else:
        starty = experiment_start_year_without_sset(exp)
        if starty is None:
            form = "Cannot guess first year for experiment %s : DR says :'%s' "
            if is_sset_not_None():
                form += "and 'branch_year_in_child' is not provided in experiment's settings"
            raise Dr2xmlError(form % (exp.label, exp.starty))


def experiment_end_year(exp):
    """
    Find the year of an experiment
    :param exp: experiment
    :return: end year of the experiment
    """
    try:
        return int(float(exp.endy))
    except:
        return None


def experiment_end_year_from_sset(exp):
    """
    Find the end year of an experiment
    :param exp: experiment
    :return: end year of the experiment
    """
    if is_key_in_sset("end_year"):
        return get_variable_from_sset_without_default("end_year")
    else:
        return experiment_end_year(exp)


def select_CMORvars_for_lab(sset=False, year=None):
    """
    A function to list CMOR variables relevant for a lab (and also,
    optionnally for an experiment and a year)
    The variables relative to the laboratory settings are get using the dict_interface module:
    list of MIPS, max Tier, list of excluded variables names

    Args:
      sset (boolean): should simulation settings be used
                      the parameter taken here are: source_type,
                      max priority (and all for filtering on the simulation)
                      If sset is False, use union of mips among all grid choices
      year (int,optional) : simulation year - used when sset is not None,
                   to additionally filter on year

    Returns:
      A list of 'simplified CMOR variables'

    """
    logger = get_logger()
    #
    # From MIPS set to Request links
    global sc, global_rls, grid_choice, rls_for_all_experiments, sn_issues
    if sset:
        tierMax = get_variable_from_sset_else_lset_without_default('tierMax')
    else:
        tierMax = get_variable_from_lset_without_default('tierMax')
    if sc is None:
        sc = initialize_sc(tierMax)

    # Set sizes for lab settings, if available (or use CNRM-CM6-1 defaults)
    mcfg = namedtuple('mcfg', ['nho', 'nlo', 'nha', 'nla', 'nlas', 'nls', 'nh1'])
    if sset:
        source, source_type = get_source_id_and_type()
        grid_choice = get_variable_from_lset_without_default("grid_choice", source)
        mips_list = set(get_variable_from_lset_without_default('mips', grid_choice))
        sizes = get_variable_from_lset_without_default("sizes", grid_choice)
        # sizes=get_variable_from_lset_with_default("sizes",[259200,60,64800,40,20,5,100])
        sc.mcfg = mcfg._make(sizes)._asdict()
    else:
        mips_list = set()
        for grid in get_variable_from_lset_without_default('mips'):
            mips_list = mips_list.union(set(get_variable_from_lset_without_default('mips', grid)))
        grid_choice = "LR"
    # Sort mip_list for reproducibility
    mips_list = list(mips_list)
    mips_list.sort()
    #
    if rls_for_all_experiments is None:
        # Because scope do not accept list types
        rls_for_mips = sorted(list(sc.getRequestLinkByMip(set(mips_list))), key=lambda x: x.label)
        logger.info("Number of Request Links which apply to MIPS", print_struct(mips_list), " is: ", len(rls_for_mips))
        #
        excluded_rls = list()
        for rl in rls_for_mips:
            if rl.label in get_variable_from_lset_with_default("excluded_request_links", []):
                excluded_rls.append(rl)
        for rl in excluded_rls:
            rls_for_mips.remove(rl)
        logger.info("Number of Request Links after filtering by excluded_request_links is: ", len(rls_for_mips))
        #
        excluded_rls = list()
        inclinks = get_variable_from_lset_with_default("included_request_links", [])
        if len(inclinks) > 0:
            for rl in rls_for_mips:
                if rl.label not in inclinks:
                    excluded_rls.append(rl)
            for rl in excluded_rls:
                logger.critical("RequestLink %s is not included" % rl.label)
                rls_for_mips.remove(rl)
        logger.info("Number of Request Links after filtering by included_request_links is: ", len(rls_for_mips))
        rls_for_all_experiments = [rl for rl in rls_for_mips]
    else:
        rls_for_mips = sorted(rls_for_all_experiments, key=lambda x: x.label)
    #
    if sset:
        experiment_id = get_variable_from_sset_with_default_in_sset('experiment_for_requests', 'experiment_id')
        exp = get_uid(get_experiment_label(experiment_id))
        logger.info("Filtering for experiment %s, covering years [ %s , %s ] in DR" %
                    (experiment_id, exp.starty, exp.endy))
        # print "Request links before filter :"+`[ rl.label for rl in rls_for_mips ]`
        filtered_rls = []
        for rl in rls_for_mips:
            # Access all requesItems ids which refer to this RequestLink
            ri_ids = get_request_by_id_by_sect(rl.uid, 'requestItem')
            for ri_id in ri_ids:
                ri = get_uid(ri_id)
                # debug=(ri.label=='C4mipC4mipLandt2')
                logger.debug("Checking requestItem ", ri.title,)
                applies, endyear = RequestItem_applies_for_exp_and_year(ri, experiment_id, year)
                if applies:
                    logger.debug(" applies ")
                    filtered_rls.append(rl)
                else:
                    logger.debug(" does not apply ")

        rls = filtered_rls
        logger.info("Number of Request Links which apply to experiment ", experiment_id, " member ",
                    get_variable_from_sset_without_default('realization_index'), " and MIPs",
                    print_struct(mips_list), " is: ", len(rls))
        # print "Request links that apply :"+`[ rl.label for rl in filtered_rls ]`
    else:
        rls = rls_for_mips

    global_rls = rls

    # From Request links to CMOR vars + grid
    # miprl_ids=[ rl.uid for rl in rls ]
    # miprl_vars=sc.varsByRql(miprl_ids, pmax=lset['max_priority'])
    if sset:
        pmax = get_variable_from_sset_else_lset_without_default('max_priority')
    else:
        pmax = get_variable_from_lset_without_default('max_priority')
    miprl_vars_grids = []
    for rl in rls:
        logger.debug("processing RequestLink %s" % rl.title)
        rl_vars = sc.varsByRql([rl.uid], pmax=pmax)
        for v in rl_vars:
            # The requested grid is given by the RequestLink except if spatial shape matches S-*
            gr = rl.grid
            cmvar = get_uid(v)
            st = get_uid(cmvar.stid)
            sp = get_uid(st.spid)
            if sp.label[0:2] == "S-":
                gr = 'cfsites'
            if (v, gr) not in miprl_vars_grids:
                miprl_vars_grids.append((v, gr))
                # if 'ua' in cmvar.label : print "adding %s %s"%(cmvar.label,get_uid(cmvar.vid).label)
            # else:
            #    print "Duplicate pair var/grid : ",cmvar.label,cmvar.mipTable,gr
    logger.info('Number of (CMOR variable, grid) pairs for these requestLinks is :%s' % len(miprl_vars_grids))

    # for (v,g) in miprl_vars_grids :
    #    if get_uid(v).label=="ps" : print "step 1 : ps in table",get_uid(v).mipTable,g

    #
    if sset:
        inctab = get_variable_from_sset_else_lset_with_default("included_tables", default=list())
    else:
        inctab = get_variable_from_lset_with_default("included_tables", list())
    exctab = get_variable_from_lset_with_default("excluded_tables", list())
    if sset:
        exctab.extend(get_variable_from_sset_with_default("excluded_tables", list()))
    if sset:
        incvars = get_variable_from_sset_else_lset_with_default("included_vars", default=list())
    else:
        incvars = get_variable_from_lset_with_default('included_vars', list())
    excvars = get_variable_from_lset_with_default('excluded_vars', list())
    if sset:
        excvars_for_expes = get_variable_from_sset_with_default('excluded_vars', list())
        excvars.extend(excvars_for_expes)

    excpairs = get_variable_from_lset_with_default('excluded_pairs', list())
    if sset:
        config = get_variable_from_sset_without_default('configuration')
        if (is_key_in_lset('excluded_vars_per_config')) and \
                (config in get_variable_from_lset_without_default('excluded_vars_per_config')):
            excvars.extend(get_variable_from_lset_without_default('excluded_vars_per_config', config))
        excpairs.extend(get_variable_from_sset_with_default('excluded_pairs', list()))

    filtered_vars = list()
    for (v, g) in miprl_vars_grids:
        cmvar = get_uid(v)
        ttable = get_uid(cmvar.mtid)
        mipvar = get_uid(cmvar.vid)
        if ((len(incvars) == 0 and mipvar.label not in excvars) or (len(incvars) > 0 and mipvar.label in incvars))\
                and ((len(inctab) > 0 and ttable.label in inctab) or (len(inctab) == 0 and ttable.label not in exctab))\
                and ((mipvar.label, ttable.label) not in excpairs):
            filtered_vars.append((v, g))
            logger.debug("adding var %s, grid=%s, ttable=%s=" % (cmvar.label, g, ttable.label))  # ,exctab,excvars

    logger.info('Number once filtered by excluded/included vars and tables and spatial shapes is : %s' \
                % len(filtered_vars))

    # Filter the list of grids requested for each variable based on lab policy
    d = OrderedDict()
    for (v, g) in filtered_vars:
        if v not in d:
            d[v] = set()
        d[v].add(g)
    logger.info('Number of distinct CMOR variables (whatever the grid) : %d' % len(d))
    multiple_grids = list()
    for v in d:
        d[v] = decide_for_grids(v, d[v])
        if len(d[v] > 1):
            multiple_grids.append(get_uid(v).label)
            if print_multiple_grids:
                logger.info("\tVariable %s will be processed with multiple grids : %s"
                            % (multiple_grids[-1], repr(d[v])))
    if not print_multiple_grids:
        logger.info("\tThese variables will be processed with multiple grids " +
                    "(rerun with print_multiple_grids set to True for details) :" + repr(multiple_grids.sort()))
    #
    # Print a count of distinct var labels
    logger.info('Number of distinct var labels is : %d' % len(set([get_uid(v).label for v in d])))

    # Translate CMORvars to a list of simplified CMORvar objects
    simplified_vars = []
    allow_pseudo = get_variable_from_lset_with_default('allow_pseudo_standard_names', False)
    for v in d:
        svar = SimpleCMORVar()
        cmvar = get_uid(v)
        sn_issues = complement_svar_using_cmorvar(svar, cmvar, sn_issues, [], allow_pseudo)
        svar.Priority = analyze_priority(cmvar, mips_list)
        svar.grids = d[v]
        if get_uid(v).label in ["tas", ]:
            logger.debug("When complementing, tas is included , grids are %s" % svar.grids)
        simplified_vars.append(svar)
    logger.info('Number of simplified vars is :', len(simplified_vars))
    logger.info("Issues with standard names are :", print_struct(sorted(list(sn_issues))))

    return simplified_vars


def gather_AllSimpleVars(year=False, select="on_expt_and_year"):
    """
    List of mip variables asked
    :param year: year when the variables are created
    :param select: selection criteria
    :return: list of mip variables
    """
    logger = get_logger()
    if select in ["on_expt_and_year", ""]:
        mip_vars_list = select_CMORvars_for_lab(True, year)
    elif select in ["on_expt", ]:
        mip_vars_list = select_CMORvars_for_lab(True, None)
    elif select in ["no", ]:
        mip_vars_list = select_CMORvars_for_lab(False, None)
    else:
        logger.error("Choice %s is not allowed for arg 'select'" % select)
        raise Dr2xmlError("Choice %s is not allowed for arg 'select'" % select)
    #
    if get_variable_from_sset_else_lset_with_default('listof_home_vars', 'listof_home_vars', None):
        exp = get_variable_from_sset_with_default_in_sset('experiment_for_requests', 'experiment_id')
        process_home_vars(mip_vars_list, get_variable_from_lset_without_default("mips", grid_choice),
                          expid=exp)
    else:
        logger.info("Info: No HOMEvars list provided.")
    return mip_vars_list


def select_variables_to_be_processed(year, context, select):
    """
    Return the list of variables to be processed.
    """
    logger = get_logger()
    #
    # --------------------------------------------------------------------
    # Extract CMOR variables for the experiment and year and lab settings
    # --------------------------------------------------------------------
    mip_vars_list = gather_AllSimpleVars(year, select)
    # Group CMOR vars per realm
    svars_per_realm = OrderedDict()
    for svar in mip_vars_list:
        realm = svar.modeling_realm
        if realm not in svars_per_realm:
            svars_per_realm[realm] = []
        if svar not in svars_per_realm[realm]:
            add = True
            for ovar in svars_per_realm[realm]:
                if ovar.label == svar.label and ovar.spatial_shp == svar.spatial_shp \
                        and ovar.frequency == svar.frequency and ovar.cell_methods == svar.cell_methods:
                    add = False
            # Settings may allow for duplicate var in two tables. In DR01.00.21, this actually
            # applies to very few fields (ps-Aermon, tas-ImonAnt, areacellg)
            if get_variable_from_lset_with_default('allow_duplicates', True) or add:
                svars_per_realm[realm].append(svar)
            else:
                logger.warning("Not adding duplicate %s (from %s) for realm %s" % (svar.label, svar.mipTable, realm))
        else:
            old = svars_per_realm[realm][0]
            logger.warning("Duplicate svar %s %s %s %s" % (old.label, old.grid, svar.label, svar.grid))
            pass
    logger.info("\nRealms for these CMORvars :", *sorted(list(svars_per_realm)))
    #
    # --------------------------------------------------------------------
    # Select on context realms, grouping by table
    # Excluding 'excluded_vars' and 'excluded_spshapes' lists
    # --------------------------------------------------------------------
    svars_per_table = OrderedDict()
    context_realms = get_variable_from_lset_without_default('realms_per_context', context)
    processed_realms = list()
    for realm in context_realms:
        if realm in processed_realms:
            continue
        processed_realms.append(realm)
        print("Processing realm '%s' of context '%s'" % (realm, context))
        # print 50*"_"
        excludedv = OrderedDict()
        if realm in svars_per_realm:
            for svar in list(svars_per_realm[realm]):
                # exclusion de certaines spatial shapes (ex. Polar Stereograpic Antarctic/Groenland)
                if svar.label not in get_variable_from_lset_without_default('excluded_vars') and \
                        svar.spatial_shp and \
                        svar.spatial_shp not in get_variable_from_lset_without_default("excluded_spshapes"):
                    if svar.mipTable not in svars_per_table:
                        svars_per_table[svar.mipTable] = []
                    svars_per_table[svar.mipTable].append(svar)
                else:
                    reason = "unknown reason"
                    if svar.label in get_variable_from_lset_without_default('excluded_vars'):
                        reason = "They are in exclusion list "
                    if not svar.spatial_shp:
                        reason = "They have no spatial shape "
                    if svar.spatial_shp in get_variable_from_lset_without_default("excluded_spshapes"):
                        reason = "They have excluded spatial shape : %s" % svar.spatial_shp
                    if reason not in excludedv:
                        excludedv[reason] = []
                    excludedv[reason].append((svar.label, svar.mipTable))
        if len(list(excludedv)) > 0:
            logger.info("The following pairs (variable,table) have been excluded for these reasons :\n%s" %
                        "\n".join(["%s: %s" % (reason, print_struct(excludedv[reason], skip_sep=True, sort=True))
                                   for reason in sorted(list(excludedv))]))
    logger.debug("For table AMon: ", [v.label for v in svars_per_table["Amon"]])
    #
    # --------------------------------------------------------------------
    # Add svars belonging to the orphan list
    # --------------------------------------------------------------------
    if context in get_variable_from_lset_without_default('orphan_variables'):
        orphans = get_variable_from_lset_without_default('orphan_variables', context)
        for svar in mip_vars_list:
            if svar.label in orphans:
                if svar.label not in get_variable_from_lset_without_default('excluded_vars') and svar.spatial_shp and \
                        svar.spatial_shp not in get_variable_from_lset_without_default("excluded_spshapes"):
                    if svar.mipTable not in svars_per_table:
                        svars_per_table[svar.mipTable] = []
                    svars_per_table[svar.mipTable].append(svar)
    #
    # --------------------------------------------------------------------
    # Remove svars belonging to other contexts' orphan lists
    # --------------------------------------------------------------------
    for other_context in get_variable_from_lset_without_default('orphan_variables'):
        if other_context != context:
            orphans = get_variable_from_lset_without_default('orphan_variables', other_context)
            for table in svars_per_table:
                toremove = list()
                for svar in svars_per_table[table]:
                    if svar.label in orphans:
                        toremove.append(svar)
                for svar in toremove:
                    svars_per_table[table].remove(svar)
    logger.debug("Pour table AMon: ", [v.label for v in svars_per_table["Amon"]])
    # Return the different values
    return svars_per_table
