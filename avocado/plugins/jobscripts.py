import os
import logging

from avocado.utils import process
from avocado.core.settings import settings
from avocado.plugins.base import JobPre, JobPost


CONFIG_SECTION = 'avocado.plugins.jobscripts'


class JobScripts(JobPre, JobPost):

    name = 'jobscripts'
    description = 'Runs scripts before/after the job is run'

    def __init__(self):
        self.log = logging.getLogger("avocado.app")
        self.warn_non_existing_dir = settings.get_value(section=CONFIG_SECTION,
                                                        key="warn_non_existing_dir",
                                                        key_type=bool,
                                                        default=False)
        self.warn_non_zero_status = settings.get_value(section=CONFIG_SECTION,
                                                       key="warn_non_zero_status",
                                                       key_type=bool,
                                                       default=False)

    def run_scripts(self, kind, scripts_dir):
        if not os.path.isdir(scripts_dir):
            if self.warn_non_existing_dir:
                self.log.error("Directory configured to hold %s-job scripts "
                               "has not been found: %s", kind, scripts_dir)
            return

        dir_list = os.listdir(scripts_dir)
        scripts = [os.path.join(scripts_dir, f) for f in dir_list]
        scripts = [f for f in scripts
                   if os.access(f, os.R_OK | os.X_OK)]
        scripts.sort()
        for script in scripts:
            result = process.run(script, ignore_status=True)
            if (result.exit_status != 0) and self.warn_non_zero_status:
                self.log.error('Script "%s" exited with status "%i"',
                               script, result.exit_status)

    def pre(self, job):
        d = settings.get_value(section=CONFIG_SECTION,
                               key="pre", key_type=str,
                               default="/etc/avocado/scripts/job/pre.d/")
        self.run_scripts('pre', d)

    def post(self, job):
        d = settings.get_value(section=CONFIG_SECTION,
                               key="post", key_type=str,
                               default="/etc/avocado/scripts/job/post.d/")
        self.run_scripts('post', d)
