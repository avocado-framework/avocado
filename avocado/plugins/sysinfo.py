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
"""
System information plugin
"""
from avocado.core import sysinfo
from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import (
    CLICmd,
    Init,
    JobPostTests,
    JobPreTests,
    PostTest,
    PreTest,
)
from avocado.core.settings import settings
from avocado.core.teststatus import STATUSES_NOT_OK
from avocado.core.utils.path import prepend_base_path, system_wide_or_base_path
from avocado.utils import path


class SysinfoInit(Init):

    name = "sysinfo"
    description = "Initializes sysinfo settings"

    def initialize(self):
        help_msg = (
            "Enable or disable sysinfo collection (like hardware "
            "details, profiles, etc.)"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="enabled",
            default=True,
            key_type=bool,
            help_msg=help_msg,
        )

        help_msg = (
            "Enable or disable sysinfo collection (like hardware "
            "details, profiles, etc.) for each test"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="per_test",
            default=False,
            key_type=bool,
            help_msg=help_msg,
        )

        help_msg = (
            "Overall timeout to collect commands, when <=0 no timeout is enforced"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="commands_timeout",
            key_type=int,
            default=-1,
            help_msg=help_msg,
        )

        help_msg = (
            "Whether to take a list of installed packages previous to avocado jobs"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="installed_packages",
            key_type=bool,
            default=False,
            help_msg=help_msg,
        )

        help_msg = (
            "Whether to run certain commands in bg to give extra job "
            "debug information"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="profiler",
            key_type=bool,
            default=False,
            help_msg=help_msg,
        )

        help_msg = "Force LANG for sysinfo collection"
        settings.register_option(
            section="sysinfo.collect", key="locale", default="C", help_msg=help_msg
        )

        help_msg = (
            "Optimize sysinfo collected so that duplicates between pre "
            "and post re not stored in post"
        )
        settings.register_option(
            section="sysinfo.collect",
            key="optimize",
            default=False,
            key_type=bool,
            help_msg=help_msg,
        )

        help_msg = (
            "File with list of commands that will be executed and "
            "have their output collected"
        )
        default = system_wide_or_base_path("etc/avocado/sysinfo/commands")
        settings.register_option(
            section="sysinfo.collectibles",
            key="commands",
            key_type=prepend_base_path,
            default=default,
            help_msg=help_msg,
        )
        help_msg = (
            "File with list of commands that will be executed and "
            "have their output collected, in case of failed test"
        )
        default = system_wide_or_base_path("etc/avocado/sysinfo/fail_commands")
        settings.register_option(
            section="sysinfo.collectibles",
            key="fail_commands",
            key_type=prepend_base_path,
            default=default,
            help_msg=help_msg,
        )

        help_msg = "File with list of files that will be collected verbatim"
        default = system_wide_or_base_path("etc/avocado/sysinfo/files")
        settings.register_option(
            section="sysinfo.collectibles",
            key="files",
            key_type=prepend_base_path,
            default=default,
            help_msg=help_msg,
        )

        help_msg = (
            "File with list of files that will be collected verbatim"
            ", in case of failed test"
        )
        default = system_wide_or_base_path("etc/avocado/sysinfo/fail_files")
        settings.register_option(
            section="sysinfo.collectibles",
            key="fail_files",
            key_type=prepend_base_path,
            default=default,
            help_msg=help_msg,
        )

        help_msg = "File with list of commands that will run alongside the job/test"
        default = system_wide_or_base_path("etc/avocado/sysinfo/profilers")
        settings.register_option(
            section="sysinfo.collectibles",
            key="profilers",
            key_type=prepend_base_path,
            default=default,
            help_msg=help_msg,
        )


class SysInfoJob(JobPreTests, JobPostTests):

    name = "sysinfo"
    description = "Collects system information before/after the job is run"

    def __init__(self, config):  # pylint: disable=W0231
        self.sysinfo = None
        self.sysinfo_enabled = config.get("sysinfo.collect.enabled")

    def _init_sysinfo(self, job_logdir):
        if self.sysinfo is None:
            basedir = path.init_dir(job_logdir, "sysinfo")
            self.sysinfo = sysinfo.SysInfo(basedir=basedir)

    def pre_tests(self, job):
        if not self.sysinfo_enabled:
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.start()

    def post_tests(self, job):
        if not self.sysinfo_enabled:
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.end()


class SysInfoTest(PreTest, PostTest):
    """Implements the sysinfo pre/post test plugin.

    It will create pre/post-test tasks for collecting system information.
    """

    name = "sysinfo"
    description = "Collects system information before/after the test is run."

    def _is_sysinfo_enabled(self, config):
        if not (
            config.get("sysinfo.collect.enabled")
            and config.get("sysinfo.collect.per_test")
        ):
            return False
        return True

    def pre_test_runnables(self, test_runnable, suite_config=None):
        suite_config = suite_config or {}
        if not self._is_sysinfo_enabled(suite_config):
            return []
        sysinfo_config = sysinfo.gather_collectibles_config(suite_config)
        return [
            Runnable.from_avocado_config(
                "sysinfo",
                "pre",
                config=suite_config,
                name="pre",
                sysinfo=sysinfo_config,
                output_dir=test_runnable.output_dir,
            )
        ]

    def post_test_runnables(self, test_runnable, suite_config=None):
        suite_config = suite_config or {}
        if not self._is_sysinfo_enabled(suite_config):
            return []
        sysinfo_config = sysinfo.gather_collectibles_config(suite_config)
        return [
            (
                Runnable.from_avocado_config(
                    "sysinfo",
                    "post",
                    config=suite_config,
                    name="post",
                    sysinfo=sysinfo_config,
                    test_fail=False,
                    output_dir=test_runnable.output_dir,
                ),
                ["pass"],
            ),
            (
                Runnable.from_avocado_config(
                    "sysinfo",
                    "post",
                    config=suite_config,
                    name="post",
                    sysinfo=sysinfo_config,
                    test_fail=True,
                    output_dir=test_runnable.output_dir,
                ),
                [status.lower() for status in STATUSES_NOT_OK],
            ),
        ]


class SysInfo(CLICmd):

    """
    Collect system information
    """

    name = "sysinfo"
    description = "Collect system information"

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super().configure(parser)

        help_msg = (
            "Directory where Avocado will dump sysinfo data.  If one "
            "is not given explicitly, it will default to a directory "
            'named "sysinfo-" followed by a timestamp in the current '
            "working directory."
        )
        settings.register_option(
            section="sysinfo.collect",
            key="sysinfodir",
            default=None,
            help_msg=help_msg,
            parser=parser,
            positional_arg=True,
            nargs="?",
        )

    def run(self, config):
        sysinfodir = config.get("sysinfo.collect.sysinfodir")
        sysinfo.collect_sysinfo(sysinfodir)
