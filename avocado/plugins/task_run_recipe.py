from avocado.core import nrunner
from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class TaskRunRecipe(CLICmd):

    name = 'task-run-recipe'
    description = "*EXPERIMENTAL* runner: runs one task from recipe file"

    def configure(self, parser):
        parser = super(TaskRunRecipe, self).configure(parser)
        for arg in nrunner.CMD_TASK_RUN_RECIPE_ARGS:
            parser.add_argument(*arg[0], **arg[1])

    def run(self, config):
        try:
            nrunner.subcommand_task_run_recipe(config, LOG_UI.info)
            return exit_codes.AVOCADO_ALL_OK
        except Exception as e:
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
