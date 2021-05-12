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

from .dispatcher import RunnerDispatcher
from .exceptions import (JobTestSuiteReferenceResolutionError,
                         OptionValidationError)
from .loader import (DiscoverMode, LoaderError, LoaderUnhandledReferenceError,
                     loader)
from .parser import HintParser
from .resolver import ReferenceResolutionResult, resolve
from .settings import settings
from .tags import filter_test_tags, filter_test_tags_runnable
from .test import DryRunTest, Test
from .varianter import Varianter


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
    :returns: the resolutions converted to tasks
    :rtype: list of :class:`avocado.core.nrunner.Task`
    """
    result = []
    filter_by_tags = config.get("filter.by_tags.tags")
    include_empty = config.get("filter.by_tags.include_empty")
    include_empty_key = config.get('filter.by_tags.include_empty_key')
    runner_config = settings.filter_config(config, r'^runner\.')
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
            runnable.config = runner_config
            result.append(runnable)
    return result


class TestSuite:
    def __init__(self, name, config=None, tests=None, job_config=None,
                 resolutions=None):
        self.name = name
        self.tests = tests
        self.resolutions = resolutions

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

        if (self.config.get('run.dry_run.enabled') and
                self.config.get('run.test_runner') == 'runner'):
            self._convert_to_dry_run()

        if self.size == 0:
            return

    def __len__(self):
        """This is a convenient method to run `len()` over this object.

        With this you can run: len(a_suite) and will return the same as
        `len(a_suite.tests)`.
        """
        return self.size

    def _convert_to_dry_run(self):
        for i in range(self.size):
            self.tests[i] = [DryRunTest, self.tests[i][1]]

    @classmethod
    def _from_config_with_loader(cls, config, name=None):
        references = config.get('run.references')
        ignore_missing = config.get('run.ignore_missing_references')
        verbose = config.get('core.verbose')
        subcommand = config.get('subcommand')

        # To-be-removed: For some reason, avocado list will display more tests
        # if in verbose mode. IMO, this is a little inconsistent with the 'run'
        # command.  This hack was needed to make one specific test happy.
        tests_mode = DiscoverMode.DEFAULT
        if subcommand == 'list':
            if verbose:
                tests_mode = DiscoverMode.ALL
            else:
                tests_mode = DiscoverMode.AVAILABLE

        try:
            loader.load_plugins(config)
            tests = loader.discover(references,
                                    force=ignore_missing,
                                    which_tests=tests_mode)
            if config.get("filter.by_tags.tags"):
                tests = filter_test_tags(
                    tests,
                    config.get("filter.by_tags.tags"),
                    config.get("filter.by_tags.include_empty"),
                    config.get('filter.by_tags.include_empty_key'))
        except (LoaderUnhandledReferenceError, LoaderError) as details:
            raise TestSuiteError(details)

        if name is None:
            name = str(uuid4())
        return cls(name=name, config=config, tests=tests)

    @classmethod
    def _from_config_with_resolver(cls, config, name=None):
        ignore_missing = config.get('run.ignore_missing_references')
        references = config.get('run.references')
        try:
            hint = None
            hint_filepath = '.avocado.hint'
            if os.path.exists(hint_filepath):
                hint = HintParser(hint_filepath)
            resolutions = resolve(references,
                                  hint=hint,
                                  ignore_missing=ignore_missing)
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
            stats = self._increment_dict_key_counter(stats, test.kind)
        return stats

    def _get_stats_from_runner(self):
        stats = {}
        mapping = loader.get_type_label_mapping()

        for cls, _ in self.tests:
            if isinstance(cls, str):
                cls = Test
            stats = self._increment_dict_key_counter(stats, mapping[cls])
        return stats

    def _get_tags_stats_from_nrunner(self):
        stats = {}
        for runnable in self.tests:
            if runnable is None:
                continue
            tags = runnable.tags or {}
            for tag in tags:
                stats = self._increment_dict_key_counter(stats, tag)
        return stats

    def _get_tags_stats_from_runner(self):
        stats = {}
        for test in self.tests:
            params = test[1]
            for tag in params.get('tags', {}):
                stats = self._increment_dict_key_counter(stats, tag)
        return stats

    @staticmethod
    def _increment_dict_key_counter(dict_object, key):
        try:
            dict_object[key.lower()] += 1
        except KeyError:
            dict_object[key.lower()] = 1
        return dict_object

    @property
    def references(self):
        if self._references is None:
            self._references = self.config.get('run.references')
        return self._references

    @property
    def runner(self):
        if self._runner is None:
            runner_name = self.config.get('run.test_runner') or 'runner'
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
        runner_name = self.config.get('run.test_runner') or 'runner'
        if runner_name == 'runner':
            return self._get_stats_from_runner()
        elif runner_name == 'nrunner':
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
        runner_name = self.config.get('run.test_runner') or 'runner'
        if runner_name == 'runner':
            return self._get_tags_stats_from_runner()
        elif runner_name == 'nrunner':
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
                    raise OptionValidationError("Unable to parse "
                                                "variant: %s" % details)
            self._variants = variants
        return self._variants

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
        config.update(suite_config)
        if job_config:
            config.update(job_config)
        runner = config.get('run.test_runner') or 'runner'
        if runner == 'nrunner':
            suite = cls._from_config_with_resolver(config, name)
        else:
            suite = cls._from_config_with_loader(config, name)

        if not config.get('run.ignore_missing_references'):
            if not suite.tests:
                msg = ("Test Suite could not be created. No test references "
                       "provided nor any other arguments resolved into tests")
                raise TestSuiteError(msg)

        return suite
