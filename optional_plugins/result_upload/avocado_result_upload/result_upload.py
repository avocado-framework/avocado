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
# Copyright: Virtuozzo Inc. 2017
# Authors: Dmitry Monakhov <dmonakhov@openvz.org>

"""
Avocado Plugin to propagate Job results to remote host
"""

from avocado.core.plugin_interfaces import CLI, Result
from avocado.core.settings import settings
from avocado.utils import path as utils_path
from avocado.utils import process


class ResultUpload(Result):

    """
    ResultsUpload output class
    """

    name = 'result_upload'
    description = 'ResultUpload result support'

    def render(self, result, job):
        """
        Upload result, which corresponds to one test from
        the Avocado Job

        if job.status == "RUNNING":
            return  # Don't create results on unfinished jobs

        """
        self.upload_url = job.config.get('plugins.result_upload.url')  # pylint: disable=W0201
        self.upload_cmd = job.config.get('plugins.result_upload.cmd')  # pylint: disable=W0201

        if self.upload_url is None:
            return
        if self.upload_cmd is None:
            return
        ret = process.run(f"{self.upload_cmd} {job.logdir} {self.upload_url}")
        if ret.exit_status:
            job.log.error(f"ResultUploader failed msg={result.stderr}")


class ResultUploadCLI(CLI):

    """
    ResultsUpload output class
    """

    name = 'result_upload'
    description = "ResultUpload options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'result-upload options'
        parser = run_subcommand_parser.add_argument_group(msg)
        help_msg = 'Specify the result upload url'
        settings.register_option(section='plugins.result_upload',
                                 key='url',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--result-upload-url',
                                 metavar='URL')

        try:
            rsync_bin = utils_path.find_command('rsync')
            def_ssh = ('ssh -oLogLevel=error -o stricthostkeychecking=no'
                       ' -o userknownhostsfile=/dev/null'
                       ' -o batchmode=yes -o passwordauthentication=no')
            def_upload_cmd = f'{rsync_bin} -arz -e \'{def_ssh} \''
        except utils_path.CmdNotFoundError:
            def_upload_cmd = None

        help_msg = 'Specify the command to upload results'
        settings.register_option(section='plugins.result_upload',
                                 key='cmd',
                                 help_msg=help_msg,
                                 default=def_upload_cmd,
                                 parser=parser,
                                 long_arg='--result-upload-cmd',
                                 metavar='COMMAND')

    def run(self, config):
        pass
