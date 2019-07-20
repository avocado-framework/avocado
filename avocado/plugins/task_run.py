from avocado.core import nrunner
from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class TaskRun(CLICmd):

    name = 'task-run'
    description = "*EXPERIMENTAL* runner: runs one task"

    def configure(self, parser):
        parser = super(TaskRun, self).configure(parser)

        for arg in nrunner.CMD_TASK_RUN_ARGS:
            parser.add_argument(*arg[0], **arg[1])

    def run(self, config):
        try:
            nrunner.subcommand_task_run(config, LOG_UI.info)
            return exit_codes.AVOCADO_ALL_OK
        except Exception as e:
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
