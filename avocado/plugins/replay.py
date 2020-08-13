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
from avocado.core.dispatcher import JobPrePostDispatcher
from avocado.core.future.settings import settings
from avocado.core.plugin_interfaces import CLICmd


class Replay(CLICmd):

    """Implements the avocado 'replay' subcommand."""

    name = 'replay'
    description = "Runs a new job using a previous job as its configuration"

    def configure(self, parser):
        parser = super(Replay, self).configure(parser)
        help_msg = ('Replays a job, identified by: complete or partial Job '
                    'ID, "latest" for the latest job, the job results path.')
        settings.register_option(section='job.replay',
                                 key='source_job_id',
                                 help_msg=help_msg,
                                 metavar='SOURCE_JOB_ID',
                                 default='latest',
                                 nargs='?',
                                 positional_arg=True,
                                 parser=parser)

    @staticmethod
    def _exit_fail(message):
        output.LOG_UI.error(message)
        sys.exit(exit_codes.AVOCADO_FAIL)

    @staticmethod
    def _retrieve_source_job_config(source_job_id):
        results_dir = get_job_results_dir(source_job_id)
        if not results_dir:
            msg = 'Could not find the results directory for Job "%s"' % source_job_id
            Replay._exit_fail(msg)
        config_file_path = os.path.join(results_dir, 'jobdata', 'args.json')
        try:
            with open(config_file_path, 'r') as config_file:
                return json.load(config_file)
        except OSError:
            msg = 'Could not open the source Job configuration "%s"' % config_file_path
            Replay._exit_fail(msg)
        except json.decoder.JSONDecodeError:
            msg = 'Could not read a valid configuration from file "%s"' % config_file_path
            Replay._exit_fail(msg)

    def run(self, config):
        namespace = 'job.replay.source_job_id'
        source_job_id = config.get(namespace)
        source_job_config = self._retrieve_source_job_config(source_job_id)
        if hasattr(source_job_config, namespace):
            del(source_job_config[namespace])
        # Flag that this is indeed a replayed job, which is impossible to
        # tell solely based on the job.replay.source_job_id given that it
        # has a default value of 'latest' for convenience reasons
        source_job_config['job.replay.enabled'] = True
        with job.Job.from_config(source_job_config) as job_instance:
            pre_post_dispatcher = JobPrePostDispatcher()
            try:
                output.log_plugin_failures(pre_post_dispatcher.load_failures)
                pre_post_dispatcher.map_method('pre', job_instance)
                job_run = job_instance.run()
            finally:
                pre_post_dispatcher.map_method('post', job_instance)

        return job_run
