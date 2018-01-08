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
import json
import os

from . import varianter
from .output import LOG_UI, LOG_JOB
from .settings import settings
from ..utils.path import init_dir


JOB_DATA_DIR = 'jobdata'
CONFIG_FILENAME = 'config'
TEST_REFERENCES_FILENAME = 'test_references'
VARIANTS_FILENAME = 'variants.json'
PWD_FILENAME = 'pwd'
ARGS_FILENAME = 'args.json'
CMDLINE_FILENAME = 'cmdline'


def record(args, logdir, variants, references=None, cmdline=None):
    """
    Records all required job information.
    """
    def json_bad_variants_obj(item):
        for log in [LOG_UI, LOG_JOB]:
            log.warning("jobdata.variants: Unable to serialize '%s'", item)
        return str(item)
    base_dir = init_dir(logdir, JOB_DATA_DIR)
    path_cfg = os.path.join(base_dir, CONFIG_FILENAME)
    path_references = os.path.join(base_dir, TEST_REFERENCES_FILENAME)
    path_variants = os.path.join(base_dir, VARIANTS_FILENAME)
    path_pwd = os.path.join(base_dir, PWD_FILENAME)
    path_args = os.path.join(base_dir, ARGS_FILENAME)
    path_cmdline = os.path.join(base_dir, CMDLINE_FILENAME)

    if references:
        with open(path_references, 'w') as references_file:
            references_file.write('%s' % references)
            references_file.flush()
            os.fsync(references_file)

    with open(path_cfg, 'w') as config_file:
        settings.config.write(config_file)
        config_file.flush()
        os.fsync(config_file)

    with open(path_variants, 'w') as variants_file:
        json.dump(variants.dump(), variants_file, default=json_bad_variants_obj)
        variants_file.flush()
        os.fsync(variants_file)

    with open(path_pwd, 'w') as pwd_file:
        pwd_file.write('%s' % os.getcwd())
        pwd_file.flush()
        os.fsync(pwd_file)

    with open(path_args, 'w') as args_file:
        json.dump(args.__dict__, args_file, default=lambda x: None)
        args_file.flush()
        os.fsync(args_file)

    with open(path_cmdline, 'w') as cmdline_file:
        cmdline_file.write('%s' % cmdline)
        cmdline_file.flush()
        os.fsync(cmdline_file)


def _retrieve(resultsdir, resource):
    path = os.path.join(resultsdir, JOB_DATA_DIR, resource)
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


def retrieve_references(resultsdir):
    """
    Retrieves the job test references from the results directory.
    """
    recorded_references = _retrieve(resultsdir, TEST_REFERENCES_FILENAME)
    if recorded_references is None:
        return None
    with open(recorded_references, 'r') as references_file:
        return ast.literal_eval(references_file.read())


def retrieve_variants(resultsdir):
    """
    Retrieves the job variants object from the results directory.
    """
    recorded_variants = _retrieve(resultsdir, VARIANTS_FILENAME)
    if recorded_variants:
        with open(recorded_variants, 'r') as variants_file:
            return varianter.Varianter(state=json.load(variants_file))


def retrieve_args(resultsdir):
    """
    Retrieves the job args from the results directory.
    """
    recorded_args = _retrieve(resultsdir, ARGS_FILENAME)
    if recorded_args:
        with open(recorded_args, 'r') as args_file:
            return json.load(args_file)


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
        # Attempt to restore cmdline from log
        try:
            with open(os.path.join(resultsdir, "job.log"), "r") as log:
                import re
                cmd = re.search(r"# \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} "
                                r"\w{17}\w\d{4} INFO | Command line: (.*)",
                                log.read())
                if cmd:
                    import shlex
                    return shlex.split(cmd.group(1))
        except IOError:
            pass
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
