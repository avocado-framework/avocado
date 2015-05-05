.. _Writing Plugins:

Avocado Plugins
===============

In order to keep the code base approachable, and allow for cleanly extending
the test runner functionality, avocado has a plugin system. In order to
exemplify the concepts involved, let's use another old time favorite,
the "Print hello world" theme.

List available plugins
----------------------

Avocado has a builtin ``plugins`` command that lets you list available
plugins::

    $ avocado plugins
    Plugins loaded:
        test_lister - Implements the avocado 'list' functionality. (Enabled)
        sysinfo - Collect system information and log. (Enabled)
        test_runner - Implements the avocado 'run' functionality. (Enabled)
        xunit - xUnit output plugin. (Enabled)
        plugins_list - Implements the avocado 'plugins' functionality. (Enabled)

Now, let's write a simple plugin.

Writing a plugin to extend the runner functionality
---------------------------------------------------

Let's say you want to write a plugin that adds a new subcommand to the test
runner, ``hello``. This is how you'd do it::

    from avocado.core.plugins import plugin


    class HelloWorld(plugin.Plugin):

        """
        The classical Hello World! plugin example.
        """

        name = 'hello_world'
        enabled = True

        def configure(self, parser):
            self.parser = parser.subcommands.add_parser(
                'hello',
                help='Hello World! plugin example')
            super(HelloWorld, self).configure(self.parser)

        def run(self, args):
            print(self.__doc__)

As you can see, plugins inherit from :class:`avocado.core.plugins.plugin.Plugin`,
that have the methods :func:`avocado.core.plugins.plugin.Plugin.configure` and
:func:`avocado.core.plugins.plugin.Plugin.activate`. Configure does add the
command parser to the app test runner, and activate, if necessary will activate
your plugin, overriding avocado core functionality. In this configure method,
we added a new parser for the new command ``hello`` and automatically set
it to the method ``run``, that will print the plugin's docstring.

Make avocado aware of the new plugin
------------------------------------

Avocado has an option ``--plugins`` that allows you to provide a filesystem
location that contains plugins, that will be automatically loaded.

Note that all external plugins shall be prefixed with this ``avocado_`` name,
otherwise the Python module will be just ignored and no plugin inside
will be loaded!

In the avocado source tree, the ``avocado_hello.py`` example is available under
``examples/plugins``. So, in order to enable the hello plugin, you can do a::

    $ avocado --plugins examples/plugins/ plugins
    Plugins loaded:
        test_lister - Implements the avocado 'list' functionality. (Enabled)
        sysinfo - Collect system information and log. (Enabled)
        test_runner - Implements the avocado 'run' functionality. (Enabled)
        xunit - xUnit output plugin. (Enabled)
        plugins_list - Implements the avocado 'plugins' functionality. (Enabled)
        hello_world - The classical Hello World! plugin example. (Enabled)

Run it
------

To run it, you can simply call the newly registered runner command ``hello``::

    $ avocado --plugins examples/plugins/ hello
        The classical Hello World! plugin example.

Wrap Up
-------

We have briefly discussed the making of avocado plugins. A look at the module
:mod:`avocado.core.plugins` would be useful to look some of the other possibilities
available.
