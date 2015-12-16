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
Record information and replay jobs using the information recorded
"""


def record(args, logdir):
    replay_dir = path.init_dir(logdir, 'replay')
    path_cfg = os.path.join(replay_dir, 'config')
    path_urls = os.path.join(replay_dir, 'urls')
    path_mux = path.init_dir(replay_dir, 'multiplex')

    urls = getattr(args, 'url', None)
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


def _get_unused_path(directory, filename):
    count = 1
    path = os.path.join(directory, filename)
    while os.path.exists(path):
        filename = "%s_%s" % (count, filename)
        path = os.path.join(directory, filename)
        count += 1

    return path
