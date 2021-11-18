from avocado.core.plugin_interfaces import CLI
from avocado.core.settings import settings


class SpawnerCLI(CLI):

    name = 'spawner'
    description = 'spawner command line options for "run"'

    def configure(self, parser):
        super(SpawnerCLI, self).configure(parser)
        parser = parser.subcommands.choices.get('run', None)
        if parser is None:
            return

        parser = parser.add_argument_group('spawner specific options')
        help_msg = ("This will disable the fetching output files from test "
                    "environment. This might be useful when you are running the "
                    "tests in different environment than avocado, like external "
                    "machine, and fetching might be time-consuming.")
        settings.register_option(section='test.output',
                                 key='enabled',
                                 default=True,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--disable-test-output-fetch')

    def run(self, config):
        pass
