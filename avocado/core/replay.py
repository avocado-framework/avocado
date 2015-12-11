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

import os
from .settings import settings
from ..utils import path

"""
Record information and replay jobs using the information recorded
"""


class Replay(object):

    """
    Object to record and represent the information needed for a job replay
    """

    def __init__(self, logdir):
        self.replay_dir = path.init_dir(logdir, 'replay')
        self.path_cfg = os.path.join(self.replay_dir, 'config')
        self.path_urls = os.path.join(self.replay_dir, 'urls')
        self.path_mux = path.init_dir(self.replay_dir, 'multiplex')

    def record_urls(self, urls):
        with open(self.path_urls, 'w') as f:
            f.write('%s' % urls)

    def record_config(self):
        with open(self.path_cfg, 'w') as f:
            settings.config.write(f)

    def record_mux(self, mux_files):
        if mux_files:
            for mux_file in mux_files:
                file_path = self._get_uniq_path(self.path_mux,
                                                os.path.basename(mux_file))
                with open(file_path, 'w') as f:
                    with open(mux_file, 'r') as source:
                        f.write(source.read())

    def _get_uniq_path(self, directory, filename):
        cont = 1
        path = os.path.join(directory, filename)
        while os.path.exists(path):
            filename = "%s_%s" % (cont, filename)
            path = os.path.join(directory, filename)
            cont += 1

        return path
