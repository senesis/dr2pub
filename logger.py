#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools used in assembling and quality control check
"""

from __future__ import unicode_literals, print_function, absolute_import, division

import logging
import os
import six
import sys


log_dir = os.getcwd()
log_filename = "assemble_and_QC_postpro.out.{}".format(os.environ.get("MTOOL_JOB_ID", ""))
log_file = os.sep.join([log_dir, log_filename])
log_level = "info"

logger = logging.getLogger()


def initialize_logger(logfile=log_file, default=False, level="info"):
    change_log_file(logfile=logfile, default=default)
    change_log_level(level=level)


def change_log_file(logfile=log_file, default=False):
    global log_file, logger
    if default:
        logger = get_logger()
        for hdlr in logger.handlers[:]:
            try:
                hdlr.flush()
                hdlr.close()
            except:
                pass
            logger.removeHandler(hdlr)
        logger.addHandler(logging.StreamHandler(sys.stdout))
    else:
        log_file = logfile
        logger = logging.getLogger()
        for hdlr in logger.handlers[:]:
            try:
                hdlr.flush()
                hdlr.close()
            except:
                pass
            logger.removeHandler(hdlr)
        new_hdlr = logging.FileHandler(log_file)
        logger.addHandler(new_hdlr)
    return logger


def get_logger():
    return logger


def log_level_to_int(level):
    if isinstance(level, six.string_types):
        if level.lower() == 'debug':
            return logging.DEBUG
        elif level.lower() == 'critical':
            return logging.CRITICAL
        elif level.lower() == 'info':
            return logging.INFO
        elif level.lower() == 'warning':
            return logging.WARNING
        elif level.lower() == 'error':
            return logging.ERROR
    else:
        return level


def log_msg(level, *args, **kwargs):
    logger.log(log_level_to_int(level), *args, **kwargs)


def change_log_level(level=log_level):
    global logger, log_level
    log_level = level
    logger.setLevel(log_level_to_int(level))
