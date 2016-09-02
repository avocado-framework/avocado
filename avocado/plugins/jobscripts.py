import os
import logging

from avocado.core.plugin_interfaces import JobPre, JobPost
from avocado.core.settings import settings
from avocado.utils import process


CONFIG_SECTION = 'plugins.jobscripts'


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
                                                       default=True)

    def _run_scripts(self, kind, scripts_dir, job):
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
        if not scripts:
            return

        env = self._job_to_environment_variables(job)
        for script in scripts:
            result = process.run(script, ignore_status=True, env=env)
            if (result.exit_status != 0) and self.warn_non_zero_status:
                self.log.error('%s job script "%s" exited with status "%i"',
                               kind.capitalize(), script, result.exit_status)

    @staticmethod
    def _job_to_environment_variables(job):
        env = {}
        env['AVOCADO_JOB_UNIQUE_ID'] = job.unique_id
        env['AVOCADO_JOB_STATUS'] = job.status
        if job.logdir is not None:
            env['AVOCADO_JOB_LOGDIR'] = job.logdir
        return env

    def pre(self, job):
        path = settings.get_value(section=CONFIG_SECTION,
                                  key="pre", key_type='path',
                                  default="/etc/avocado/scripts/job/pre.d/")
        self._run_scripts('pre', path, job)

    def post(self, job):
        path = settings.get_value(section=CONFIG_SECTION,
                                  key="post", key_type='path',
                                  default="/etc/avocado/scripts/job/post.d/")
        self._run_scripts('post', path, job)
