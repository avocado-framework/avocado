from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class HelloWorld(CLICmd):

    name = 'hello_parser'
    description = "The classical Hello World plugin example!"

    def configure(self, parser):
        parser = super().configure(parser)

        settings.register_option(section='hello',
                                 key='message',
                                 key_type=str,
                                 default=self.description,
                                 help_msg="Configure the message to display",
                                 parser=parser,
                                 long_arg='--hello-message')

    def run(self, config):
        msg = config.get('hello.message')
        LOG_UI.info(msg)
