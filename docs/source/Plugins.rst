Plugin System
=============

Avocado has a plugin system that can be used to extended it in a clean way.

Listing plugins
---------------

The ``avocado`` command line tool has a builtin ``plugins`` command that lets
you list available plugins. The usage is pretty simple::

 $ avocado plugins
 Plugins enabled:
    config                               Implements the avocado 'config' subcommand
    distro                               Implements the avocado 'distro' subcommand
    exec_path                            Implements the avocado 'exec-path' subcommand
    gdb                                  Run tests with GDB goodies enabled
    htmlresult                           HTML job report
    json                                 JSON output
    ...

Since plugins are (usually small) bundles of Python code, they may fail to load if
the Python code is broken for any reason. Example::

 $ avocado plugins
 Plugins enabled:
    config                               Implements the avocado 'config' subcommand
  ...
  Unloadable plugin modules:
    avocado.core.plugins.htmlresult      ImportError No module named pystache

Besides load errors, plugins may also disable themselves due to, say, missing
requirements on your environment. This is the case for the ``run_vm`` plugin when
it's run on machine not capable of (``libvirt`` based) virtualization::

 $ avocado plugins
  Plugins enabled:
    config                               Implements the avocado 'config' subcommand
  ...
  Plugins disabled:
    run_vm                               Disabled during plugin configuration

.. _Writing Plugins:

Writing a plugin
----------------

What better way to understand how an Avocado plugin works than creating one?
Let's use another old time favorite for that, the "Print hello world" theme.

Code example
~~~~~~~~~~~~

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

As you can see, plugins inherit from :class:`avocado.core.plugins.plugin.Plugin`.
Its most important methods are :func:`configure
<avocado.core.plugins.plugin.Plugin.configure>`, :func:`run
<avocado.core.plugins.plugin.Plugin.run>` and
:func:`activate <avocado.core.plugins.plugin.Plugin.activate>`.

:func:`configure <avocado.core.plugins.plugin.Plugin.configure>` adds the command
parser to the test runner. In this code example method, we added a new parser for
the new ``hello`` command.

The :func:`run <avocado.core.plugins.plugin.Plugin.run>` method is the main entry
point. In this code example it will simply print the plugin's docstring.

:func:`activate <avocado.core.plugins.plugin.Plugin.activate>`, if necessary,
will activate your plugin, overriding Avocado core functionality.


Wrap Up
~~~~~~~

We have briefly discussed the making of Avocado plugins. A look at the module
:mod:`avocado.core.plugins` is also recommended.
