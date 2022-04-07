import argparse
import inspect
import json
import os
import re
import sys

import pkg_resources

from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import TASK_DEFAULT_CATEGORY, Task


def _get_kind_options_from_executable_name():
    executable_name = os.path.basename(sys.argv[0])
    match = re.match(r'^avocado\-runner\-(.+)$', executable_name)
    options = {'type': str, 'help': 'Kind of runnable'}
    if match:
        options['required'] = False
        options['default'] = match.group(1)
        options['help'] += ', defaults to "%(default)s"'
    else:
        options['required'] = True
    return options


def _parse_key_val(argument):
    key_value = argument.split('=', 1)
    if len(key_value) < 2:
        msg = (f'Invalid keyword parameter: "{argument}". Valid option must '
               f'be a "KEY=VALUE" like expression')
        raise argparse.ArgumentTypeError(msg)
    return tuple(key_value)


class BaseRunnerApp:
    '''
    Helper base class for common runner application behavior
    '''

    #: The name of the command line application given to the command line
    #: parser
    PROG_NAME = ''

    #: The description of the command line application given to the
    #: command line parser
    PROG_DESCRIPTION = ''

    #: The names of types of runnables that this runner can handle.
    RUNNABLE_KINDS_CAPABLE = []

    #: The command line arguments to the "runnable-run" command
    CMD_RUNNABLE_RUN_ARGS = (
        (('-k', '--kind'),
         _get_kind_options_from_executable_name()),

        (('-u', '--uri'),
         {'type': str, 'default': None, 'help': 'URI of runnable'}),

        (('-c', '--config'),
         {'type': str, 'default': '{}', 'help': 'A config JSON data'}),

        (('-a', '--arg'),
         {'action': 'append', 'default': [],
          'help': 'Simple arguments to runnable'}),

        (('kwargs',),
         {'default': [], 'type': _parse_key_val, 'nargs': '*',
          'metavar': 'KEY_VAL',
          'help': 'Keyword (key=val) arguments to runnable'}),
    )

    CMD_RUNNABLE_RUN_RECIPE_ARGS = (
        (('recipe', ),
         {'type': str, 'help': 'Path to the runnable recipe file'}),
    )

    CMD_TASK_RUN_ARGS = (
        (('-i', '--identifier'),
         {'type': str, 'required': True, 'help': 'Task unique identifier'}),
        (('-t', '--category'),
         {'type': str, 'required': False, 'default': TASK_DEFAULT_CATEGORY,
          'help': (f'The category for tasks. Only tasks with category set '
                   f'to "{TASK_DEFAULT_CATEGORY}" (the default) will be '
                   f'included in the test results of its parent job. Other '
                   f'categories may be used for purposes that do include '
                   f'test results such as requirements resolution tasks')}),
        (('-s', '--status-uri'),
         {'action': 'append', 'default': None,
          'help': 'URIs of status services to report to'}),
        (('-j', '--job-id'),
         {'type': str, 'required': False, 'metavar': 'JOB_ID',
          'help': 'Identifier of Job this task belongs to'}),
    )
    CMD_TASK_RUN_ARGS += CMD_RUNNABLE_RUN_ARGS

    CMD_TASK_RUN_RECIPE_ARGS = (
        (('recipe', ),
         {'type': str, 'help': 'Path to the task recipe file'}),
    )

    CMD_STATUS_SERVER_ARGS = (
        (('uri', ),
         {'type': str, 'help': 'URI to bind a status server to'}),
    )

    def __init__(self, echo=print, prog=None, description=None):
        self.echo = echo
        self.parser = None
        if prog is None:
            prog = self.PROG_NAME
        if description is None:
            description = self.PROG_DESCRIPTION
        self._class_commands_method = self._get_commands_method()
        self._setup_parser(prog, description)

    def _setup_parser(self, prog, description):
        self.parser = argparse.ArgumentParser(prog=prog,
                                              description=description)
        subcommands = self.parser.add_subparsers(dest='subcommand')
        subcommands.required = True
        for command, method in self._class_commands_method.items():
            command_args = f"CMD_{command.upper().replace('-', '_')}_ARGS"
            command_parser = subcommands.add_parser(
                command,
                help=self._get_command_method_help_message(method))
            if hasattr(self, command_args):
                for arg in getattr(self, command_args):
                    command_parser.add_argument(*arg[0], **arg[1])

    def _get_commands_method(self):
        prefix = 'command_'
        return {c[0][len(prefix):].replace('_', '-'): getattr(self, c[0])
                for c in inspect.getmembers(self, inspect.ismethod)
                if c[0].startswith(prefix)}

    @staticmethod
    def _get_command_method_help_message(command_method):
        help_message = ''
        docstring = command_method.__doc__
        if docstring:
            docstring_lines = docstring.strip().splitlines()
            if docstring_lines:
                help_message = docstring_lines[0]
        return help_message

    def run(self):
        """
        Runs the application by finding a suitable command method to call
        """
        args = vars(self.parser.parse_args())
        subcommand = args.get('subcommand')
        kallable = self._class_commands_method.get(subcommand, None)
        if kallable is not None:
            return kallable(args)

    def get_commands(self):
        """
        Return the command names, as seen on the command line application

        For every method whose name starts with "command", and the name of
        the command follows, with underscores replaced by dashes.  So, a
        method named "command_foo_bar", will be a command available on the
        command line as "foo-bar".

        :rtype: list
        """
        return list(self._class_commands_method.keys())

    def get_capabilities(self):
        """
        Returns the runner capabilities, including runnables and commands

        This can be used by higher level tools, such as the entity spawning
        runners, to know which runner can be used to handle each runnable
        type.

        :rtype: dict
        """
        return {"runnables": self.RUNNABLE_KINDS_CAPABLE,
                "commands": self.get_commands(),
                "configuration_used": self.get_configuration_used_by_runners()}

    def get_runner_from_runnable(self, runnable):
        """
        Returns a runner that is suitable to run the given runnable

        :rtype: instance of class inheriting from :class:`BaseRunner`
        :raises: ValueError if runnable is now supported
        """
        runner = runnable.pick_runner_class()
        if runner is not None:
            return runner()
        raise ValueError(f'Unsupported kind of runnable: {runnable.kind}')

    def get_configuration_used_by_runners(self):
        """Returns the configuration keys used by capable runners.

        :returns: the configuration keys (aka namespaces) used by known runners
        :rtype: list
        """
        config_used = []
        for kind in self.RUNNABLE_KINDS_CAPABLE:
            for ep in pkg_resources.iter_entry_points(
                    'avocado.plugins.runnable.runner',
                    kind):
                try:
                    runner = ep.load()
                    config_used += runner.CONFIGURATION_USED
                except ImportError:
                    continue
        return list(set(config_used))

    def command_capabilities(self, _):
        """
        Outputs capabilities, including runnables and commands

        The output is intended to be consumed by upper layers of Avocado, such
        as the Job layer selecting the right runner script to handle a runnable
        of a given kind, or identifying if a runner script has a given feature
        (as implemented by a command).
        """
        self.echo(json.dumps(self.get_capabilities()))

    def command_runnable_run(self, args):
        """
        Runs a runnable definition from arguments

        This defines a Runnable instance purely from the command line
        arguments, then selects a suitable Runner, and runs it.

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_args(args)
        runner = self.get_runner_from_runnable(runnable)
        for status in runner.run(runnable):
            self.echo(status)

    def command_runnable_run_recipe(self, args):
        """
        Runs a runnable definition from a recipe

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_recipe(args.get('recipe'))
        runner = self.get_runner_from_runnable(runnable)
        for status in runner.run(runnable):
            self.echo(status)

    def command_task_run(self, args):
        """
        Runs a task from arguments

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_args(args)
        task = Task(runnable, args.get('identifier'),
                    args.get('status_uri', []),
                    category=args.get('category', TASK_DEFAULT_CATEGORY),
                    job_id=args.get('job_id'))
        for status in task.run():
            self.echo(status)

    def command_task_run_recipe(self, args):
        """
        Runs a task from a recipe

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        task = Task.from_recipe(args.get('recipe'))
        for status in task.run():
            self.echo(status)
