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

    from avocado.core.output import LOG_JOB
    from avocado.core.plugin_interfaces import CLICmd


    class HelloWorld(CLICmd):

        name = 'hello'
        description = 'The classical Hello World! plugin example.'

        def run(self, args):
            LOG_JOB.info(self.description)

As you can see, this plugins inherits from :class:`avocado.core.plugin_interfaces.CLICmd`.
This specific base class allows for the creation of new commands for the Avocado
CLI tool. The only mandatory method to be implemented is :func:`run
<avocado.core.plugin_interfaces.CLICmd.run>` and it's the plugin main entry point.

This plugin uses :py:data:`avocado.core.output.LOG_JOB` to produce the hello
world output in the Job log. One can also use
:py:data:`avocado.core.output.LOG_UI` to produce output in the human readable
output.

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

Fully qualified named for a plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The plugin registry mentioned earlier, (`setuptools`_ and its `entry
points`_) is global to a given Python installation.  Avocado uses the
namespace prefix ``avocado.plugins.`` to avoid name clashes with other
software.  Now, inside Avocado itself, there's no need keep using the
``avocado.plugins.`` prefix.

Take for instance, the Job Pre/Post plugins are defined on
``setup.py``::

  'avocado.plugins.job.prepost': [
     'jobscripts = avocado.plugins.jobscripts:JobScripts'
  ]

The setuptools entry point namespace is composed of the mentioned
prefix ``avocado.plugins.``, which is is then followed by the Avocado
plugin type, in this case, ``job.prepost``.

Inside avocado itself, the fully qualified name for a plugin is the
plugin type, such as ``job.prepost`` concatenated to the name used in
the entry point definition itself, in this case, ``jobscripts``.

To summarize, still using the same example, the fully qualified
Avocado plugin name is going to be ``job.prepost.jobscripts``.

.. _disabling-a-plugin:

Disabling a plugin
~~~~~~~~~~~~~~~~~~

Even though a plugin can be installed and registered under
`setuptools`_ `entry points`_, it can be explicitly disabled in
Avocado.

The mechanism available to do so is to add entries to the ``disable``
key under the ``plugins`` section of the Avocado configuration file.
Example::

  [plugins]
  disable = ['cli.hello', 'job.prepost.jobscripts']

The exact effect on Avocado when a plugin is disabled depends on the
plugin type.  For instance, by disabling plugins of type ``cli.cmd``,
the command implemented by the plugin should no longer be available on
the Avocado command line application.  Now, by disabling a
``job.prepost`` plugin, those won't be executed before/after the
execution of the jobs.

Default plugin execution order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In many situations, such as result generation, not one, but all of the
enabled plugin types will be executed.  The order in which the plugins
are executed follows the lexical order of the entry point name.

For example, for the JSON result plugin, whose fully qualified name
is ``result.json``, has an entry point name of ``json``, as can be seen
on its registration code in ``setup.py``::

   ...
   entry_points={
      'avocado.plugins.result': [
         'json = avocado.plugins.jsonresult:JSONResult',
   ...

If it sounds too complicated, it isn't.  It just means that for
plugins of the same type, a plugin named ``automated`` will be
executed before the plugin named ``uploader``.

In the default Avocado set of result plugins, it means that the JSON
plugin (``json``) will be executed before the XUnit plugin (``xunit``).
If the HTML result plugin is installed and enabled (``html``) it will
be executed before both JSON and XUnit.

Configuring the plugin execution order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On some circumstances it may be necessary to change the order in which plugins
are executed.  To do so, add a ``order`` entry a configuration file section
named after the plugin type.  For ``job.prepost`` plugin types, the section name
has to be named ``plugins.job.prepost``, and it would look like this::

  [plugins.job.prepost]
  order = ['myplugin', 'jobscripts']

That configuration sets the ``job.prepost.myplugin`` plugin to execute before
the standard Avocado ``job.prepost.jobscripts`` does.

Wrap Up
~~~~~~~

We have briefly discussed the making of Avocado plugins. We recommend
the `Stevedore documentation`_ and also a look at the
:mod:`avocado.core.plugin_interfaces` module for the various plugin interface definitions.

Some plugins examples are available in the `Avocado source tree`_, under ``examples/plugins``.

Finally, exploring the real plugins shipped with Avocado in :mod:`avocado.plugins`
is the final "documentation" source.


.. _Stevedore: https://github.com/openstack/stevedore
.. _Stevedore documentation: http://docs.openstack.org/developer/stevedore/index.html
.. _setuptools: https://setuptools.readthedocs.io/en/latest/
.. _entry points: https://setuptools.readthedocs.io/en/latest/pkg_resources.html#entry-points
.. _Avocado source tree: https://github.com/avocado-framework/avocado/tree/master/examples/plugins
