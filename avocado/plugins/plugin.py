"""Plugins basic structure."""


class Plugin(object):

    """
    Base class for plugins.

    You'll inherit from this to write you own plugins.
    """

    def __init__(self, name=None, enabled=False):
        """Creates a new plugin instance.

        :param name: plugin name
        :param enabled: enabled/disabled status
        """
        if name is None:
            name = self.__class__.__name__.lower()
        self.name = name
        self.enabled = enabled

    def configure(self, parser):
        """Configuration and argument parsing.

        :param parser: a subparser of `ArgumentParser`
        """
        raise NotImplementedError('Plugins must implement the method configure')
