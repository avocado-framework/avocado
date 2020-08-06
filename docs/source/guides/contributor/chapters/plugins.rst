*************************
Writing an Avocado plugin
*************************

What better way to understand how an Avocado plugin works than creating one?
Let's use another old time favorite for that, the "Print hello world" theme.

Code example
============

Let's say you want to write a plugin that adds a new subcommand to the test
runner, ``hello``. This is how you'd do it:

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello/hello.py

This plugins inherits from
:class:`avocado.core.plugin_interfaces.CLICmd`.  This specific base
class allows for the creation of new commands for the Avocado CLI
tool. The only mandatory method to be implemented is :func:`run
<avocado.core.plugin_interfaces.CLICmd.run>` and it's the plugin main
entry point.

This plugin uses :py:data:`avocado.core.output.LOG_UI` to produce the hello
world output in the console.

.. note:: Different loggers can be used in other contexts and for
          different purposes.  One such example is
          :py:data:`avocado.core.output.LOG_JOB`, which can be used to
          output to job log files when running a job.

Registering Plugins
===================

Avocado makes use of the `setuptools` and its `entry points` to register and
find Python objects. So, to make your new plugin visible to Avocado, you need
to add to your setuptools based `setup.py` file something like:

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello/setup.py

Then, by running either ``$ python setup.py install`` or ``$ python setup.py
develop`` your plugin should be visible to Avocado.

Namespace
=========

The plugin registry mentioned earlier, (`setuptools` and its `entry points`) is
global to a given Python installation.  Avocado uses the namespace prefix
``avocado.plugins.`` to avoid name clashes with other software.  Now, inside
Avocado itself, there's no need keep using the ``avocado.plugins.`` prefix.

Take for instance, the Job Pre/Post plugins are defined on ``setup.py``::

  'avocado.plugins.job.prepost': [
     'jobscripts = avocado.plugins.jobscripts:JobScripts'
  ]

The setuptools entry point namespace is composed of the mentioned prefix
``avocado.plugins.``, which is is then followed by the Avocado plugin type, in
this case, ``job.prepost``.

Inside Avocado itself, the fully qualified name for a plugin is the plugin
type, such as ``job.prepost`` concatenated to the name used in the entry point
definition itself, in this case, ``jobscripts``.

To summarize, still using the same example, the fully qualified Avocado plugin
name is going to be ``job.prepost.jobscripts``.


Plugin config files
===================

Plugins can extend the list of config files parsed by ``Settings`` objects by
dropping the individual config files into ``/etc/avocado/conf.d``
(linux/posix-way) or they can take advantages of the Python entry point using
``avocado.plugins.settings``.

1. `/etc/avocado/conf.d`:

In order to not disturb the main Avocado config file, those plugins, if they
wish so, may install additional config files to
``/etc/avocado/conf.d/[pluginname].conf``, that will be parsed after the system
wide config file. Users can override those values as well at the local config
file level. Considering the config for the hypothethical plugin ``salad``:

.. code-block:: ini

    [salad.core]
    base = ceasar
    dressing = ceasar

If you want, you may change ``dressing`` in your config file by simply adding a
``[salad.core]`` new section in your local config file, and set a different
value for ``dressing`` there.

2. `avocado.plugins.settings`:

This entry-point uses ``avocado.core.plugin_interfaces.Settings``-like object
to extend the list of parsed files. It only accepts individual files, but you
can use something like ``glob.glob("*.conf")`` to add all config files inside a
directory.

You need to create the plugin (eg. ``my_plugin/settings.py``)::

   from avocado.core.plugin_interfaces import Settings

   class MyPluginSettings(Settings):
       def adjust_settings_paths(self, paths):
           paths.extend(glob.glob("/etc/my_plugin/conf.d/*.conf"))


And register it in your ``setup.py`` entry-points::

   from setuptools import setup
   ...
   setup(name="my-plugin",
         entry_points={
             'avocado.plugins.settings': [
                 "my-plugin-settings = my_plugin.settings.MyPluginSettings",
                 ],
             ...

Which extends the list of files to be parsed by settings object. Note this
has to be executed early in the code so try to keep the required deps
minimal (for example the `avocado.core.settings.settings` is not yet
available).
