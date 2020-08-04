from enum import Enum
from uuid import uuid1

from .dispatcher import RunnerDispatcher
from .exceptions import OptionValidationError
from .future.settings import settings
from .loader import LoaderError, LoaderUnhandledReferenceError, loader
from .resolver import resolve
from .tags import filter_test_tags
from .test import DryRunTest
from .utils import resolutions_to_tasks
from .varianter import Varianter


class TestSuiteError(Exception):
    pass


class TestSuiteStatus(Enum):
    RESOLUTION_NOT_STARTED = object()
    TESTS_NOT_FOUND = object()
    TESTS_FOUND = object()
    UNKNOWN = object()


class TestSuite:
    def __init__(self, name, config, tests=None, job_config=None):
        self.name = name
        self.tests = tests

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

        if (config.get('run.dry_run.enabled') and
                self.config.get('run.test_runner') == 'runner'):
            self._convert_to_dry_run()

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
        try:
            loader.load_plugins(config)
            tests = loader.discover(references, force=ignore_missing)
            if config.get("filter.by_tags.tags"):
                tests = filter_test_tags(
                    tests,
                    config.get("filter.by_tags.tags"),
                    config.get("filter.by_tags.include_empty"),
                    config.get('filter.by_tags.include_empty_key'))
        except (LoaderUnhandledReferenceError, LoaderError) as details:
            raise TestSuiteError(details)

        return cls(name=name or str(uuid1),
                   config=config,
                   tests=tests)

    @classmethod
    def _from_config_with_resolver(cls, config, name=None):
        ignore_missing = config.get('run.ignore_missing_references')
        references = config.get('run.references')
        resolutions = resolve(references, ignore_missing=ignore_missing)
        tasks = resolutions_to_tasks(resolutions, config)

        return cls(name=name or str(uuid1),
                   config=config,
                   tests=tasks)

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
        if job_config:
            config.update(job_config)
        runner = config.get('run.test_runner') or 'runner'
        if runner == 'nrunner':
            suite = cls._from_config_with_resolver(config, name)
        else:
            suite = cls._from_config_with_loader(config, name)

        if not config.get('run.ignore_missing_references'):
            if not suite.tests:
                msg = ("Test Suite could not be create. No test references "
                       "provided nor any other arguments resolved into tests")
                raise TestSuiteError(msg)

        return suite
