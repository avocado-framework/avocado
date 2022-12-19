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
# Authors: Beraldo Leal <bleal@redhat.com>

"""
Jobs subcommand
"""
import json
import os
from datetime import datetime
from glob import glob

from avocado.core import exit_codes, output
from avocado.core.data_dir import get_job_results_dir, get_logs_dir
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings
from avocado.utils import astring


class Jobs(CLICmd):
    """
    Implements the avocado 'jobs' subcommand
    """

    name = "jobs"
    description = "Manage Avocado jobs"

    @staticmethod
    def _get_data_from_file(filename):
        if not filename or not os.path.isfile(filename):
            raise FileNotFoundError(f"File not found {filename}")

        with open(filename, "r", encoding="utf-8") as fp:
            return json.load(fp)

    @staticmethod
    def _print_job_details(details):
        for key, value in details.items():
            LOG_UI.info("%-12s: %s", key, value)

    @staticmethod
    def _print_job_tests(tests):
        test_matrix = []
        date_fmt = "%Y/%m/%d %H:%M:%S"
        for test in tests:
            status = test.get("status")
            decorator = output.TEST_STATUS_DECORATOR_MAPPING.get(status)
            end = datetime.fromtimestamp(test.get("end"))
            test_matrix.append(
                (
                    test.get("id"),
                    end.strftime(date_fmt),
                    f"{float(test.get('time')):5f}",
                    decorator(status, ""),
                )
            )
        header = (
            output.TERM_SUPPORT.header_str("Test ID"),
            output.TERM_SUPPORT.header_str("End Time"),
            output.TERM_SUPPORT.header_str("Run Time"),
            output.TERM_SUPPORT.header_str("Status"),
        )
        for line in astring.iter_tabular_output(test_matrix, header=header, strip=True):
            LOG_UI.debug(line)

    def configure(self, parser):
        """
        Add the subparser for the assets action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super().configure(parser)

        subcommands = parser.add_subparsers(
            dest="jobs_subcommand", metavar="sub-command"
        )
        subcommands.required = True

        help_msg = "List all known jobs by Avocado"
        subcommands.add_parser("list", help=help_msg)

        help_msg = (
            "Show details about a specific job. When passing a Job "
            'ID, you can use any Job Reference (job_id, "latest", '
            "or job results path)."
        )
        show_parser = subcommands.add_parser("show", help=help_msg)
        settings.register_option(
            section="jobs.show",
            key="job_id",
            help_msg="JOB id",
            metavar="JOBID",
            default="latest",
            nargs="?",
            positional_arg=True,
            parser=show_parser,
        )

    @staticmethod
    def handle_list_command(jobs_results):
        """Called when 'avocado jobs list' command is executed."""

        for filename in jobs_results.values():
            with open(filename, "r", encoding="utf-8") as fp:
                job = json.load(fp)
                LOG_UI.info(
                    "%-40s %-26s %3s (%s/%s/%s/%s)",
                    job["job_id"],
                    job["start"],
                    job["total"],
                    job["pass"],
                    job["skip"],
                    job["errors"],
                    job["failures"],
                )

        return exit_codes.AVOCADO_ALL_OK

    def handle_show_command(self, config):
        """Called when 'avocado jobs show' command is executed."""

        job_id = config.get("jobs.show.job_id")
        results_dir = get_job_results_dir(job_id)
        if results_dir is None:
            LOG_UI.error("Error: Job %s not found", job_id)
            return exit_codes.AVOCADO_GENERIC_CRASH

        results_file = os.path.join(results_dir, "results.json")
        try:
            results_data = self._get_data_from_file(results_file)
        except FileNotFoundError as ex:
            # Results data are important and should exit if not found
            LOG_UI.error(ex)
            return exit_codes.AVOCADO_GENERIC_CRASH

        data = {
            "JOB ID": job_id,
            "JOB LOG": results_data.get("debuglog"),
        }

        # We could improve this soon with more data and colors
        self._print_job_details(data)
        LOG_UI.info("")
        self._print_job_tests(results_data.get("tests"))
        results = (
            "PASS %d | ERROR %d | FAIL %d | SKIP %d |"
            "WARN %d | INTERRUPT %s | CANCEL %s"
        )
        results %= (
            results_data.get("pass", 0),
            results_data.get("error", 0),
            results_data.get("failures", 0),
            results_data.get("skip", 0),
            results_data.get("warn", 0),
            results_data.get("interrupt", 0),
            results_data.get("cancel", 0),
        )
        self._print_job_details({"RESULTS": results})
        return exit_codes.AVOCADO_ALL_OK

    def run(self, config):
        results = {}

        jobs_dir = get_logs_dir()
        for result in glob(os.path.join(jobs_dir, "*/results.json")):
            with open(result, "r", encoding="utf-8") as fp:
                job = json.load(fp)
                results[job["job_id"]] = result

        subcommand = config.get("jobs_subcommand")
        if subcommand == "list":
            return self.handle_list_command(results)
        elif subcommand == "show":
            return self.handle_show_command(config)
        return exit_codes.AVOCADO_ALL_OK
