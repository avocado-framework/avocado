from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class HelloWorld(CLICmd):

    name = 'hello'
    description = 'The classical Hello World! plugin example.'

    def run(self, config):
        LOG_UI.info(self.description)
