Plugin System
=============

Avocado has a plugin system that can be used to extended it in a clean way.

Listing plugins
---------------

The ``avocado`` command line tool has a builtin ``plugins`` command that lets
you list available plugins. The usage is pretty simple::

 $ avocado plugins
 Plugins that add new commands (avocado.plugins.cli.cmd):
 exec-path Returns path to avocado bash libraries and exits.
 run       Run one or more tests (native test, test alias, binary or script)
 sysinfo   Collect system information
 ...
 Plugins that add new options to commands (avocado.plugins.cli):
 remote  Remote machine options for 'run' subcommand
 journal Journal options for the 'run' subcommand
 ...

Since plugins are (usually small) bundles of Python code, they may fail to load if
the Python code is broken for any reason. Example::

 $ avocado plugins
 Failed to load plugin from module "avocado.plugins.exec_path": ImportError('No module named foo',)
 Plugins that add new commands (avocado.plugins.cli.cmd):
 run       Run one or more tests (native test, test alias, binary or script)
 sysinfo   Collect system information
 ...

.. _Writing Plugins:

Writing a plugin
----------------

What better way to understand how an Avocado plugin works than creating one?
Let's use another old time favorite for that, the "Print hello world" theme.

Code example
~~~~~~~~~~~~

Let's say you want to write a plugin that adds a new subcommand to the test
runner, ``hello``. This is how you'd do it::

    from avocado.plugins.base import CLICmd


    class HelloWorld(CLICmd):

        name = 'hello'
        description = 'The classical Hello World! plugin example.'

        def run(self, args):
            print(self.description)

As you can see, this plugins inherits from :class:`avocado.plugins.base.CLICmd`.
This specific base class allows for the creation of new commands for the Avocado
CLI tool. The only mandatory method to be implemented is :func:`run
<avocado.plugins.base.CLICmd.run>` and it's the plugin main entry point.
In this code example it will simply print the plugin's description.

Registering Plugins
~~~~~~~~~~~~~~~~~~~

Avocado makes use of the `Stevedore`_ library to load and activate plugins.
Stevedore itself uses `setuptools`_ and its `entry points`_ to register
and find Python objects. So, to make your new plugin visible to Avocado, you need
to add to your setuptools based `setup.py` file something like::

 setup(name='mypluginpack',
 ...
 entry_points={
    'avocado.plugins.cli': [
       'hello = mypluginpack.hello:HelloWorld',
    ]
 }
 ...

Then, by running either ``$ python setup.py install`` or ``$ python setup.py
develop`` your plugin should be visible to Avocado.

Wrap Up
~~~~~~~

We have briefly discussed the making of Avocado plugins. We recommend
the `Stevedore documentation`_ and also a look at the
:mod:`avocado.plugins.base` module for the various plugin interface definitions.

Some plugins examples are available in the `Avocado source tree`_, under ``examples/plugins``.

Finally, exploring the real plugins shipped with Avocado in :mod:`avocado.plugins`
is the final "documentation" source.


.. _Stevedore: https://github.com/openstack/stevedore
.. _Stevedore documentation: http://docs.openstack.org/developer/stevedore/index.html
.. _setuptools: https://pythonhosted.org/setuptools/
.. _entry points: https://pythonhosted.org/setuptools/pkg_resources.html#entry-points
.. _Avocado source tree: https://github.com/avocado-framework/avocado/tree/master/examples/plugins
