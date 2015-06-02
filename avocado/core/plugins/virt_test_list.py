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
# Copyright: Red Hat Inc. 2015
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Avocado plugin that augments 'avocado list' with virt-test related options.
"""

import os
import sys

from avocado.settings import settings
from avocado.core.plugins import plugin

# virt-test supports using autotest from a git checkout, so we'll have to
# support that as well. The code below will pick up the environment variable
# $AUTOTEST_PATH and do the import magic needed to make the autotest library
# available in the system.
AUTOTEST_PATH = None

if 'AUTOTEST_PATH' in os.environ:
    AUTOTEST_PATH = os.path.expanduser(os.environ['AUTOTEST_PATH'])
    client_dir = os.path.join(os.path.abspath(AUTOTEST_PATH), 'client')
    setup_modules_path = os.path.join(client_dir, 'setup_modules.py')
    import imp
    setup_modules = imp.load_source('autotest_setup_modules',
                                    setup_modules_path)
    setup_modules.setup(base_path=client_dir,
                        root_module_name="autotest.client")

# The code below is used by this plugin to find the virt test directory,
# so that it can load the virttest python lib, used by the plugin code.
# If the user doesn't provide the proper configuration, the plugin will
# fail to load.
VIRT_TEST_DIR = None

if 'VIRT_TEST_DIR' in os.environ:
    VIRT_TEST_DIR = os.environ['VIRT_TEST_DIR']
else:
    VIRT_TEST_DIR = settings.get_value(section='virt_test', key='virt_test_dir', default=None)

if VIRT_TEST_DIR is not None:
    sys.path.append(os.path.expanduser(VIRT_TEST_DIR))

from virttest.standalone_test import SUPPORTED_TEST_TYPES
from virttest.defaults import DEFAULT_GUEST_OS


class VirtTestListerPlugin(plugin.Plugin):

    """
    Implements the avocado virt test options
    """

    name = 'virt_test_compat_lister'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        self.parser = parser
        vt_compat_group_lister = parser.lister.add_argument_group(
            'Virt-Test compat layer - Lister options')
        vt_compat_group_lister.add_argument("--vt-type", action="store",
                                            dest="vt_type",
                                            help="Choose test type (%s). "
                                                 "Default: qemu" %
                                            ", ".join(SUPPORTED_TEST_TYPES),
                                            default='qemu')
        vt_compat_group_lister.add_argument("--vt-guest-os", action="store",
                                            dest="vt_guest_os",
                                            default=None,
                                            help=("Select the guest OS to be "
                                                  "used (different guests "
                                                  "support different test "
                                                  "lists). You can list "
                                                  "available guests "
                                                  "with --vt-list-guests. "
                                                  "Default: %s" %
                                                  DEFAULT_GUEST_OS))
        vt_compat_group_lister.add_argument("--vt-list-guests",
                                            action="store_true",
                                            default=False,
                                            help="List available guests")
