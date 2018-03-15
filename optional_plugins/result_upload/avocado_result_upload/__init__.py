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
from avocado.utils import process
from avocado.utils import path as utils_path


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
        self.upload_url = None
        if getattr(job.args, 'result_upload_url', None) is not None:
            self.upload_url = job.args.result_upload_url

        self.upload_cmd = None
        if getattr(job.args, 'result_upload_cmd', None) is not None:
            self.upload_cmd = job.args.result_upload_cmd

        if self.upload_url is None:
            return
        if self.upload_cmd is None:
            return
        ret = process.run("%s %s %s" % (self.upload_cmd, job.logdir,
                                        self.upload_url))
        if ret.exit_status:
            job.log.error("ResultUploader failed msg=%s" % result.stderr)


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
        parser.add_argument('--result-upload-url',
                            dest='result_upload_url', default=None,
                            help='Specify the result upload url')

        try:
            rsync_bin = utils_path.find_command('rsync')
            def_ssh = ('ssh -oLogLevel=error -o stricthostkeychecking=no'
                       ' -o userknownhostsfile=/dev/null'
                       ' -o batchmode=yes -o passwordauthentication=no')
            def_upload_cmd = '%s -arz -e \'%s \'' % (rsync_bin, def_ssh)
        except utils_path.CmdNotFoundError:
            def_upload_cmd = None

        parser.add_argument('--result-upload-cmd',
                            dest='result_upload_cmd', default=def_upload_cmd,
                            help='Specify the command to upload results')

    def run(self, args):
        url = getattr(args, 'result_upload_url', None)
        if url is None:
            url = settings.get_value('plugins.result_upload',
                                     'url',
                                     default=None)
            if url is not None:
                args.result_upload_url = url

        cmd = getattr(args, 'result_upload_cmd', None)
        if cmd is None:
            cmd = settings.get_value('plugins.result_upload',
                                     'command',
                                     default=None)
            if cmd is not None:
                args.result_upload_cmd = cmd
