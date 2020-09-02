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
# Copyright: Red Hat Inc. 2019
# Authors: Willian Rampazzo <willianr@redhat.com>

"""
Assets subcommand
"""

import ast
import os
import urllib.parse

from avocado.core import data_dir, exit_codes, safeloader
from avocado.core.nrunner import Task
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd, JobPreTests
from avocado.core.settings import settings
from avocado.utils import data_structures
from avocado.utils.asset import Asset


class FetchAssetHandler(ast.NodeVisitor):  # pylint: disable=R0902
    """
    Handles the parsing of instrumented tests for `fetch_asset` statements.
    """

    PATTERN = 'fetch_asset'

    def __init__(self, file_name, klass=None, method=None):
        self.file_name = file_name
        # fetch assets from specific test using klass and method
        self.klass = klass
        # we need to make sure we cover the setUp method when fetching
        # assets for a specific test
        self.method = [method, 'setUp']
        self.asgmts = {}
        self.calls = []

        # hold current class and current method to make sure we have the
        # correct context for the assignment statement.
        # at this time, module constants and class attributes are discarded.
        self.current_klass = None
        self.current_method = None

        # check if we have valid instrumented tests
        # discards disabled tests
        self.tests = safeloader.find_avocado_tests(self.file_name)[0]

        # create Abstract Syntax Tree from test source file
        with open(self.file_name) as source_file:
            self.tree = ast.parse(source_file.read(), self.file_name)

        # build list of keyword arguments from calls that match pattern
        self.visit(self.tree)

    def _parse_args(self, node):
        """
        Parse the AST fetch_asset node and build the arguments dictionary.
        :param node: AST node to be evaluated
        :type node: ast.Attribute
        :returns: keywords and arguments from a fetch_asset call.
        :rtype: dict
        """
        args = []
        # variables to make lines shorter
        cur_klass = self.current_klass
        cur_method = self.current_method

        # parse args from call
        for arg in node.args:
            # handle string args
            if isinstance(arg, ast.Str):
                args.append(arg.s)
            # handle variable args
            elif isinstance(arg, ast.Name):
                # look for assignments at method
                if arg.id in self.asgmts[cur_klass][cur_method]:
                    args.append(self.asgmts[cur_klass][cur_method][arg.id])
                # right now we support just one level of variable as argument,
                # with a pure string assignment, in the same context,
                # just like `name = 'file.zip'`
                else:
                    return None

        # starts building the keywords dictionary for the asset.Asset()
        # class constructor.
        keywords = ["name", "asset_hash", "algorithm", "locations", "expire"]
        fetch_args = dict(zip(keywords, args))

        # parse keyword args for call
        for kwarg in node.keywords:
            # variable to make lines shorter
            kword = kwarg.arg
            # handle `keyword = string`
            if isinstance(kwarg.value, ast.Str):
                fetch_args[kword] = kwarg.value.s
            # handle `keyword = variable`
            elif isinstance(kwarg.value, ast.Name):
                name = kwarg.value.id
                # look for assignments at method
                if name in self.asgmts[cur_klass][cur_method]:
                    fetch_args[kword] = self.asgmts[cur_klass][cur_method][name]
                # right now we support just one level of variable as argument,
                # with a pure string assignment, in the same context,
                # just like `name = 'file.zip'`
                else:
                    return None

        # Fill empty keywords with None
        for kword in keywords:
            if kword not in fetch_args:
                fetch_args[kword] = None

        return fetch_args

    def visit_ClassDef(self, node):  # pylint: disable=C0103
        """
        Visit ClassDef on AST and save current Class.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        if node.name in self.tests:
            if self.klass and node.name != self.klass:
                return

            # reset the current method pointer
            self.current_method = None
            self.current_klass = node.name
            self.asgmts[self.current_klass] = {}
            self.generic_visit(node)

    def visit_FunctionDef(self, node):  # pylint: disable=C0103
        """
        Visit FunctionDef on AST and save current method.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        # make sure we are into a class method and not a function
        if self.current_klass:
            if self.method[0] and node.name not in self.method:
                return

            self.current_method = node.name
            self.asgmts[self.current_klass][self.current_method] = {}
        self.generic_visit(node)

    def visit_Assign(self, node):  # pylint: disable=C0103
        """
        Visit Assign on AST and build list of assignments that matches the
        pattern pattern `name = string`.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        if isinstance(node.value, ast.Str):
            # make sure we are into a class method, we are not supporting
            # attributes and module constant assignments at this time
            if self.current_klass and self.current_method:
                # variables to make dictionary assignment line shorter
                cur_klass = self.current_klass
                cur_method = self.current_method
                # if it is a class attribute, save the attribute name
                # otherwise, save the local variable name
                if isinstance(node.targets[0], ast.Attribute):
                    name = node.targets[0].attr
                else:
                    name = node.targets[0].id
                self.asgmts[cur_klass][cur_method][name] = node.value.s
        self.generic_visit(node)

    def visit_Call(self, node):  # pylint: disable=C0103
        """
        Visit Calls on AST and build list of calls that matches the pattern.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        # make sure we are into a class method
        if self.current_klass and self.current_method:
            if isinstance(node.func, ast.Attribute):
                if self.PATTERN in node.func.attr:
                    call = self._parse_args(node)
                    if call:
                        self.calls.append(call)


def fetch_assets(test_file, klass=None, method=None, logger=None):
    """
    Fetches the assets based on keywords listed on FetchAssetHandler.calls.
    :param test_file: File name of instrumented test to be evaluated
    :type test_file: str
    :returns: list of names that were successfully fetched and list of
    fails.
    """
    def validate_parameters(call):
        """
        Validate the parameters to make sure we have a supported case.

        :param call: List of parameter to the Asset object.
        :type call: dict
        :returns: True or False
        """
        name = call.get('name', None)
        locations = call.get('locations', None)
        # probably, parameter name was defined as a class attribute
        if ((name is None) or
                # probably, parameter locations was defined as a class attribute
                (not urllib.parse.urlparse(name).scheme and
                 locations is None)):
            return False
        return True

    cache_dirs = data_dir.get_cache_dirs()
    success = []
    fail = []
    handler = FetchAssetHandler(test_file, klass, method)
    for call in handler.calls:
        # validate the parameters
        if not validate_parameters(call):
            continue
        expire = call.pop('expire', None)
        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))
        try:
            # make dictionary unpacking compatible with python 3.4 as it does
            # not support constructions like:
            # Asset(**call, cache_dirs=cache_dirs, expire=expire)
            call['cache_dirs'] = cache_dirs
            call['expire'] = expire
            asset_obj = Asset(**call)
            if logger is not None:
                logger.info('Fetching asset from %s:%s.%s',
                            test_file, klass, method)
            asset_obj.fetch()
            success.append(call['name'])
        except (OSError, ValueError) as failed:
            fail.append(failed)
    return success, fail


class FetchAssetJob(JobPreTests):  # pylint: disable=R0903
    """
    Implements the assets fetch job pre tests. This has the same effect of
    running the 'avocado assets fetch INSTRUMENTED', but it runs during the
    test execution, before the actual test starts.
    """
    name = "fetchasset"
    description = "Fetch assets before the test run"

    def __init__(self, config=None):
        pass

    def pre_tests(self, job):
        if not job.config.get('stdout_claimed_by', None):
            logger = job.log
        else:
            logger = None
        for suite in job.test_suites:
            for test in suite.tests:
                # ignore nrunner/resolver based test suites that contain
                # task, because the requirements resolution planned is
                # completely different from the traditional job runner
                if isinstance(test, Task):
                    continue
                # fetch assets only on instrumented tests
                if isinstance(test[0], str):
                    fetch_assets(test[1]['modulePath'],
                                 test[0],
                                 test[1]['methodName'],
                                 logger)


class Assets(CLICmd):
    """
    Implements the avocado 'assets' subcommand
    """
    name = 'assets'
    description = 'Manage assets'

    def configure(self, parser):
        """
        Add the subparser for the assets action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super(Assets, self).configure(parser)

        subcommands = parser.add_subparsers(dest='assets_subcommand')
        subcommands.required = True

        fetch_subcommand_parser = subcommands.add_parser(
            'fetch',
            help='Fetch assets from test source or config file if it\'s not'
            ' already in the cache')
        help_msg = "Path to avocado instrumented test"
        settings.register_option(section='assets.fetch',
                                 key='references',
                                 help_msg=help_msg,
                                 default=[],
                                 metavar='AVOCADO_INSTRUMENTED',
                                 key_type=list,
                                 nargs='+',
                                 parser=fetch_subcommand_parser,
                                 positional_arg=True)

        help_msg = "always return success for the fetch command."
        settings.register_option(section='assets.fetch',
                                 key='ignore_errors',
                                 help_msg=help_msg,
                                 default=False,
                                 key_type=bool,
                                 parser=fetch_subcommand_parser,
                                 long_arg='--ignore-errors')

    def run(self, config):
        subcommand = config.get('assets_subcommand')
        # we want to let the command caller knows about fails
        exitcode = exit_codes.AVOCADO_ALL_OK

        if subcommand == 'fetch':
            # fetch assets from instrumented tests
            for test_file in config.get('assets.fetch.references'):
                if os.path.isfile(test_file) and test_file.endswith('.py'):
                    LOG_UI.debug('Fetching assets from %s.', test_file)
                    success, fail = fetch_assets(test_file)

                    for asset_file in success:
                        LOG_UI.debug('  File %s fetched or already on'
                                     ' cache.', asset_file)
                    for asset_file in fail:
                        LOG_UI.error(asset_file)

                    if fail:
                        exitcode |= exit_codes.AVOCADO_FAIL
                else:
                    LOG_UI.warning('No such file or file not supported: %s',
                                   test_file)
                    exitcode |= exit_codes.AVOCADO_FAIL

            # check if we should ignore the errors
            if config.get('assets.fetch.ignore_errors'):
                exitcode = exit_codes.AVOCADO_ALL_OK

        return exitcode
