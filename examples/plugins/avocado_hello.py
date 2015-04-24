from avocado.core.plugins import plugin


class HelloWorld(plugin.Plugin):

    """
    The classical Hello World! plugin example.
    """

    name = 'hello_world'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the 'hello' action.
        """
        self.parser = parser.subcommands.add_parser(
            'hello',
            help='Hello World! plugin example')
        super(HelloWorld, self).configure(self.parser)

    def run(self, args):
        """
        This method is called whenever we use the command 'hello'.
        """
        print(self.__doc__)
