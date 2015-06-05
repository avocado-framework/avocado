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
        self.test_loader = loader.TestLoaderProxy()
        self.test_loader.load_plugins(args)
        self.args = args

    def _extra_listing(self):
        self.test_loader.get_extra_listing(self.args)

    def _get_keywords(self):
        keywords = self.test_loader.get_base_keywords()
        if self.args.keywords:
            keywords = self.args.keywords
        return keywords

    def _get_test_suite(self, paths):
        return self.test_loader.discover(paths, list_non_tests=self.args.verbose)

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

        type_label_mapping = self.test_loader.get_type_label_mapping()
        decorator_mapping = self.test_loader.get_decorator_mapping()

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
            header = (self.term_support.header_str('Type'), self.term_support.header_str('Test'))

        for line in astring.tabular_output(test_matrix, header=header).splitlines():
            self.view.notify(event='minor', msg="%s" % line)

        if self.args.verbose:
            self.view.notify(event='minor', msg='')
            for key in sorted(stats):
                self.view.notify(event='message', msg=("%s: %s" % (key.upper(), stats[key])))

    def _list(self):
        self._extra_listing()
        keywords = self._get_keywords()
        test_suite = self._get_test_suite(keywords)
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
    priority = 0

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser('list', help='List available test modules')
        self.parser.add_argument('keywords', type=str, default=[], nargs='*',
                                 help="List of paths, aliases or other "
                                      "keywords used to locate tests. "
                                      "If empty, avocado will list tests on "
                                      "the configured test source, "
                                      "(see 'avocado config --datadir') Also, "
                                      "if there are other test loader plugins "
                                      "active, tests from those plugins might "
                                      "also show up (behavior may vary among "
                                      "plugins)")
        self.parser.add_argument('-V', '--verbose',
                                 action='store_true', default=False,
                                 help='Whether to show extra information '
                                      '(headers and summary). Current: %(default)s')
        self.parser.add_argument('--paginator',
                                 choices=('on', 'off'), default='on',
                                 help='Turn the paginator on/off. '
                                      'Current: %(default)s')
        super(TestList, self).configure(self.parser)
        parser.lister = self.parser

    def run(self, args):
        test_lister = TestLister(args)
        return test_lister.list()
