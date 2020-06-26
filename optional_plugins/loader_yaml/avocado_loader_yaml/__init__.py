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
# Copyright: Red Hat Inc. 2017
# Author: Lukas Doktor <ldoktor@redhat.com>
"""Avocado Plugin that loads tests from YAML files"""

import copy

from avocado.core import loader, output, parameters
from avocado.core.plugin_interfaces import CLI
from avocado.core.settings import settings
from avocado_varianter_yaml_to_mux import create_from_yaml, mux


class YamlTestsuiteLoader(loader.TestLoader):

    """
    Gets variants from a YAML file and uses `test_reference` entries
    to create a test suite.
    """

    name = "yaml_testsuite"
    _extra_type_label_mapping = {}
    _extra_decorator_mapping = {}

    @staticmethod
    def get_type_label_mapping():
        """
        No type is discovered by default, uses "full_*_mappings" to report
        the actual types after "discover()" is called.
        """
        return {}

    def get_full_type_label_mapping(self):
        return self._extra_type_label_mapping

    @staticmethod
    def get_decorator_mapping():
        return {}

    def get_full_decorator_mapping(self):
        return self._extra_decorator_mapping

    def _get_loader(self, params):
        """
        Initializes test loader according to params.

        Uses params.get():
          test_reference_resolver_class - loadable location of the loader class
          test_reference_resolver_args - args to override current Avocado args
                                         before being passed to the loader
                                         class. (dict)
          test_reference_resolver_extra - extra_params to be passed to resolver
                                          (dict)
        """
        resolver_class = params.get("test_reference_resolver_class")
        if not resolver_class:
            if params.get("test_reference"):
                resolver_class = "avocado.core.loader.FileLoader"
            else:
                # Don't supply the default when no `test_reference` is given
                # to avoid listing default FileLoader tests
                return None
        mod, klass = resolver_class.rsplit(".", 1)
        try:
            loader_class = getattr(__import__(mod, fromlist=[klass]), klass)
        except ImportError:
            raise RuntimeError("Unable to import class defined by test_"
                               "reference_resolver_class '%s.%s'"
                               % (mod, klass))
        _args = params.get("test_reference_resolver_args")
        if not _args:
            config = self.config
        else:
            config = copy.copy(self.config)
            config.update(_args)
        extra_params = params.get("test_reference_resolver_extra", default={})
        if extra_params:
            extra_params = copy.deepcopy(extra_params)
        return loader_class(config, extra_params)

    def discover(self, reference, which_tests=loader.DiscoverMode.DEFAULT):
        tests = []
        if reference is None:
            return tests
        try:
            root = mux.apply_filters(create_from_yaml([reference]),
                                     self.config.get("run.mux_suite_only", []),
                                     self.config.get("run.mux_suite_out", []))
        except IOError:
            return []
        mux_tree = mux.MuxTree(root)
        for variant in mux_tree:
            params = parameters.AvocadoParams(variant, ["/run/*"],
                                              output.LOG_JOB.name)
            references = params.get("test_reference")
            if not isinstance(references, (list, tuple)):
                references = [references]
            for reference in references:
                test_loader = self._get_loader(params)
                if not test_loader:
                    continue
                _tests = test_loader.discover(reference, which_tests)
                self._extra_type_label_mapping.update(
                    test_loader.get_full_type_label_mapping())
                self._extra_decorator_mapping.update(
                    test_loader.get_full_decorator_mapping())
                name_prefix = params.get("mux_suite_test_name_prefix")
                if _tests:
                    if isinstance(name_prefix, list):
                        name_prefix = "".join(name_prefix)
                    for tst in _tests:
                        if name_prefix:
                            tst[1]["name"] = name_prefix + tst[1]["name"]
                        tst[1]["params"] = (variant, ["/run/*"])
                    tests.extend(_tests)
        return tests


class LoaderYAML(CLI):

    name = 'loader_yaml'
    description = "YAML test loader options for the 'run' subcommand"

    def configure(self, parser):
        subparser = parser.subcommands.choices.get('run', None)
        if subparser is None:
            return

        mux_options = subparser.add_argument_group("yaml to mux testsuite options")
        help_msg = "Filter only part of the YAML suite file"
        settings.register_option(section='run',
                                 key='mux_suite_only',
                                 nargs='+',
                                 help_msg=help_msg,
                                 parser=mux_options,
                                 long_arg='--mux-suite-only',
                                 key_type=list,
                                 default=[])
        help_msg = "Filter out part of the YAML suite file"
        settings.register_option(section='run',
                                 key='mux_suite_out',
                                 nargs='+',
                                 help_msg=help_msg,
                                 parser=mux_options,
                                 long_arg='--mux-suite-out',
                                 key_type=list,
                                 default=[])

    def run(self, config):
        loader.loader.register_plugin(YamlTestsuiteLoader)
