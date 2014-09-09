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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import os
import process


def make(path, make='make', env='', extra_args='', ignore_status=False):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param env: environment variables to be set before calling make
                (e.g.: CFLAGS).
    :param extra: extra command line arguments to pass to make.
    """
    cwd = os.getcwd()
    os.chdir(path)
    if env:
        env += ' '
    cmd = '%smake' % env
    makeopts = os.environ.get('MAKEOPTS', '')
    if makeopts:
        cmd += ' %s' % makeopts
    if extra_args:
        cmd += ' %s' % extra_args
    make_process = process.system(cmd, ignore_status=ignore_status)
    os.chdir(cwd)
    return make_process
