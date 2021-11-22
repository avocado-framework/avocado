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
from datetime import datetime

from avocado.core import exit_codes, safeloader
from avocado.core.nrunner import Runnable
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd, JobPreTests
from avocado.core.settings import settings
from avocado.utils import data_structures
from avocado.utils.asset import SUPPORTED_OPERATORS, Asset
from avocado.utils.astring import iter_tabular_output
from avocado.utils.data_structures import DataSize, InvalidDataSize
from avocado.utils.output import display_data_size


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
        self.methods = [method, 'setUp']
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
        """Parse the AST fetch_asset node and build the arguments dictionary.

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
        """Visit ClassDef on AST and save current Class.

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
        """Visit FunctionDef on AST and save current method.

        :param node: AST node to be evaluated
        :type node: ast.*
        """
        # make sure we are into a class method and not a function
        if self.current_klass:
            if self.methods[0] and node.name not in self.methods:
                return

            self.current_method = node.name
            self.asgmts[self.current_klass][self.current_method] = {}
        self.generic_visit(node)

    @staticmethod
    def _ast_list_to_list(node):
        result = []
        for item in node.value.elts:
            if hasattr(item, 'value'):
                result.append(item.value)
        return result

    def visit_Assign(self, node):  # pylint: disable=C0103
        """Visit Assign on AST and build assignments.

        This method will visit and build list of assignments that matches the
        pattern pattern `name = string`.

        :param node: AST node to be evaluated
        :type node: ast.*
        """
        if isinstance(node.value, (ast.Str, ast.List)):
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

                if isinstance(node.value, ast.Str):
                    self.asgmts[cur_klass][cur_method][name] = node.value.s
                elif isinstance(node.value, ast.List):
                    self.asgmts[cur_klass][cur_method][name] = self._ast_list_to_list(node)

        self.generic_visit(node)

    def visit_Call(self, node):  # pylint: disable=C0103
        """Visit Calls on AST and build list of calls that matches the pattern.

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
    """Fetches the assets based on keywords listed on FetchAssetHandler.calls.

    :param test_file: File name of instrumented test to be evaluated
                      :type test_file: str
    :returns: list of names that were successfully fetched and list of
              fails.
    """
    cache_dirs = settings.as_dict().get('datadir.paths.cache_dirs')
    timeout = settings.as_dict().get('assets.fetch.timeout')
    success = []
    fail = []
    handler = FetchAssetHandler(test_file, klass, method)
    for call in handler.calls:
        expire = call.pop('expire', None)
        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))

        try:
            asset_obj = Asset(**call, cache_dirs=cache_dirs, expire=expire)
            if logger is not None:
                logger.info('Fetching asset from %s:%s.%s',
                            test_file, klass, method)
            asset_obj.fetch(timeout)
            success.append(call['name'])
        except (OSError, ValueError) as failed:
            fail.append(failed)
    return success, fail


class FetchAssetJob(JobPreTests):  # pylint: disable=R0903
    """Implements the assets fetch job pre tests.

    This has the same effect of running the 'avocado assets fetch
    INSTRUMENTED', but it runs during the test execution, before the actual
    test starts.
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
        candidates = []
        for suite in job.test_suites:
            for test in suite.tests:
                # ignore nrunner/resolver based test suites that contain
                # runnable, because the requirements resolution planned is
                # completely different from the traditional job runner
                if isinstance(test, Runnable):
                    continue

                # fetch assets only on instrumented tests
                if isinstance(test[0], str):
                    candidate = (test[1]['modulePath'],
                                 test[0],
                                 test[1]['methodName'])
                    if candidate not in candidates:
                        candidates.append(candidate)

        for candidate in candidates:
            fetch_assets(*candidate, logger)


class Assets(CLICmd):
    """
    Implements the avocado 'assets' subcommand
    """
    name = 'assets'
    description = 'Manage assets'

    @staticmethod
    def _count_filter_args(config):
        sub_command = config.get('assets_subcommand')
        args = [config.get("assets.{}.days".format(sub_command)),
                config.get("assets.{}.size_filter".format(sub_command)),
                config.get("assets.{}.overall_limit".format(sub_command))]
        return len([a for a in args if a is not None])

    def configure(self, parser):
        """Add the subparser for the assets action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        def register_filter_options(subparser, section):
            help_msg = ("Apply action based on a size filter (comparison "
                        "operator + value) in bytes. Ex '>20', '<=200'. "
                        "Supported operators: " +
                        ", ".join(SUPPORTED_OPERATORS))
            settings.register_option(section=section,
                                     key='size_filter',
                                     help_msg=help_msg,
                                     default=None,
                                     metavar="FILTER",
                                     key_type=str,
                                     long_arg='--by-size-filter',
                                     parser=subparser)

            help_msg = "How old (in days) should Avocado look for assets?"
            settings.register_option(section=section,
                                     key='days',
                                     help_msg=help_msg,
                                     default=None,
                                     key_type=int,
                                     metavar="DAYS",
                                     long_arg='--by-days',
                                     parser=subparser)

            help_msg = ("Filter will be based on a overall system limit "
                        "threshold in bytes (with assets ordered by last "
                        "access) or with a suffix unit. Valid suffixes are: ")
            help_msg += ','.join(DataSize.MULTIPLIERS.keys())

            settings.register_option(section=section,
                                     key='overall_limit',
                                     help_msg=help_msg,
                                     default=None,
                                     key_type=str,
                                     metavar="LIMIT",
                                     long_arg='--by-overall-limit',
                                     parser=subparser)

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

        help_msg = "Timeout to be used when download an asset."
        settings.register_option(section='assets.fetch',
                                 key='timeout',
                                 help_msg=help_msg,
                                 default=300,
                                 key_type=int,
                                 metavar="TIMEOUT",
                                 parser=fetch_subcommand_parser,
                                 long_arg='--timeout')

        register_subcommand_parser = subcommands.add_parser(
                'register',
                help='Register an asset directly to the cacche')

        help_msg = "Unique name to associate with this asset."
        settings.register_option(section='assets.register',
                                 key='name',
                                 help_msg=help_msg,
                                 default=None,
                                 key_type=str,
                                 parser=register_subcommand_parser,
                                 positional_arg=True)

        help_msg = "Path to asset that you would like to register manually."
        settings.register_option(section='assets.register',
                                 key='url',
                                 help_msg=help_msg,
                                 default=None,
                                 key_type=str,
                                 parser=register_subcommand_parser,
                                 positional_arg=True)

        help_msg = "SHA1 hash of this asset."
        settings.register_option(section='assets.register',
                                 key='sha1_hash',
                                 help_msg=help_msg,
                                 default=None,
                                 key_type=str,
                                 metavar="SHA1",
                                 long_arg='--hash',
                                 parser=register_subcommand_parser)

        purge_subcommand_parser = subcommands.add_parser(
                'purge',
                help='Removes assets cached locally.')
        register_filter_options(purge_subcommand_parser, 'assets.purge')

        help_msg = 'List all cached assets.'
        list_subcommand_parser = subcommands.add_parser(
                'list',
                help=help_msg)
        register_filter_options(list_subcommand_parser, 'assets.list')

    def handle_purge(self, config):
        days = config.get('assets.purge.days')
        size_filter = config.get('assets.purge.size_filter')
        overall_limit = config.get('assets.purge.overall_limit')

        if self._count_filter_args(config) != 1:
            msg = ("You should choose --by-size-filter or --by-days. "
                   "For help, run: avocado assets purge --help")
            LOG_UI.error(msg)
            return exit_codes.AVOCADO_FAIL

        cache_dirs = config.get('datadir.paths.cache_dirs')
        try:
            if days is not None:
                Asset.remove_assets_by_unused_for_days(days, cache_dirs)
            elif size_filter is not None:
                Asset.remove_assets_by_size(size_filter, cache_dirs)
            elif overall_limit is not None:
                try:
                    size = DataSize(overall_limit).b
                    Asset.remove_assets_by_overall_limit(size, cache_dirs)
                except InvalidDataSize:
                    error_msg = "You are using an invalid suffix. "
                    error_msg += "Use one of the following values: "
                    error_msg += ",".join(DataSize.MULTIPLIERS.keys())
                    LOG_UI.error(error_msg)
                    return exit_codes.AVOCADO_FAIL

        except (FileNotFoundError, OSError) as e:
            LOG_UI.error("Could not remove asset: %s", e)
            return exit_codes.AVOCADO_FAIL
        return exit_codes.AVOCADO_ALL_OK

    def handle_list(self, config):
        days = config.get('assets.list.days')
        size_filter = config.get('assets.list.size_filter')
        if self._count_filter_args(config) == 2:
            msg = ("You should choose --by-size-filter or --by-days. "
                   "For help, run: avocado assets list --help")
            LOG_UI.error(msg)
            return exit_codes.AVOCADO_FAIL

        cache_dirs = config.get('datadir.paths.cache_dirs')
        try:
            assets = None
            if days is not None:
                assets = Asset.get_assets_unused_for_days(days, cache_dirs)
            elif size_filter is not None:
                assets = Asset.get_assets_by_size(size_filter, cache_dirs)
            elif assets is None:
                assets = Asset.get_all_assets(cache_dirs)
        except (FileNotFoundError, OSError) as e:
            LOG_UI.error("Could get assets: %s", e)
            return exit_codes.AVOCADO_FAIL

        matrix = []
        for asset in assets:
            stat = os.stat(asset)
            basename = os.path.basename(asset)
            hash_path = "{}-CHECKSUM".format(asset)
            atime = datetime.fromtimestamp(stat.st_atime)
            _, checksum = Asset.read_hash_from_file(hash_path)
            matrix.append((basename,
                           str(checksum or "unknown")[:10],
                           atime.strftime('%Y-%m-%d %H:%M:%S'),
                           display_data_size(stat.st_size)))
        header = ("asset", "checksum", "atime", "size")
        output = list(iter_tabular_output(matrix, header))
        if len(output) == 1:
            LOG_UI.info("No asset found in your cache system.")
        else:
            for line in output:
                LOG_UI.info(line)

    @staticmethod
    def handle_fetch(config):
        exitcode = exit_codes.AVOCADO_ALL_OK
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
            return exit_codes.AVOCADO_ALL_OK
        return exitcode

    @staticmethod
    def handle_register(config):
        cache_dirs = config.get('datadir.paths.cache_dirs')
        name = config.get('assets.register.name')
        asset_hash = config.get('assets.register.sha1_hash')
        location = config.get('assets.register.url')
        # Adding a twice the location is a small hack due the current logic to
        # return "by_name". This needs to be improved soon.
        asset = Asset(name=name,
                      asset_hash=asset_hash,
                      locations=[location, location],
                      cache_dirs=cache_dirs)

        try:
            asset.find_asset_file()
            LOG_UI.error("Asset with name %s already registered.", name)
            return exit_codes.AVOCADO_WARNING
        except OSError:
            try:
                asset.fetch()
                LOG_UI.info("Done. Now you can reference it by name %s", name)
                return exit_codes.AVOCADO_ALL_OK
            except OSError as e:
                LOG_UI.error(e)
                return exit_codes.AVOCADO_FAIL

    def run(self, config):
        subcommand = config.get('assets_subcommand')

        if subcommand == 'fetch':
            return self.handle_fetch(config)
        elif subcommand == 'register':
            return self.handle_register(config)
        elif subcommand == 'purge':
            return self.handle_purge(config)
        elif subcommand == 'list':
            return self.handle_list(config)
        else:
            return exit_codes.UTILITY_FAIL
