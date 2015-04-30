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

import os
import sys

from avocado.core.plugins import plugin
from avocado import data_dir as avocado_data_dir
from avocado.settings import settings
from avocado.settings import config_path_local

if 'VIRT_TEST_DIR' in os.environ:
    virt_test_dir = os.environ['VIRT_TEST_DIR']
else:
    virt_test_dir = settings.get_value(section='virt-test', key='test_suite_path', default=None)
    if virt_test_dir is None or not os.path.isdir(virt_test_dir):
        print('Virt test dir not set/invalid. Please make sure you add to %s' % config_path_local)
        print('')
        print('[virt-test]')
        print('test_suite_path=/valid/path/to/virt_test')
        print('')
        print('If you are working from an avocado source code repo, please')
        print('$ export VIRT_TEST_DIR="/valid/path/to/virt_test"')
        sys.exit(1)

sys.path.append(os.path.expanduser(virt_test_dir))

from virttest import arch
from virttest import bootstrap
from virttest import data_dir
from virttest import defaults

data_dir.get_data_dir = avocado_data_dir.get_data_dir

from virttest.standalone_test import SUPPORTED_TEST_TYPES


class VirtBootstrap(plugin.Plugin):

    """
    Implements the avocado 'vt-bootstrap' subcommand
    """

    name = 'virt_test_compat_bootstrap'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser('vt-bootstrap',
                                                    help='Setup tests for the virt test compatibility layer')
        self.parser.add_argument("--vt-type", action="store", dest="type",
                                 help="Choose test type (%s)" % ", ".join(SUPPORTED_TEST_TYPES),
                                 default='qemu')
        self.parser.add_argument("--vt-guest-os", action="store", dest="guest_os",
                                 default=None,
                                 help=("Select the guest OS to be used. "
                                       "If -c is provided, this will be ignored. "
                                       "Default: %s" % defaults.DEFAULT_GUEST_OS))
        self.parser.add_argument("--vt-selinux-setup", action="store_true",
                                 dest="selinux_setup", default=False,
                                 help="Define default contexts of directory.")
        self.parser.add_argument("--vt-no-downloads", action="store_true",
                                 dest="no_downloads", default=False,
                                 help="Do not attempt to download JeOS images")
        self.parser.add_argument("--vt-update-config", action="store_true",
                                 default=False,
                                 dest="update_config", help=("Forces configuration "
                                                             "updates (all manual "
                                                             "config file editing "
                                                             "will be lost). "
                                                             "Requires --vt-type to be set"))
        self.parser.add_argument("--vt-update-providers", action="store_true",
                                 default=False,
                                 dest="update_providers", help=("Forces test "
                                                                "providers to be "
                                                                "updated (git repos "
                                                                "will be pulled)"))
        super(VirtBootstrap, self).configure(self.parser)

    def run(self, args):
        if args.update_config:
            test_dir = data_dir.get_backend_dir(args.type)
            shared_dir = os.path.join(data_dir.get_root_dir(), "shared")
            bootstrap.create_config_files(test_dir, shared_dir,
                                          interactive=True,
                                          force_update=False)
            bootstrap.create_subtests_cfg(args.type)
            bootstrap.create_guest_os_cfg(args.type)
            sys.exit(0)

        check_modules = []
        online_docs_url = None
        interactive = True
        default_userspace_paths = []

        if args.type == "qemu":
            default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
            check_modules = arch.get_kvm_module_list()
            online_docs_url = "https://github.com/autotest/virt-test/wiki/GetStarted"
        elif args.type == "libvirt":
            default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
        elif args.type == "libguestfs":
            default_userspace_paths = ["/usr/bin/libguestfs-test-tool"]
        elif args.type == "lvsb":
            default_userspace_paths = ["/usr/bin/virt-sandbox"]
        elif args.type == "openvswitch":
            default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
            check_modules = ["openvswitch"]
            online_docs_url = "https://github.com/autotest/autotest/wiki/OpenVSwitch"
        elif args.type == "v2v":
            default_userspace_paths = ["/usr/bin/virt-v2v"]

        restore_image = not args.no_downloads

        test_dir = data_dir.get_backend_dir(args.type)
        bootstrap.bootstrap(test_name=args.type, test_dir=test_dir,
                            base_dir=avocado_data_dir.get_data_dir(),
                            default_userspace_paths=default_userspace_paths,
                            check_modules=check_modules,
                            online_docs_url=online_docs_url,
                            interactive=interactive,
                            selinux=args.selinux_setup,
                            restore_image=restore_image,
                            verbose=True,
                            update_providers=args.update_providers,
                            guest_os=(args.guest_os or
                                      defaults.DEFAULT_GUEST_OS))
        sys.exit(0)
