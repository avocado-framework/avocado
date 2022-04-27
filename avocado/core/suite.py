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
# Copyright: Red Hat Inc. 2020
# Author: Beraldo Leal <bleal@redhat.com>

import os
from enum import Enum
from uuid import uuid4

from avocado.core.dispatcher import RunnerDispatcher
from avocado.core.exceptions import (JobTestSuiteReferenceResolutionError,
                                     OptionValidationError)
from avocado.core.parser import HintParser
from avocado.core.resolver import ReferenceResolutionResult, resolve
from avocado.core.settings import settings
from avocado.core.tags import filter_test_tags_runnable
from avocado.core.tree import TreeNode
from avocado.core.varianter import Varianter, is_empty_variant


class TestSuiteError(Exception):
    pass


class TestSuiteStatus(Enum):
    RESOLUTION_NOT_STARTED = object()
    TESTS_NOT_FOUND = object()
    TESTS_FOUND = object()
    UNKNOWN = object()


def resolutions_to_runnables(resolutions, config):
    """
    Transforms resolver resolutions into runnables suitable for a suite

    A resolver resolution
    (:class:`avocado.core.resolver.ReferenceResolution`) contains
    information about the resolution process (if it was successful
    or not) and in case of successful resolutions a list of
    resolutions.  It's expected that the resolution contain one
    or more :class:`avocado.core.nrunner.Runnable`.

    This function sets the runnable specific configuration for each
    runnable.  It also performs tag based filtering on the runnables
    for possibly excluding some of the Runnables.

    :param resolutions: possible multiple resolutions for multiple
                        references
    :type resolutions: list of :class:`avocado.core.resolver.ReferenceResolution`
    :param config: job configuration
    :type config: dict
    :returns: the resolutions converted to runnables
    :rtype: list of :class:`avocado.core.nrunner.Runnable`
    """
    result = []
    filter_by_tags = config.get("filter.by_tags.tags")
    include_empty = config.get("filter.by_tags.include_empty")
    include_empty_key = config.get('filter.by_tags.include_empty_key')
    for resolution in resolutions:
        if resolution.result != ReferenceResolutionResult.SUCCESS:
            continue
        for runnable in resolution.resolutions:
            if filter_by_tags:
                if not filter_test_tags_runnable(runnable,
                                                 filter_by_tags,
                                                 include_empty,
                                                 include_empty_key):
                    continue
            result.append(runnable)
    return result


class TestSuite:
    def __init__(self, name, config=None, tests=None, job_config=None,
                 resolutions=None, enabled=True):
        self.name = name
        self.tests = tests
        self.resolutions = resolutions
        self.enabled = enabled

        # Create a complete config dict with all registered options + custom
        # config
        self.config = settings.as_dict()
        if job_config:
            self.config.update(job_config)
        if config:
            self.config.update(config)

        self._variants = None
        self._references = None
        self._runner = None
        self._test_parameters = None

        self._check_both_parameters_and_variants()

        if self.config.get('run.dry_run.enabled'):
            self._convert_to_dry_run()

        if self.size == 0:
            return

    def _has_both_parameters_and_variants(self):
        if not self.test_parameters:
            return False
        for variant in self.variants.itertests():
            var = variant.get("variant")
            if not is_empty_variant(var):
                return True
        return False

    def _check_both_parameters_and_variants(self):
        if self._has_both_parameters_and_variants():
            err_msg = ('Specifying test parameters (with config entry '
                       '"run.test_parameters" or command line "-p") along with '
                       'any varianter plugin (run "avocado plugins" for a list)'
                       ' is not yet supported. Please use one or the other.')
            raise TestSuiteError(err_msg)

    def __len__(self):
        """This is a convenient method to run `len()` over this object.

        With this you can run: len(a_suite) and will return the same as
        `len(a_suite.tests)`.
        """
        return self.size

    def _convert_to_dry_run(self):
        if self.config.get('run.test_runner') == 'nrunner':
            for runnable in self.tests:
                runnable.kind = 'dry-run'

    @classmethod
    def _from_config_with_resolver(cls, config, name=None):
        ignore_missing = config.get('run.ignore_missing_references')
        references = config.get('resolver.references')
        try:
            hint = None
            hint_filepath = '.avocado.hint'
            if os.path.exists(hint_filepath):
                hint = HintParser(hint_filepath)
            resolutions = resolve(references,
                                  hint=hint,
                                  ignore_missing=ignore_missing,
                                  config=config)
        except JobTestSuiteReferenceResolutionError as details:
            raise TestSuiteError(details)

        runnables = resolutions_to_runnables(resolutions, config)

        if name is None:
            name = str(uuid4())
        return cls(name=name, config=config, tests=runnables,
                   resolutions=resolutions)

    def _get_stats_from_nrunner(self):
        stats = {}
        for test in self.tests:
            self._increment_dict_key_counter(stats, test.kind)
        return stats

    def _get_tags_stats_from_nrunner(self):
        stats = {}
        for runnable in self.tests:
            if runnable is None:
                continue
            tags = runnable.tags or {}
            for tag in tags:
                self._increment_dict_key_counter(stats, tag)
        return stats

    @staticmethod
    def _increment_dict_key_counter(dict_object, key):
        try:
            dict_object[key.lower()] += 1
        except KeyError:
            dict_object[key.lower()] = 1

    @property
    def references(self):
        if self._references is None:
            self._references = self.config.get('resolver.references')
        return self._references

    @property
    def runner(self):
        if self._runner is None:
            runner_name = self.config.get('run.test_runner')
            try:
                runner_extension = RunnerDispatcher()[runner_name]
                self._runner = runner_extension.obj
            except KeyError:
                raise TestSuiteError("Runner not implemented.")
        return self._runner

    @property
    def size(self):
        """The overall length/size of this test suite."""
        if self.tests is None:
            return 0
        return len(self.tests)

    @property
    def stats(self):
        """Return a statistics dict with the current tests."""
        runner_name = self.config.get('run.test_runner')
        if runner_name == 'nrunner':
            return self._get_stats_from_nrunner()
        return {}

    @property
    def status(self):
        if self.tests is None:
            return TestSuiteStatus.RESOLUTION_NOT_STARTED
        elif self.size == 0:
            return TestSuiteStatus.TESTS_NOT_FOUND
        elif self.size > 0:
            return TestSuiteStatus.TESTS_FOUND
        else:
            return TestSuiteStatus.UNKNOWN

    @property
    def tags_stats(self):
        """Return a statistics dict with the current tests tags."""
        runner_name = self.config.get('run.test_runner')
        if runner_name == 'nrunner':
            return self._get_tags_stats_from_nrunner()
        return {}

    @property
    def test_parameters(self):
        """Placeholder for test parameters.

        This is related to --test-parameters command line option or
        (run.test_parameters).
        """
        if self._test_parameters is None:
            self._test_parameters = {name: value for name, value
                                     in self.config.get('run.test_parameters',
                                                        [])}
        return self._test_parameters

    @property
    def variants(self):
        if self._variants is None:
            variants = Varianter()
            if not variants.is_parsed():
                try:
                    variants.parse(self.config)
                except (IOError, ValueError) as details:
                    raise OptionValidationError(f"Unable to parse variant: "
                                                f"{details}")
            self._variants = variants
        return self._variants

    def get_test_variants(self):
        """Computes test variants based on the parameters"""

        if self.test_parameters:
            paths = ['/']
            tree_nodes = TreeNode().get_node(paths[0], True)
            tree_nodes.value = self.test_parameters
            variant = {"variant": tree_nodes,
                       "variant_id": None,
                       "paths": paths}
            test_variant = [(test, variant) for test in self.tests]

        else:
            # let's use variants when parameters are not available
            # define execution order
            execution_order = self.config.get('run.execution_order')
            if execution_order == "variants-per-test":
                test_variant = [(test, variant)
                                for test in self.tests
                                for variant in self.variants.itertests()]
            elif execution_order == "tests-per-variant":
                test_variant = [(test, variant)
                                for variant in self.variants.itertests()
                                for test in self.tests]
        return test_variant

    def run(self, job):
        """Run this test suite with the job context in mind.

        :param job: A :class:`avocado.core.job.Job` instance.
        :rtype: set
        """
        return self.runner.run_suite(job, self)

    @classmethod
    def from_config(cls, config, name=None, job_config=None):
        """Helper method to create a TestSuite from config dicts.

        This is different from the TestSuite() initialization because here we
        are assuming that you need some help to build the test suite. Avocado
        will try to resolve tests based on the configuration information
        instead of assuming pre populated tests.

        If you need to create a custom TestSuite, please use the TestSuite()
        constructor instead of this method.

        :param config: A config dict to be used on the desired test suite.
        :type config: dict
        :param name: The name of the test suite. This is optional and default
                     is a random uuid.
        :type name: str
        :param job_config: The job config dict (a global config). Use this to
                           avoid huge configs per test suite. This is also
                           optional.
        :type job_config: dict
        """
        suite_config = config
        config = settings.as_dict()
        if job_config:
            config.update(job_config)
        config.update(suite_config)
        runner = config.get('run.test_runner')
        if runner == 'nrunner':
            suite = cls._from_config_with_resolver(config, name)
        else:
            raise TestSuiteError(f'Suite creation for runner "{runner}" '
                                 f'is not supported')

        if not config.get('run.ignore_missing_references'):
            if not suite.tests:
                msg = ("Test Suite could not be created. No test references "
                       "provided nor any other arguments resolved into tests")
                raise TestSuiteError(msg)

        return suite
