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
# Copyright: Red Hat Inc. 2025
# Authors: Lukas Kotek <lkotek@redhat.com>
#          Jan Richter <jarichte@redhat.com>
"""
TMT output module.
"""

import datetime
import os
import pathlib
import time

from avocado.core.output import LOG_UI
from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, Init, Result
from avocado.core.settings import settings

# This naming requires tmt version >= 1.29
yaml_template = """- name: /{name}
  result: {status}
  start-time: "{start}"
  end-time: "{end}"
  duration: {time}
  data-path: {data}
  {custom}
"""


class TMTResult(Result):

    name = "tmt"
    description = "TMT result support"

    @staticmethod
    def _allowed_status(status):
        """
        Function matches avocado statuses with tmt ones
        """
        status_match = {
            "SKIP": "skip",
            "ERROR": "error",
            "FAIL": "fail",
            "WARN": "warn",
            "PASS": "pass",
            "INTERRUPTED": "error",
            "CANCEL": "skip",
            "STARTED": "info",
        }
        if status in status_match:
            return status_match[status]
        else:
            return "error"

    @staticmethod
    def _render(result):
        content = ""
        data_path = os.path.dirname(result.logfile)
        for test in result.tests:
            tmt_result = {}
            tmt_result["name"] = test.get("name", "<unknown>")
            # Avocado doesn't generate proper timestamps in json file
            tmt_result["start"] = datetime.datetime.fromtimestamp(
                test.get("actual_time_start", 0), tz=datetime.timezone.utc
            ).isoformat()
            tmt_result["end"] = datetime.datetime.fromtimestamp(
                test.get("actual_time_end", 0), tz=datetime.timezone.utc
            ).isoformat()
            tmt_result["time"] = time.strftime(
                "%H:%M:%S", time.gmtime(test.get("time_elapsed", 0))
            )

            tmt_result["status"] = TMTResult._allowed_status(test.get("status", {}))
            tmt_result["data"] = data_path
            tmt_result["custom"] = ""
            if test.get("logfile"):
                logfile_path = pathlib.Path(test.get("logfile")).relative_to(data_path)
                tmt_result["custom"] = f'log:\n{"- ":>4}{logfile_path}\n'

            content += f"{yaml_template.format(**tmt_result)}\n"
        return content

    def render(self, result, job):
        tmt_output = job.config.get("job.run.result.tmt.output")
        tmt_enabled = job.config.get("job.run.result.tmt.enabled")

        if not (tmt_enabled or tmt_output):
            return

        if not result.tests_total:
            return

        content = self._render(result)
        if tmt_enabled:
            tmt_path = os.path.join(job.logdir, "results.yaml")
            with open(tmt_path, "w", encoding="utf-8") as tmt_file:
                tmt_file.write(content)

        tmt_path = tmt_output
        if tmt_path is not None:
            if tmt_path == "-":
                LOG_UI.debug(content)
            else:
                with open(tmt_path, "w", encoding="utf-8") as tmt_file:
                    tmt_file.write(content)


class TMTInit(Init):

    name = "tmt"
    description = "TMT job result plugin initialization"

    def initialize(self):
        help_msg = (
            "Enable TMT result format and write it to FILE. "
            'Use "-" to redirect to the standard output.'
        )
        settings.register_option(
            section="job.run.result.tmt", key="output", default=None, help_msg=help_msg
        )

        help_msg = (
            "Enables default TMT result in the job results "
            'directory. File will be named "results.tmt".'
        )
        settings.register_option(
            section="job.run.result.tmt",
            key="enabled",
            key_type=bool,
            default=True,
            help_msg=help_msg,
        )


class TMTCLI(CLI):
    """
    TMT output
    """

    name = "tmt"
    description = "TMT output options for 'run' command"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get("run", None)
        if run_subcommand_parser is None:
            return

        settings.add_argparser_to_option(
            namespace="job.run.result.tmt.output",
            action=FileOrStdoutAction,
            metavar="FILE",
            parser=run_subcommand_parser,
            long_arg="--tmt",
        )

        settings.add_argparser_to_option(
            namespace="job.run.result.tmt.enabled",
            parser=run_subcommand_parser,
            long_arg="--disable-tmt-job-result",
        )

    def run(self, config):
        pass
