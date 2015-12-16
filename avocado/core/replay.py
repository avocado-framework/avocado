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
import re
import shutil
from .settings import settings
from ..utils import path

"""
Record/retrieve job information for job replay
"""


def record(args, logdir, urls=None):
    replay_dir = path.init_dir(logdir, 'replay')
    path_cfg = os.path.join(replay_dir, 'config')
    path_urls = os.path.join(replay_dir, 'urls')
    path_mux = path.init_dir(replay_dir, 'multiplex')

    if urls:
        with open(path_urls, 'w') as f:
            f.write('%s' % urls)

    mux_files = getattr(args, 'multiplex_files', None)
    if mux_files:
        for mux_file in mux_files:
            file_path = _get_unused_path(path_mux, os.path.basename(mux_file))
            shutil.copy(mux_file, file_path)

    with open(path_cfg, 'w') as f:
        settings.config.write(f)


def retrieve_urls(resultsdir):
    recorded_urls = os.path.join(resultsdir, "replay", "urls")
    with open(recorded_urls, 'r') as f:
        urls = f.read()

    return ast.literal_eval(urls)


def retrieve_mux(resultsdir):
    recorded_mux_files = os.path.join(resultsdir, 'replay', 'multiplex',
                                      '*.yaml')
    return glob.glob(recorded_mux_files)


def retrieve_replay_map(resultsdir, replay_filter):
    replay_map = None
    resultsfile = os.path.join(resultsdir, "results.json")
    with open(resultsfile, 'r') as results_file_obj:
        results = json.loads(results_file_obj.read())

    if replay_filter:
        replay_map = [index for index, test in enumerate(results['tests'])
                      if test['status'] in replay_filter]
    else:
        replay_map = None

    return replay_map


def get_resultsdir(logdir, jobid):
    matches = 0
    idfile_pattern = os.path.join(logdir, 'job-*', 'id')
    for id_file in glob.glob(idfile_pattern):
        with open(id_file, 'r') as f:
            fileid = f.read().strip('\n')
        if re.search(jobid, fileid):
            match_file = id_file
            sourcejob = fileid
            matches += 1

    if matches == 1:
        return os.path.dirname(match_file), sourcejob
    else:
        return None, None


def _get_unused_path(directory, filename):
    count = 1
    path = os.path.join(directory, filename)
    while os.path.exists(path):
        filename = "%s_%s" % (count, filename)
        path = os.path.join(directory, filename)
        count += 1

    return path
