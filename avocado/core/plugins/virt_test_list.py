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

from avocado.core import output
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

from virttest import data_dir
from virttest import standalone_test

data_dir.get_data_dir = avocado_data_dir.get_data_dir

from virttest.standalone_test import SUPPORTED_TEST_TYPES


from virt_test import VirtTestOptionsProcess


def print_test_list(options, cartesian_parser, view):
    """
    Helper function to pretty print the test list.

    This function uses a paginator, if possible (inspired on git).

    :param options: OptParse object with cmdline options.
    :param cartesian_parser: Cartesian parser object with test options.
    """
    index = 0

    view.notify(event='minor', msg=standalone_test.get_cartesian_parser_details(cartesian_parser))
    if options.tests:
        tests = options.tests.split(" ")
        cartesian_parser.only_filter(", ".join(tests))
    for params in cartesian_parser.get_dicts():
        virt_test_type = params.get('virt_test_type', "")
        supported_virt_backends = virt_test_type.split(" ")
        if options.type in supported_virt_backends:
            index += 1
            shortname = params.get("_short_name_map_file")["subtests.cfg"]
            needs_root = ((params.get('requires_root', 'no') == 'yes') or
                          (params.get('vm_type') != 'qemu'))
            basic_out = (standalone_test.bcolors.blue + str(index) + standalone_test.bcolors.end + " " +
                         shortname)
            if needs_root:
                out = (basic_out + standalone_test.bcolors.yellow + " (requires root)" +
                       standalone_test.bcolors.end + "\n")
            else:
                out = basic_out + "\n"
            view.notify(event='minor', msg=out)


class VirtTestLister(plugin.Plugin):

    """
    Implements the avocado 'vt-list' subcommand
    """

    name = 'virt_test_compat_lister'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser('vt-list',
                                                    help='List tests available by the virt test compatibility layer')
        self.parser.add_argument("--vt-type", action="store", dest="type",
                                 help="Choose test type (%s)" % ", ".join(SUPPORTED_TEST_TYPES),
                                 default='qemu')
        self.parser.add_argument("--vt-list-tests", action="store_true", dest="list",
                                 help="List tests available")
        self.parser.add_argument("--vt-list-tests-filter", action="store", dest="test_list_filter", default='',
                                 help="Pattern used to filter tests (Ex: usb)")
        self.parser.add_argument("--vt-list-guests", action="store_true",
                                 dest="list_guests",
                                 help="List guests available")
        super(VirtTestLister, self).configure(self.parser)

    def run(self, args):
        if os.getuid() == 0:
            nettype_default = 'bridge'
        else:
            nettype_default = 'user'
        args.verbose = True
        args.log_level = 'debug'
        args.console_level = 'debug'
        args.datadir = data_dir.get_data_dir()
        args.config = None
        args.arch = None
        args.machine_type = None
        args.guest_os = None
        args.keep_guest_running = False
        args.keep_image_between_tests = False
        args.mem = 1024
        args.no_filter = ''
        args.qemu = None
        args.dst_qemu = None
        args.nettype = nettype_default
        args.only_type_specific = False
        args.tests = ''
        args.uri = ''
        args.accel = 'kvm'
        args.monitor = 'human'
        args.smp = 1
        args.image_type = 'qcow2'
        args.nic_model = 'virtio_net'
        args.disk_bus = 'virtio_blk'
        args.vhost = 'off'
        args.malloc_perturb = 'yes'
        args.qemu_sandbox = 'on'
        args.tests = args.test_list_filter

        class TestListJob(object):

            def __init__(self, args, view):
                self.args = args
                self.view = view

        view = output.View(app_args=args)
        test_list_job = TestListJob(args=args, view=view)
        vt_opt_process = VirtTestOptionsProcess(job=test_list_job)
        vt_opt_process.get_parser()
