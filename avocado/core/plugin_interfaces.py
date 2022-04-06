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
# Author: Cleber Rosa <cleber@redhat.com>


import abc


class Plugin(abc.ABC):
    """Base for all plugins."""


class Init(Plugin):
    """Base plugin interface for plugins that needs to initialize itself."""

    @abc.abstractmethod
    def initialize(self):
        """Entry point for the plugin to perform its initialization."""


class Settings(Plugin):
    """Base plugin to allow modifying settings.

    Currently it only supports to extend/modify the default list of
    paths to config files.
    """

    @abc.abstractmethod
    def adjust_settings_paths(self, paths):
        """Entry point where plugin can modify the list of configuration paths."""


class CLI(Plugin):
    """Base plugin interface for adding options (non-commands) to the command line.

    Plugins that want to add extra options to the core command line application
    or to sub commands should use the 'avocado.plugins.cli' namespace.
    """

    @abc.abstractmethod
    def configure(self, parser):
        """Configures the command line parser with options specific to this plugin."""

    @abc.abstractmethod
    def run(self, config):
        """Execute any action the plugin intends.

        Example of action may include activating a special features upon
        finding that the requested command line options were set by the user.

        Note: this plugin class is not intended for adding new commands, for
        that please use `CLICmd`.
        """


class CLICmd(Plugin):
    """Base plugin interface for adding new commands to the command line app.

    Plugins that want to add extensions to the run command should use the
    'avocado.plugins.cli.cmd' namespace.
    """
    name = None
    description = None

    def configure(self, parser):
        """Lets the extension add command line options and do early configuration.

        By default it will register its `name` as the command name and give
        its `description` as the help message.
        """
        help_msg = self.description
        if help_msg is None:
            help_msg = f'Runs the {self.name} command'

        parser = parser.subcommands.add_parser(self.name,
                                               help=help_msg)
        return parser

    @abc.abstractmethod
    def run(self, config):
        """Entry point for actually running the command."""


class JobPre(Plugin):
    """Base plugin interface for adding actions before a job runs.

    Plugins that want to add actions to be run before a job runs,
    should use the 'avocado.plugins.job.prepost' namespace and
    implement the defined interface.
    """

    @abc.abstractmethod
    def pre(self, job):
        """Entry point for actually running the pre job action."""


class JobPost(Plugin):
    """Base plugin interface for adding actions after a job runs.

    Plugins that want to add actions to be run after a job runs,
    should use the 'avocado.plugins.job.prepost' namespace and
    implement the defined interface.
    """

    @abc.abstractmethod
    def post(self, job):
        """Entry point for actually running the post job action."""


class Result(Plugin):

    @abc.abstractmethod
    def render(self, result, job):
        """Entry point with method that renders the result.

        This will usually be used to write the result to a file or directory.

        :param result: the complete job result
        :type result: :class:`avocado.core.result.Result`
        :param job: the finished job for which a result will be written
        :type job: :class:`avocado.core.job.Job`
        """


class JobPreTests(Plugin):
    """Base plugin interface for adding actions before a job runs tests.

    This interface looks similar to :class:`JobPre`, but it's intended
    to be called at a very specific place, that is, between
    :meth:`avocado.core.job.Job.create_test_suite` and
    :meth:`avocado.core.job.Job.run_tests`.
    """

    @abc.abstractmethod
    def pre_tests(self, job):
        """Entry point for job running actions before tests execution."""


class JobPostTests(Plugin):
    """Base plugin interface for adding actions after a job runs tests.

    Plugins using this interface will run at the a time equivalent to
    plugins using the :class:`JobPost` interface, that is, at
    :meth:`avocado.core.job.Job.post_tests`.  This is because
    :class:`JobPost` based plugins will eventually be modified to
    really run after the job has finished, and not after it has run
    tests.
    """

    @abc.abstractmethod
    def post_tests(self, job):
        """Entry point for job running actions after the tests execution."""


class ResultEvents(JobPreTests, JobPostTests):
    """Base plugin interface for event based (stream-able) results.

    Plugins that want to add actions to be run after a job runs,
    should use the 'avocado.plugins.result_events' namespace and
    implement the defined interface.
    """

    @abc.abstractmethod
    def start_test(self, result, state):
        """Event triggered when a test starts running."""

    @abc.abstractmethod
    def test_progress(self, progress=False):
        """Interface to notify progress (or not) of the running test."""

    @abc.abstractmethod
    def end_test(self, result, state):
        """Event triggered when a test finishes running."""


class Varianter(Plugin):
    """Base plugin interface for producing test variants."""

    @abc.abstractmethod
    def __iter__(self):
        """Yields all variants.

        The variant is defined as dictionary with at least:
         * variant_id - name of the current variant
         * variant - AvocadoParams-compatible variant (usually a list)
         * paths - default path(s)

        :yield variant
        """

    @abc.abstractmethod
    def __len__(self):
        """Report number of variants."""

    @abc.abstractmethod
    def to_str(self, summary, variants, **kwargs):
        """Return human readable representation.

        The summary/variants accepts verbosity where 0 means silent and
        maximum is up to the plugin.

        :param summary: How verbose summary to output (int)
        :param variants: How verbose list of variants to output (int)
        :param kwargs: Other free-form arguments
        :rtype: str
        """


class ResolverMixin:
    """Common utilities for Resolver implementations."""

    def __init__(self, config=None):
        from avocado.core.settings import settings
        self.config = config or settings.as_dict()


class Resolver(Plugin, ResolverMixin):
    """Base plugin interface for resolving test references into resolutions."""

    @abc.abstractmethod
    def resolve(self, reference):
        """Resolves the given reference into a reference resolution.

        :param reference: a specification that can eventually be resolved
                          into a test (in the form of a
                          :class:`avocado.core.nrunner.Runnable`)
        :type reference: str
        :returns: the result of the resolution process, containing the
                  success, failure or error, along with zero or more
                  :class:`avocado.core.nrunner.Runnable` objects
        :rtype: :class:`avocado.core.resolver.ReferenceResolution`
        """


class Discoverer(Plugin, ResolverMixin):
    """Base plugin interface for discovering tests without reference."""

    @abc.abstractmethod
    def discover(self):
        """Discovers a test resolutions

        It will be used when the `test.references` variable is empty, but
        the discoverer will be able to use another data for gathering test
        resolutions. It work same as the Resolver, but without the test
        reference.

        :returns: the result of the resolution process, containing the
                  success, failure or error, along with zero or more
                  :class:`avocado.core.nrunner.Runnable` objects
        :rtype: :class:`avocado.core.resolver.ReferenceResolution`
        """


class Runner(Plugin):
    """Base plugin interface for test runners.

    This is the interface a job uses to drive the tests execution via
    compliant test runners.

    NOTE: This interface is not to be confused with the internal
    interface or idiosyncrasies of the :ref:`nrunner`.
    """

    @abc.abstractmethod
    def run_suite(self, job, test_suite):
        """Run one or more tests and report with test result.

        :param job: an instance of :class:`avocado.core.job.Job`.
        :param test_suite: an instance of TestSuite with some tests to run.
        :return: a set with types of test failures.
        """


class Spawner(Plugin):
    """Base plugin interface spawners of tasks.

    A spawner implementation will spawn Avocado in its intended location, and
    isolation model. Spawners that run on the same machine as Avocado is
    originally installed are possible children of this.
    """

    @staticmethod
    @abc.abstractmethod
    def is_task_alive(runtime_task):
        """Determines if a task is alive or not.

        :param runtime_task: wrapper for a Task with additional runtime
                             information.
        :type runtime_task: :class:`avocado.core.task.runtime.RuntimeTask`
        """

    @abc.abstractmethod
    async def spawn_task(self, runtime_task):
        """Spawns a task return whether the spawning was successful.

        :param runtime_task: wrapper for a Task with additional runtime
                             information.
        :type runtime_task: :class:`avocado.core.task.runtime.RuntimeTask`
        """

    def create_task_output_dir(self, runtime_task):
        """Creates output directory in the intended location, before the task spawn.

        The output directory path will be saved to the `task.runnable.config`
        for the usage by runners.

        :param runtime_task: wrapper for a Task with additional runtime
                             information.
        :type runtime_task: :class:`avocado.core.task.runtime.RuntimeTask`
        """

    @abc.abstractmethod
    async def wait_task(self, runtime_task):
        """Waits for a task to finish.

        :param runtime_task: wrapper for a Task with additional runtime
                             information.
        :type runtime_task: :class:`avocado.core.task.runtime.RuntimeTask`
        """

    @staticmethod
    @abc.abstractmethod
    async def check_task_requirements(runtime_task):
        """Checks if the requirements described within a task are available.

        :param runtime_task: wrapper for a Task with additional runtime
                             information.
        :type runtime_task: :class:`avocado.core.task.runtime.RuntimeTask`
        """


class DeploymentSpawner(Spawner):
    """Spawners that needs basic deployment are based on this class.

    Spawners that uses any type of isolation model would be a possible children
    of this.
    """

    @abc.abstractmethod
    async def deploy_avocado(self, where):
        """Avocado deployment for the isolated environment.

        This method should be executed before spawning the task.

        :param where: handle for where the spawner should deploy avocado.
                      You can use this parameter to pass any valid argument,
                      like a container, vm, or any other isolated environment
                      object or identifier.
        """

    @abc.abstractmethod
    async def deploy_artifacts(self):
        """Basic artifacts deployment for the isolated environment.

        During this stage test references (i.e: mytest.py), data files (i.e:
        mytest.py.data/), and any other basic requirement should be deployed to
        the isolated environment. Please keep in mind that test requirements
        defined at the requirements resolver level are not part of this
        deployment and it will be fulfilled by the requirement resolver.

        This method should also be executed before spawning the task.
        """


class RunnableRunner(Plugin):
    """Base interface for a nrunner Runner."""

    @abc.abstractmethod
    def run(self, runnable):
        """Runner main method

        Yields dictionary as output, containing status as well as relevant
        information concerning the results.

        :param runnable: a Runnable instance that describes what is to be run
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        """
