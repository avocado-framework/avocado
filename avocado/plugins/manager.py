"""Plugin Managers."""

from avocado.plugins.builtin import load_builtins

DefaultPluginManager = None


class PluginManager(object):

    """
    Base class for plugins manager.

    You'll inherit from this to write you own plugins manager.
    """

    def __init__(self):
        self.plugins = []

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def load_plugins(self):
        raise NotImplementedError('Managers must implement the method load_plugins')

    def configure(self, parser):
        raise NotImplementedError('Managers must implement the method configure')


class BuiltinPluginManager(PluginManager):

    """
    Builtins plugin manager.
    """

    def load_plugins(self):
        for plugin in load_builtins():
            self.add_plugin(plugin())

    def configure(self, parser):
        for plugin in self.plugins:
            plugin.configure(parser)


def get_plugin_manager():
    """
    Get default plugin manager.
    """
    global DefaultPluginManager
    if DefaultPluginManager is None:
        DefaultPluginManager = BuiltinPluginManager()
    return DefaultPluginManager
