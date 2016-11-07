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

from . import process


def run_make(path, make='make', env=None, extra_args='', ignore_status=None,
             allow_output_check=None, process_kwargs=None):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param make: what make command name to use.
    :param env: dictionary with environment variables to be set before
                calling make (e.g.: CFLAGS).
    :param extra: extra command line arguments to pass to make.
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) of the make process in
                               the test stream files. Valid values: 'stdout',
                               for allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error,
                               and 'none', to allow none to be
                               recorded (default). The default here is
                               'none', because usually we don't want
                               to use the compilation output as a reference
                               in tests.
    :param process_kwargs: Additional key word arguments to the underlying
                           process running the make.
    :type allow_output_check: str
    :returns: the make command result object
    """
    cwd = os.getcwd()
    os.chdir(path)
    cmd = make

    # Set default number of jobs as ncpus + 1
    if "-j" not in os.environ.get("MAKEFLAGS", ""):
        jobs = multiprocessing.cpu_count() + 1
        if not env:
            env = {"MAKEFLAGS": "-j%s" % jobs}
        elif "-j" not in env:
            env["MAKEFLAGS"] = "-j%s" % jobs

    makeopts = os.environ.get('MAKEOPTS', '')
    if makeopts:
        cmd += ' %s' % makeopts
    if extra_args:
        cmd += ' %s' % extra_args

    # Compatibility with 36LTS
    # process_kwargs was added in 43.0 and supersedes the old way of
    # specifying the process's arguments. When 36LTS is discontinued the
    # ignore_status, allow_output_check and env args should be removed.
    if process_kwargs is None:
        process_kwargs = {}
    if ignore_status is not None:   # Compatibility with 36LTS
        process_kwargs["ignore_status"] = ignore_status
    if allow_output_check is not None:  # Compatibility with 36LTS
        process_kwargs["allow_output_check"] = allow_output_check
    else:
        process_kwargs["allow_output_check"] = "none"
    if env:     # Compatibility with 36LTS
        if process_kwargs.get("env"):
            process_kwargs["env"].update(env)
        else:
            process_kwargs["env"] = env
    make_process = process.run(cmd,
                               **process_kwargs)
    os.chdir(cwd)
    return make_process


def make(path, make='make', env=None, extra_args='', ignore_status=None,
         allow_output_check=None, process_kwargs=None):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param make: what make command name to use.
    :param env: dictionary with environment variables to be set before
                calling make (e.g.: CFLAGS).
    :param extra: extra command line arguments to pass to make.
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) of the make process in
                               the test stream files. Valid values: 'stdout',
                               for allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error,
                               and 'none', to allow none to be
                               recorded (default). The default here is
                               'none', because usually we don't want
                               to use the compilation output as a reference
                               in tests.
    :type allow_output_check: str
    :returns: exit status of the make process
    """

    result = run_make(path, make, env, extra_args, ignore_status,
                      allow_output_check)

    return result.exit_status
