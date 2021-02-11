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

Registering configuration options (settings)
============================================

It is usual for a plugin to allow users to do  some degree of configuration
based on command-line options and/or configuration options. A plugin might
change its behavior depending on a specific configuration option.

Frequently, those settings come from configuration files and, sometimes, from
the command-line arguments. Like in most UNIX-like tools, command-line options
will override values defined inside the configuration files.

You, as a plugin writer, don’t need to handle this configuration by yourself.
Avocado provides a common API that can be used by plugins in order to register
options and get values.

If your plugin has options available to the users, it can register it using the
:meth:`.Settings.register_option()` method during your plugin configuration
stage. The options are parsed and provided to the plugin as a config dictionary.

Let’s take our Hello World example and change the message based on a “message”
option:

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello_option/hello_option.py

This registration will register a “configuration namespace" (“hello.message”)
inside the configuration file only. A namespace is a “section” (“hello”)
followed by a “key” (“message”). In other words, the following entry in your
configuration file is valid and will be parsed::

  [hello]
  message = My custom message

As you can see in the example above, you need to set a “default” value and this
value will be used if the option is not present in the configuration file. This
means that you can have a very small configuration file or even an empty one.

This is a very basic example of how to configure options inside your plugin.

Adding command-line options
---------------------------

Now, let’s say you would like to also allow this change via the command-line
option of your plugin (if your plugin is a command-line plugin). You need to
register in any case and use the same method to connect your “option namespace”
with your command-line option.

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello_parser/hello_parser.py

.. note:: Keep in mind that not all options should have a “command-line”
  option. Try to keep the command-line as clean as possible. We use command-line
  only for options that constantly need to change and when editing the
  configuration file is not handy.

For more information about how this registration process works, visit the
:meth:`.Settings.register_option()` method documentation.

.. _registering-plugins:

Registering plugins
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

New test type plugin example
============================

For a new test type to be recognized and executed by Avocado's "nrunner"
architecture, there needs to be two types of plugins:

 * resolvers: they resolve references into proper test descriptions
   that Avocado can run

 * runners: these make use of the resolutions made by resolvers and
   actually execute the tests, reporting the results back to Avocado

The following example shows real code for a resolver and a runner for
a "magic" test type.  This "magic" test simply passes or fails
depending on the test reference.

Resolver example
----------------

The resolver implementation will simply set the test type ("magic")
and transform the reference given into its "url":

.. literalinclude:: ../../../../../examples/plugins/tests/magic/avocado_magic/resolver.py

Runner example
--------------

The runner will receive the ``Runnable`` information created by the
resolver plugin.   Runners can be written in any language, but this
implementation reuses some base Python classes.

First, :class:`avocado.core.nrunner.BaseRunner` is used to write the
runner **class**.  And second, the
:class:`avocado.core.nrunner.BaseRunner` is used to create the command
line application, which uses the previously implemented runner class
for ``magic`` test types.

.. literalinclude:: ../../../../../examples/plugins/tests/magic/avocado_magic/runner.py

Activating the new test type plugins
------------------------------------

The plugins need to be registered so that Avocado knows about it.  See
:ref:`registering-plugins` for more information.  This is the code
that can be used to register these plugins:

.. literalinclude:: ../../../../../examples/plugins/tests/magic/setup.py

With that, you need to either run ``python setup.py install`` or
``python setup.py develop``.

.. note:: The last entry, registering a ``console_script``, is
          recommended because it allows one to experiment with the
          runner as a command line application
          (``avocado-runner-magic`` in this case).  Also, depending on
          the spawner implementation used to run the tests, having a
          runner that can be executed as an application (and not a
          Python class) is a requirement.

Listing the new test type plugins
---------------------------------

With the plugins activated, you should be able to run ``avocado plugins`` and
find (among other output)::

  Plugins that resolve test references (resolver):
  ...
  magic                Test resolver for magic words
  ...

Resolving magic tests
---------------------

Resolving the "pass" and "fail" references that the magic plugin knows about
can be seen by running ``avocado list --resolver pass fail``::

  magic pass
  magic fail

And you may get more insight into the resolution results, by adding a
verbose parameter and another reference.  Try running ``avocado -V
list --resolver pass fail something-else``::

  Type  Test Tag(s)
  magic pass
  magic fail

  Resolver             Reference      Info
  avocado-instrumented pass           File "pass" does not end with ".py"
  exec-test            pass           File "pass" does not exist or is not a executable file
  golang               pass
  avocado-instrumented fail           File "fail" does not end with ".py"
  exec-test            fail           File "fail" does not exist or is not a executable file
  golang               fail
  avocado-instrumented something-else File "something-else" does not end with ".py"
  exec-test            something-else File "something-else" does not exist or is not a executable file
  golang               something-else
  magic                something-else Word "something-else" is not a valid magic word
  python-unittest      something-else File "something-else" does not end with ".py"
  robot                something-else File "something-else" does not end with ".robot"
  tap                  something-else File "something-else" does not exist or is not a executable file

  TEST TYPES SUMMARY
  ==================
  magic: 2

It's worth realizing that magic (and other plugins) were asked to
resolve the ``something-else`` reference, but couldn't::

  Resolver             Reference      Info
  ...
  magic                something-else Word "something-else" is not a valid magic word
  ...

Running magic tests
-------------------

The common way of running Avocado tests is to run them through
``avocado run``.  In this case, we're discussing tests for the
"nrunner" architecture, so the common way of running these "magic"
tests is through a command starting with ``avocado
run --test-runner=nrunner``.

To run both the ``pass`` and ``fail`` magic tests, you'd run
``avocado run --test-runner=nrunner -- pass fail``::

  $ avocado run --test-runner=nrunner -- pass fail
  JOB ID     : 86fd45f8c1f2fe766c252eefbcac2704c2106db9
  JOB LOG    : $HOME/avocado/job-results/job-2021-02-05T12.43-86fd45f/job.log
   (1/2) pass: STARTED
   (1/2) pass: PASS (0.00 s)
   (2/2) fail: STARTED
   (2/2) fail: FAIL (0.00 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : $HOME/avocado/job-results/job-2021-02-05T12.43-86fd45f/results.html
  JOB TIME   : 1.83 s
