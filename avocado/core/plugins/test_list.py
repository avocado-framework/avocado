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

import sys

from avocado import test
from avocado import data_dir
from avocado.core import loader
from avocado.core import output
from avocado.core import exit_codes
from avocado.utils import astring
from avocado.core.plugins import plugin


class TestLister(object):

    """
    Lists available test modules
    """

    def __init__(self, args):
        use_paginator = args.paginator == 'on'
        self.view = output.View(app_args=args, use_paginator=use_paginator)
        self.term_support = output.TermSupport()
        self.test_loader = loader.TestLoader()
        self.args = args

    def _set_paths(self):
        paths = [data_dir.get_test_dir()]
        if self.args.paths:
            paths = self.args.paths
        return paths

    def _get_test_suite(self, paths):
        params_list = self.test_loader.discover_urls(paths)
        for params in params_list:
            params['omit_non_tests'] = False
        return self.test_loader.discover(params_list)

    def _validate_test_suite(self, test_suite):
        error_msg_parts = self.test_loader.validate_ui(test_suite,
                                                       ignore_not_test=True,
                                                       ignore_access_denied=True,
                                                       ignore_broken_symlinks=True)
        if error_msg_parts:
            for error_msg in error_msg_parts:
                self.view.notify(event='error', msg=error_msg)
            self.view.cleanup()
            sys.exit(exit_codes.AVOCADO_FAIL)

    def _get_test_matrix(self, test_suite):
        test_matrix = []

        type_label_mapping = {test.SimpleTest: 'SIMPLE',
                              test.BuggyTest: 'BUGGY',
                              test.NotATest: 'NOT_A_TEST',
                              test.MissingTest: 'MISSING',
                              loader.BrokenSymlink: 'BROKEN_SYMLINK',
                              loader.AccessDeniedPath: 'ACCESS_DENIED',
                              test.Test: 'INSTRUMENTED'}

        decorator_mapping = {test.SimpleTest: self.term_support.healthy_str,
                             test.BuggyTest: self.term_support.fail_header_str,
                             test.NotATest: self.term_support.warn_header_str,
                             test.MissingTest: self.term_support.fail_header_str,
                             loader.BrokenSymlink: self.term_support.fail_header_str,
                             loader.AccessDeniedPath: self.term_support.fail_header_str,
                             test.Test: self.term_support.healthy_str}

        stats = {}
        for value in type_label_mapping.values():
            stats[value.lower()] = 0

        for cls, params in test_suite:
            id_label = ''
            type_label = cls.__name__

            if 'params' in params:
                id_label = params['params']['id']
            else:
                if 'name' in params:
                    id_label = params['name']
                elif 'path' in params:
                    id_label = params['path']

            try:
                type_label = type_label_mapping[cls]
                decorator = decorator_mapping[cls]
                stats[type_label.lower()] += 1
                type_label = decorator(type_label)
            except KeyError:
                if issubclass(cls, test.Test):
                    cls = test.Test
                    type_label = type_label_mapping[cls]
                    decorator = decorator_mapping[cls]
                    stats[type_label.lower()] += 1
                    type_label = decorator(type_label)
                    id_label = params['name']

            test_matrix.append((type_label, id_label))

        return test_matrix, stats

    def _display(self, test_matrix, stats):
        header = None
        if self.args.verbose:
            header = (self.term_support.header_str('Type'), self.term_support.header_str('ID'))

        for line in astring.tabular_output(test_matrix, header=header).splitlines():
            self.view.notify(event='minor', msg="%s" % line)

        if self.args.verbose:
            self.view.notify(event='minor', msg='')
            for key in sorted(stats):
                self.view.notify(event='message', msg=("%s: %s" % (key.upper(), stats[key])))

    def _list(self):
        paths = self._set_paths()
        test_suite = self._get_test_suite(paths)
        self._validate_test_suite(test_suite)
        test_matrix, stats = self._get_test_matrix(test_suite)
        self._display(test_matrix, stats)

    def list(self):
        rc = 0
        try:
            self._list()
        except KeyboardInterrupt:
            rc = exit_codes.AVOCADO_FAIL
            msg = 'Command interrupted by user...'
            if self.view is not None:
                self.view.notify(event='error', msg=msg)
            else:
                sys.stderr.write(msg)
        finally:
            if self.view:
                self.view.cleanup()
        return rc


class TestList(plugin.Plugin):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'test_lister'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser('list', help='List available test modules')
        self.parser.add_argument('paths', type=str, default=[], nargs='*',
                                 help="List of paths. If no paths provided, "
                                      "avocado will list tests on the "
                                      "configured test directory, "
                                      "see 'avocado config --datadir'")
        self.parser.add_argument('-V', '--verbose',
                                 action='store_true', default=False,
                                 help='Whether to show extra information '
                                      '(headers and summary). Current: %(default)s')
        self.parser.add_argument('--paginator',
                                 choices=('on', 'off'), default='on',
                                 help='Turn the paginator on/off. '
                                      'Current: %(default)s')
        super(TestList, self).configure(self.parser)

    def run(self, args):
        test_lister = TestLister(args)
        return test_lister.list()
