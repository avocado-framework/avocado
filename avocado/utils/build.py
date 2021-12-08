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

import multiprocessing
import os

from avocado.utils import process


def configure(path, configure=None):  # pylint: disable=W0621
    """
    Configures the source tree for a subsequent build

    Most source directories coming from official released tarballs
    will have a "configure" script, but source code snapshots may have
    "autogen.sh" instead (which usually creates and runs a "configure"
    script itself).  This function will attempt to run the first one
    found (if a configure script name not given explicitly).

    :param configure: the name of the configure script (None for trying to
                      find one automatically)
    :type configure: str or None
    :returns: the configure script exit status, or None if no script was
              found and executed
    """
    cwd = os.getcwd()
    try:
        os.chdir(path)
        if configure is not None:
            return process.run(os.path.join(path, configure)).exit_status

        candidates = ['autogen.sh', 'configure']
        for configure in candidates:
            if os.access(configure, os.R_OK | os.X_OK):
                return process.run(os.path.join(path, configure)).exit_status
    finally:
        os.chdir(cwd)


def run_make(path, make='make', extra_args='', process_kwargs=None):  # pylint: disable=W0621
    """
    Run make, adding MAKEOPTS to the list of options.

    :param path: directory from where to run make
    :param make: what make command name to use.
    :param extra_args: extra command line arguments to pass to make.
    :param process_kwargs: Additional key word arguments to the underlying
                           process running the make.
    :returns: the make command result object
    """
    cwd = os.getcwd()
    os.chdir(path)
    cmd = make

    if process_kwargs is None:
        process_kwargs = {}
    # Set default number of jobs as ncpus + 1
    os_makeflags = os.environ.get('MAKEFLAGS', '')
    if process_kwargs.get('env') is None:
        process_kwargs['env'] = {}
    args_makeflags = process_kwargs['env'].get('MAKEFLAGS', '')

    if '-j' not in os_makeflags and '-j' not in args_makeflags:
        args_makeflags += ' -j%s' % (multiprocessing.cpu_count() + 1)
        process_kwargs['env'].update({'MAKEFLAGS': args_makeflags})

    makeopts = os.environ.get('MAKEOPTS', '')
    if makeopts:
        cmd += ' %s' % makeopts
    if extra_args:
        cmd += ' %s' % extra_args

    make_process = process.run(cmd, **process_kwargs)
    os.chdir(cwd)
    return make_process


def make(path, make='make', env=None, extra_args='', ignore_status=None,  # pylint: disable=W0621
         process_kwargs=None):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param make: what make command name to use.
    :param env: dictionary with environment variables to be set before
                calling make (e.g.: CFLAGS).
    :param extra: extra command line arguments to pass to make.
    :returns: exit status of the make process
    """

    kwargs = dict(env=env,
                  ignore_status=ignore_status)
    if process_kwargs is not None:
        kwargs.update(process_kwargs)
    result = run_make(path, make, extra_args, kwargs)

    return result.exit_status
