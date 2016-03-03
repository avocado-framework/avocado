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
# Copyright: Red Hat Inc. 2013-2015
# Author: Amador Pahim <apahim@redhat.com>

import ast
import glob
import json
import os
import pickle
import sys

from . import exit_codes
from .test import ReplaySkipTest

from .settings import settings
from ..utils import path

"""
Record/retrieve job information for job replay
"""


def record(args, logdir, mux, urls=None):
    replay_dir = path.init_dir(logdir, 'replay')
    path_cfg = os.path.join(replay_dir, 'config')
    path_urls = os.path.join(replay_dir, 'urls')
    path_mux = os.path.join(replay_dir, 'multiplex')
    path_pwd = os.path.join(replay_dir, 'pwd')
    path_args = os.path.join(replay_dir, 'args')

    if urls:
        with open(path_urls, 'w') as f:
            f.write('%s' % urls)

    with open(path_cfg, 'w') as f:
        settings.config.write(f)

    with open(path_mux, 'w') as f:
        pickle.dump(mux, f, pickle.HIGHEST_PROTOCOL)

    with open(path_pwd, 'w') as f:
        f.write('%s' % os.getcwd())

    with open(path_args, 'w') as f:
        pickle.dump(args.__dict__, f, pickle.HIGHEST_PROTOCOL)


def retrieve_pwd(resultsdir):
    recorded_pwd = os.path.join(resultsdir, "replay", "pwd")
    if not os.path.exists(recorded_pwd):
        return None

    with open(recorded_pwd, 'r') as f:
        return f.read()


def retrieve_urls(resultsdir):
    recorded_urls = os.path.join(resultsdir, "replay", "urls")
    if not os.path.exists(recorded_urls):
        return None

    with open(recorded_urls, 'r') as f:
        urls = f.read()

    return ast.literal_eval(urls)


def retrieve_mux(resultsdir):
    pkl_path = os.path.join(resultsdir, 'replay', 'multiplex')
    if not os.path.exists(pkl_path):
        return None

    with open(pkl_path, 'r') as f:
        return pickle.load(f)


def retrieve_replay_map(resultsdir, replay_filter):
    replay_map = None
    resultsfile = os.path.join(resultsdir, "results.json")
    if not os.path.exists(resultsfile):
        return None

    with open(resultsfile, 'r') as results_file_obj:
        results = json.loads(results_file_obj.read())

    replay_map = []
    for test in results['tests']:
        if test['status'] not in replay_filter:
            replay_map.append(ReplaySkipTest)
        else:
            replay_map.append(None)

    return replay_map


def retrieve_args(resultsdir):
    pkl_path = os.path.join(resultsdir, 'replay', 'args')
    if not os.path.exists(pkl_path):
        return None

    with open(pkl_path, 'r') as f:
        return pickle.load(f)


def get_resultsdir(logdir, jobid):
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
                from logging import getLogger
                getLogger("avocado.app").error("hash '%s' is not unique "
                                               "enough", jobid)
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)

    if matches == 1:
        return os.path.dirname(match_file)
    else:
        return None


def get_id(path, jobid):
    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        content = f.read().strip('\n')
    if content.startswith(jobid):
        return content
    else:
        return None
