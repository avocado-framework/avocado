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
# Copyright: Red Hat Inc. 2018
# Authors: Amador Pahim <apahim@redhat.com>

"""
Plugin to run GLib Test Framework tests in Avocado
"""

import os
import re

from avocado.core import loader, output, test
from avocado.core.nrunner import Runnable
from avocado.core.plugin_interfaces import CLI, Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult)
from avocado.core.settings import settings
from avocado.utils import path, process


class GLibTest(test.SimpleTest):

    """
    Run a GLib test command as a SIMPLE test.
    """

    @property
    def filename(self):
        """
        Returns the path of the GLib test suite.
        """
        return self._filename.split(':')[0]

    def test(self):
        """
        Create the GLib command and execute it.
        """
        test_name = self._filename.split(':')[1]
        cmd = '%s -p=%s' % (self.filename, test_name)
        result = process.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            self.fail('GLib Test execution returned a '
                      'non-0 exit code (%s)' % result)


class NotGLibTest:

    """
    Not a GLib Test (for reporting purposes)
    """


class GLibLoader(loader.TestLoader):
    """
    GLib Test loader class
    """
    name = "glib"

    def discover(self, reference, which_tests=loader.DiscoverMode.DEFAULT):
        avocado_suite = []
        subtests_filter = None
        unsafe = settings.as_dict().get('plugins.glib.unsafe')

        if reference is None:
            return []

        if ':' in reference:
            reference, _subtests_filter = reference.split(':', 1)
            subtests_filter = re.compile(_subtests_filter)

        if (os.path.isfile(reference) and
                path.PathInspector(reference).has_exec_permission() and
                unsafe):
            try:
                cmd = '%s -l' % (reference)
                result = process.run(cmd)
            except Exception as details:  # pylint: disable=W0703
                if which_tests == loader.DiscoverMode.ALL:
                    return [(NotGLibTest,
                             {"name": "%s: %s" % (reference, details)})]
                return []

            for test_item in result.stdout_text.splitlines():
                test_name = "%s:%s" % (reference, test_item)
                if subtests_filter and not subtests_filter.search(test_name):
                    continue
                avocado_suite.append((GLibTest, {'name': test_name,
                                                 'executable': test_name}))

        if which_tests == loader.DiscoverMode.ALL and not avocado_suite:
            return [(NotGLibTest,
                     {"name": "%s: No GLib-like tests found" % reference})]
        return avocado_suite

    @staticmethod
    def get_type_label_mapping():
        return {GLibTest: 'GLIB',
                NotGLibTest: "!GLIB"}

    @staticmethod
    def get_decorator_mapping():
        return {GLibTest: output.TERM_SUPPORT.healthy_str,
                NotGLibTest: output.TERM_SUPPORT.fail_header_str}


class GLibResolver(Resolver):

    name = 'glib'
    description = 'Test resolver for GLib tests'

    @staticmethod
    def resolve(reference):
        unsafe = settings.as_dict().get('plugins.glib.unsafe')
        if (os.path.isfile(reference) and
                os.access(reference, os.R_OK) and
                unsafe):
            try:
                cmd = '%s -l' % (reference)
                result = process.run(cmd)
            except Exception as details:  # pylint: disable=W0703
                return ReferenceResolution(reference,
                                           ReferenceResolutionResult.ERROR,
                                           info=details,
                                           origin=GLibResolver.name)
            runnables = []
            for test_item in result.stdout_text.splitlines():
                uri = "%s:%s" % (reference, test_item)
                runnables.append(Runnable('glib', uri))
            if runnables:
                return ReferenceResolution(reference,
                                           ReferenceResolutionResult.SUCCESS,
                                           runnables)
        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.NOTFOUND)


class GLibCLI(CLI):

    """
    Run GLib Test Framework tests
    """

    name = 'glib'
    description = "GLib Framework options for 'run' subcommand"

    def configure(self, parser):
        settings.register_option(section='plugins.glib',
                                 key='unsafe',
                                 key_type=bool,
                                 default=False,
                                 help_msg='Force unsafe mode.')

    def run(self, config):
        loader.loader.register_plugin(GLibLoader)
