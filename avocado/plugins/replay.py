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
# Copyright: Red Hat, Inc. 2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""Replay Job Plugin"""

import json
import os
import sys

from avocado.core import exit_codes, job, output
from avocado.core.data_dir import get_job_results_dir
from avocado.core.jobdata import retrieve_job_config
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Replay(CLICmd):
    """Implements the avocado 'replay' subcommand."""

    name = "replay"
    description = "Runs a new job using a previous job as its configuration"

    def configure(self, parser):
        parser = super().configure(parser)
        help_msg = (
            "Replays a job, identified by: complete or partial Job "
            'ID, "latest" for the latest job, the job results path.'
        )
        settings.register_option(
            section="job.replay",
            key="source_job_id",
            help_msg=help_msg,
            metavar="SOURCE_JOB_ID",
            default="latest",
            nargs="?",
            positional_arg=True,
            parser=parser,
        )
        help_msg = (
            "Resume the job, skipping tests (and their variants) that "
            "already passed or were skipped in the source job."
        )
        settings.register_option(
            section="job.replay",
            key="resume",
            help_msg=help_msg,
            default=False,
            key_type=bool,
            action="store_true",
            parser=parser,
            long_arg="--resume",
        )

    @staticmethod
    def _exit_fail(message):
        output.LOG_UI.error(message)
        sys.exit(exit_codes.AVOCADO_FAIL)

    @staticmethod
    def _retrieve_source_job_config(source_job_id):
        results_dir = get_job_results_dir(source_job_id)
        if not results_dir:
            msg = f"Could not find the results directory " f'for Job "{source_job_id}"'
            Replay._exit_fail(msg)
        try:
            return retrieve_job_config(results_dir)
        except OSError:
            msg = f"Could not open the {source_job_id} " f"Job configuration"
            Replay._exit_fail(msg)
        except json.decoder.JSONDecodeError:
            msg = f"Could not read a valid configuration " f'of Job "{source_job_id}"'
            Replay._exit_fail(msg)

    @staticmethod
    def _load_completed_test_names(results_dir):
        """Return the set of test name strings that already passed or were
        skipped in the source job.

        Each entry is ``"{identifier};{variant_id}"`` (or just
        ``"{identifier}"`` when no variant was used), matching the ``name``
        field written by :class:`avocado.plugins.jsonresult.JSONResult`.

        :param results_dir: path to the source job results directory
        :type results_dir: str
        :returns: set of completed test name strings
        :rtype: set
        """
        results_path = os.path.join(results_dir, "results.json")
        if not os.path.exists(results_path):
            return set()
        try:
            with open(results_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.decoder.JSONDecodeError):
            return set()
        return {
            t["name"]
            for t in data.get("tests", [])
            if t.get("status", "").upper() in ("PASS", "SKIP")
        }

    def run(self, config):
        namespace = "job.replay.source_job_id"
        source_job_id = config.get(namespace)
        results_dir = get_job_results_dir(source_job_id)
        if not results_dir:
            msg = (
                f"Could not find the results directory "
                f'for Job "{source_job_id}"'
            )
            self._exit_fail(msg)
        source_job_config = self._retrieve_source_job_config(source_job_id)
        if hasattr(source_job_config, namespace):
            del source_job_config[namespace]
        # Flag that this is indeed a replayed job, which is impossible to
        # tell solely based on the job.replay.source_job_id given that it
        # has a default value of 'latest' for convenience reasons
        source_job_config["job.replay.enabled"] = True
        if config.get("job.replay.resume"):
            completed = self._load_completed_test_names(results_dir)
            if completed:
                output.LOG_UI.info(
                    "Resume mode: skipping %d previously completed test(s).",
                    len(completed),
                )
            source_job_config["job.replay.resume.completed_tests"] = completed
        with job.Job.from_config(source_job_config) as job_instance:
            job_run = job_instance.run()
        return job_run
