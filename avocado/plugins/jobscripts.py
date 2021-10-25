import os

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings
from avocado.core.utils.path import prepend_base_path
from avocado.utils import process


class JobScriptsInit(Init):
    name = 'jobscripts-init'
    description = 'Jobscripts plugin initialization'

    def initialize(self):
        help_msg = 'Warn if configured (or default) directory does not exist'
        settings.register_option(section='plugins.jobscripts',
                                 key='warn_non_existing_dir',
                                 key_type=bool,
                                 default=False,
                                 help_msg=help_msg)

        help_msg = 'Warn if any script run return non-zero status'
        settings.register_option(section='plugins.jobscripts',
                                 key='warn_non_zero_status',
                                 key_type=bool,
                                 default=True,
                                 help_msg=help_msg)

        help_msg = 'Directory with scripts to be executed before a job is run'
        default = '/etc/avocado/scripts/job/pre.d/'
        settings.register_option(section='plugins.jobscripts',
                                 key='pre',
                                 key_type=prepend_base_path,
                                 help_msg=help_msg,
                                 default=default)

        help_msg = 'Directory with scripts to be executed after a job is run'
        default = '/etc/avocado/scripts/job/post.d/'
        settings.register_option(section='plugins.jobscripts',
                                 key='post',
                                 key_type=prepend_base_path,
                                 help_msg=help_msg,
                                 default=default)


class JobScripts(JobPre, JobPost):

    name = 'jobscripts'
    description = 'Runs scripts before/after the job is run'

    def _run_scripts(self, kind, scripts_dir, job):
        config = job.config
        if not os.path.isdir(scripts_dir):
            if config.get('plugins.jobscripts.warn_non_existing_dir'):
                LOG_UI.error("Directory configured to hold %s-job scripts "
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
        non_zero_namespace = 'plugins.jobscripts.warn_non_zero_status'
        warn_non_zero_status = config.get(non_zero_namespace)
        for script in scripts:
            result = process.run(script, ignore_status=True, env=env)
            if (result.exit_status != 0) and warn_non_zero_status:
                LOG_UI.error('%s job script "%s" exited with status "%i"',
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
        path = job.config.get('plugins.jobscripts.pre')
        self._run_scripts('pre', path, job)

    def post(self, job):
        path = job.config.get('plugins.jobscripts.post')
        self._run_scripts('post', path, job)
