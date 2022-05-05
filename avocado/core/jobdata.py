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
import json
import os

from avocado.core.nrunner.config import ConfigDecoder, ConfigEncoder
from avocado.core.output import LOG_JOB, LOG_UI
from avocado.core.settings import settings
from avocado.core.varianter import VARIANTS_FILENAME
from avocado.utils.astring import string_to_safe_path
from avocado.utils.path import init_dir

JOB_DATA_DIR = 'jobdata'
CONFIG_FILENAME = 'config'
TEST_REFERENCES_FILENAME = 'test_references'
PWD_FILENAME = 'pwd'
JOB_CONFIG_FILENAME = 'args.json'
CMDLINE_FILENAME = 'cmdline'


def json_bad_variants_obj(item):
    for log in [LOG_UI, LOG_JOB]:
        log.warning("jobdata.variants: Unable to serialize '%s'", item)
    return str(item)


def record_suite_variant(path_variants, suite):
    with open(path_variants, 'w', encoding='utf-8') as variants_file:
        variants = []
        variants += suite.variants.dump()
        json.dump(variants, variants_file, default=json_bad_variants_obj)
        variants_file.flush()
        os.fsync(variants_file)


def record(job, cmdline=None):
    """
    Records all required job information.
    """
    base_dir = init_dir(job.logdir, JOB_DATA_DIR)
    path_cfg = os.path.join(base_dir, CONFIG_FILENAME)
    path_references = os.path.join(base_dir, TEST_REFERENCES_FILENAME)
    path_pwd = os.path.join(base_dir, PWD_FILENAME)
    path_job_config = os.path.join(base_dir, JOB_CONFIG_FILENAME)
    path_cmdline = os.path.join(base_dir, CMDLINE_FILENAME)

    references = job.config.get('resolver.references')
    if references:
        with open(path_references, 'w', encoding='utf-8') as references_file:
            references_file.write(f'{references}')
            references_file.flush()
            os.fsync(references_file)

    with open(path_cfg, 'w', encoding='utf-8') as config_file:
        settings.config.write(config_file)
        config_file.flush()
        os.fsync(config_file)

    for idx, suite in enumerate(job.test_suites, 1):
        if suite.name:
            suite_var_name = f"variants-{idx}-{suite.name}.json"
        else:
            suite_var_name = f"variants-{idx}.json"
        suite_var_name = string_to_safe_path(suite_var_name)
        path_suite_variant = os.path.join(base_dir, suite_var_name)
        record_suite_variant(path_suite_variant, suite)

    with open(path_pwd, 'w', encoding='utf-8') as pwd_file:
        pwd_file.write(f'{os.getcwd()}')
        pwd_file.flush()
        os.fsync(pwd_file)

    with open(path_job_config, 'w', encoding='utf-8') as job_config_file:
        json.dump(job.config, job_config_file,
                  cls=ConfigEncoder)
        job_config_file.flush()
        os.fsync(job_config_file)

    with open(path_cmdline, 'w', encoding='utf-8') as cmdline_file:
        cmdline_file.write(f'{cmdline}')
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
    with open(recorded_pwd, 'r', encoding='utf-8') as pwd_file:
        return pwd_file.read()


def retrieve_references(resultsdir):
    """
    Retrieves the job test references from the results directory.
    """
    recorded_references = _retrieve(resultsdir, TEST_REFERENCES_FILENAME)
    if recorded_references is None:
        return None
    with open(recorded_references, 'r', encoding='utf-8') as references_file:
        return ast.literal_eval(references_file.read())


def get_variants_path(resultsdir):
    """
    Retrieves the variants path from the results directory.
    """
    return _retrieve(resultsdir, VARIANTS_FILENAME)


def retrieve_job_config(resultsdir):
    """
    Retrieves the job config from the results directory.
    """
    recorded_job_config = _retrieve(resultsdir, JOB_CONFIG_FILENAME)
    if recorded_job_config:
        with open(recorded_job_config, 'r', encoding='utf-8') as job_config_file:
            return json.load(job_config_file, cls=ConfigDecoder)


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
            with open(os.path.join(resultsdir, "job.log"), "r", encoding='utf-8') as log:
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
    with open(recorded_cmdline, 'r', encoding='utf-8') as cmdline_file:
        return ast.literal_eval(cmdline_file.read())
