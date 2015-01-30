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

from avocado import loader
from avocado import test
from avocado.core import data_dir
from avocado.core import output
from avocado.core import exit_codes
from avocado.utils import astring
from avocado.plugins import plugin


class TestLister(plugin.Plugin):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'test_lister'
    enabled = True
    view = None
    test_loader = loader.TestLoader()
    term_support = output.TermSupport()

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'list',
            help='List available test modules')
        self.parser.add_argument('paths', type=str, default=[], nargs='*',
                                 help="List of paths. If no paths provided, "
                                      "avocado will list tests on the "
                                      "configured test directory, "
                                      "see 'avocado config --datadir'")
        self.parser.add_argument('-V', '--verbose',
                                 action='store_true', default=False,
                                 help='Whether to show extra information '
                                      '(headers and summary). Current: %('
                                      'default)s')
        super(TestLister, self).configure(self.parser)

    def _run(self, args):
        """
        List available test modules.

        :param args: Command line args received from the list subparser.
        """
        self.view = output.View(app_args=args)

        paths = [data_dir.get_test_dir()]
        if args.paths:
            paths = args.paths
        params_list = self.test_loader.discover_urls(paths)
        for params in params_list:
            params['omit_non_tests'] = False
        test_suite = self.test_loader.discover(params_list)
        error_msg_parts = self.test_loader.validate_ui(test_suite,
                                                       ignore_not_test=True,
                                                       ignore_access_denied=True,
                                                       ignore_broken_symlinks=True)
        if error_msg_parts:
            for error_msg in error_msg_parts:
                self.view.notify(event='error', msg=error_msg)
            sys.exit(exit_codes.AVOCADO_FAIL)

        test_matrix = []
        stats = {'simple': 0,
                 'instrumented': 0,
                 'buggy': 0,
                 'missing': 0,
                 'not_a_test': 0,
                 'broken_symlink': 0,
                 'access_denied': 0}
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

            if cls == test.SimpleTest:
                stats['simple'] += 1
                type_label = self.term_support.healthy_str('SIMPLE')
            elif cls == test.BuggyTest:
                stats['buggy'] += 1
                type_label = self.term_support.fail_header_str('BUGGY')
            elif cls == test.NotATest:
                if not args.verbose:
                    continue
                stats['not_a_test'] += 1
                type_label = self.term_support.warn_header_str('NOT_A_TEST')
            elif cls == test.MissingTest:
                stats['missing'] += 1
                type_label = self.term_support.fail_header_str('MISSING')
            elif cls == loader.BrokenSymlink:
                stats['broken_symlink'] += 1
                type_label = self.term_support.fail_header_str('BROKEN_SYMLINK')
            elif cls == loader.AccessDeniedPath:
                stats['access_denied'] += 1
                type_label = self.term_support.fail_header_str('ACCESS_DENIED')
            else:
                if issubclass(cls, test.Test):
                    stats['instrumented'] += 1
                    type_label = self.term_support.healthy_str('INSTRUMENTED')

            test_matrix.append((type_label, id_label))

        header = None
        if args.verbose:
            header = (self.term_support.header_str('Type'),
                      self.term_support.header_str('file'))
        for line in astring.tabular_output(test_matrix,
                                           header=header).splitlines():
            self.view.notify(event='minor', msg="%s" % line)

        if args.verbose:
            self.view.notify(event='minor', msg='')

            self.view.notify(event='message', msg=("SIMPLE: %s" %
                                                   stats['simple']))
            self.view.notify(event='message', msg=("INSTRUMENTED: %s" %
                                                   stats['instrumented']))
            self.view.notify(event='message', msg=("BUGGY: %s" %
                                                   stats['buggy']))
            self.view.notify(event='message', msg=("MISSING: %s" %
                                                   stats['missing']))
            self.view.notify(event='message', msg=("NOT_A_TEST: %s" %
                                                   stats['not_a_test']))
            self.view.notify(event='message', msg=("ACCESS_DENIED: %s" %
                                                   stats['access_denied']))
            self.view.notify(event='message', msg=("BROKEN_SYMLINK: %s" %
                                                   stats['broken_symlink']))

    def run(self, args):
        try:
            self._run(args)
        except KeyboardInterrupt:
            msg = ('Command interrupted by '
                   'user...')
            if self.view is not None:
                self.view.notify(event='error', msg=msg)
            else:
                sys.stderr.write(msg)
            sys.exit(exit_codes.AVOCADO_FAIL)
