# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

"""
Record/retrieve job information
"""

import ast
import glob
import os
import pickle

from .settings import settings
from ..utils.path import init_dir


JOB_DATA_DIR = 'jobdata'
JOB_DATA_FALLBACK_DIR = 'replay'
CONFIG_FILENAME = 'config'
URLS_FILENAME = 'urls'
MUX_FILENAME = 'multiplex'
PWD_FILENAME = 'pwd'
ARGS_FILENAME = 'args'
CMDLINE_FILENAME = 'cmdline'


def record(args, logdir, mux, urls=None, cmdline=None):
    """
    Records all required job information.
    """
    base_dir = init_dir(logdir, JOB_DATA_DIR)
    path_cfg = os.path.join(base_dir, CONFIG_FILENAME)
    path_urls = os.path.join(base_dir, URLS_FILENAME)
    path_mux = os.path.join(base_dir, MUX_FILENAME)
    path_pwd = os.path.join(base_dir, PWD_FILENAME)
    path_args = os.path.join(base_dir, ARGS_FILENAME)
    path_cmdline = os.path.join(base_dir, CMDLINE_FILENAME)

    if urls:
        with open(path_urls, 'w') as urls_file:
            urls_file.write('%s' % urls)

    with open(path_cfg, 'w') as config_file:
        settings.config.write(config_file)

    with open(path_mux, 'w') as mux_file:
        pickle.dump(mux, mux_file, pickle.HIGHEST_PROTOCOL)

    with open(path_pwd, 'w') as pwd_file:
        pwd_file.write('%s' % os.getcwd())

    with open(path_args, 'w') as args_file:
        pickle.dump(args.__dict__, args_file, pickle.HIGHEST_PROTOCOL)

    with open(path_cmdline, 'w') as cmdline_file:
        cmdline_file.write('%s' % cmdline)


def _retrieve(resultsdir, resource):
    path = os.path.join(resultsdir, JOB_DATA_DIR, resource)
    if not os.path.exists(path):
        path = os.path.join(resultsdir, JOB_DATA_FALLBACK_DIR, resource)
        if not os.path.exists(path):
            return None
    return path


def retrieve_pwd(resultsdir):
    """
    Retrieves the job pwd from the results directory.
    """
    recorded_pwd = _retrieve(resultsdir, PWD_FILENAME)
    if recorded_pwd is None:
        return None
    with open(recorded_pwd, 'r') as pwd_file:
        return pwd_file.read()


def retrieve_urls(resultsdir):
    """
    Retrieves the job urls from the results directory.
    """
    recorded_urls = _retrieve(resultsdir, URLS_FILENAME)
    if recorded_urls is None:
        return None
    with open(recorded_urls, 'r') as urls_file:
        return ast.literal_eval(urls_file.read())


def retrieve_mux(resultsdir):
    """
    Retrieves the job Mux object from the results directory.
    """
    recorded_mux = _retrieve(resultsdir, MUX_FILENAME)
    if recorded_mux is None:
        return None
    with open(recorded_mux, 'r') as mux_file:
        return pickle.load(mux_file)


def retrieve_args(resultsdir):
    """
    Retrieves the job args from the results directory.
    """
    recorded_args = _retrieve(resultsdir, ARGS_FILENAME)
    if recorded_args is None:
        return None
    with open(recorded_args, 'r') as args_file:
        return pickle.load(args_file)


def retrieve_config(resultsdir):
    """
    Retrieves the job settings from the results directory.
    """
    recorded_config = _retrieve(resultsdir, CONFIG_FILENAME)
    if recorded_config is None:
        return None
    return recorded_config


def retrieve_cmdline(resultsdir):
    """
    Retrieves the job command line from the results directory.
    """
    recorded_cmdline = _retrieve(resultsdir, CMDLINE_FILENAME)
    if recorded_cmdline is None:
        return None
    with open(recorded_cmdline, 'r') as cmdline_file:
        return ast.literal_eval(cmdline_file.read())


def get_resultsdir(logdir, jobid):
    """
    Gets the job results directory using a Job ID.
    """
    if os.path.isdir(jobid):
        return os.path.expanduser(jobid)
    elif os.path.isfile(jobid):
        return os.path.dirname(os.path.expanduser(jobid))
    elif jobid == 'latest':
        try:
            actual_dir = os.readlink(os.path.join(logdir, 'latest'))
            return os.path.join(logdir, actual_dir)
        except IOError:
            return None

    matches = 0
    short_jobid = jobid[:7]
    if len(short_jobid) < 7:
        short_jobid += '*'
    idfile_pattern = os.path.join(logdir, 'job-*-%s' % short_jobid, 'id')
    for id_file in glob.glob(idfile_pattern):
        if get_id(id_file, jobid) is not None:
            match_file = id_file
            matches += 1
            if matches > 1:
                raise ValueError("hash '%s' is not unique enough" % jobid)

    if matches == 1:
        return os.path.dirname(match_file)
    else:
        return None


def get_id(path, jobid):
    """
    Gets the full Job ID using the results directory path and a partial
    Job ID or the string 'latest'.
    """
    if os.path.isdir(jobid) or os.path.isfile(jobid):
        jobid = ''
    elif jobid == 'latest':
        jobid = os.path.basename(os.path.dirname(path))[-7:]

    if not os.path.exists(path):
        return None

    with open(path, 'r') as jobid_file:
        content = jobid_file.read().strip('\n')
    if content.startswith(jobid):
        return content
    else:
        return None
