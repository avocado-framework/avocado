.. _writing_plugin:

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

If your plugin has options available to the users, register it using the
:meth:`.Settings.register_option()` method during your plugin configuration
stage. The options are parsed and provided to the plugin as a config dictionary.

Let’s take our Hello World example and change the message based on a “message”
option:

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello_option/hello_option.py

The code in the example above registers a **configuration namespace**
(*hello.message*) inside the configuration file only. A namespace is a
**section** (*hello*) followed by a **key** (*message*). In other words, the
following entry in your configuration file is also valid and will be parsed::

  [hello]
  message = My custom message

As you can see in the example above, you need to set a **default** value and
this value will be used if the option is not present in the configuration file.
This means that you can have a very small configuration file or even an empty
one.

This is a very basic example of how to configure options inside your plugin.

Adding command-line options
---------------------------

Now, let’s say you would like to also allow this change via the command-line
option of your plugin (if your plugin is a command-line plugin). You need to
register in any case and use the same method to connect your **option namespace**
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
``avocado.plugins.``, which is then followed by the Avocado plugin type, in
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
    base = caesar
    dressing = caesar

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

.. _plugins_execution_order:

Plugins execution order
=======================
Avocado lets plugin developers to define plugin priority, which ensures the
default execution order.The plugins with higher priority will be executed
earlier than the plugins with lower priority. The priorities are on the scale
between 0-100 and as default all plugins have priority set to
NORMAL (50). For easier usage, avocado has predefined
values in: 

.. autoclass:: avocado.core.extension_manager.PluginPriority
   :noindex:
   :members:
   :undoc-members:

To define a priority for plugin, you have to create class attribute ``priority``
same as you're defining ``name`` and ``description``:

.. literalinclude:: ../../../../../examples/plugins/cli-cmd/hello_priority/hello_priority.py

Now, the plugin ``HelloWorld`` has priority high and will be executed before
every plugin without priority variable (default priority).

As a plugin developer, you have to consider that users can change the execution
order by ``plugins.$type.order`` option. In such case, at first will be executed
the plugins from ``plugins.$type.order`` and then the rest of plugins by its
priority. For example the default order is [plugin1, plugin2, plugin3, plugin4]
the ``plugins.$type.order`` is [plugin2, plugin4] then the real order will be
[plugin2, plugin4, plugin1, plugin3]

.. _new-test-type-plugin-example:

Cacheable plugins
=================
The results of Pre-test and Post-test plugins defined in :class:`avocado.core.plugin_interfaces.PreTest`
and :class:`avocado.core.plugin_interfaces.PostTest` can be saved in cache. This is 
very useful If the results can be used by other tests or even other avocado executions. 
As an example of such plugin is `Dependency resolver` in :ref:`managing-requirements` 
which installs dependencies for test into the test environment.

As a default, all pre- / post-plugins are noncacheable. To make plugin cacheable you 
have to set plugin variable `is_cacheable` to `True`, like this:

.. literalinclude:: ../../../../../examples/plugins/test-pre-post/hello/hello.py

New test type plugin example
============================

For a new test type to be recognized and executed by Avocado's nrunner
architecture, there needs to be two types of plugins and one optional:

 * resolvers: they resolve references into proper test descriptions
   that Avocado can run.

 * discoverers (optional): They are doing the same job as resolvers but
   without a reference. They are used when the tests can be created from
   different data e.g. *config files*.

 * runners: these make use of the resolutions made by resolvers and
   actually execute the tests, reporting the results back to Avocado

The following example shows real code for a resolver and a runner for
a *magic* test type.  This *magic* test simply passes or fails
depending on the test reference.

Resolver and Discoverer example
-------------------------------

The resolver implementation will simply set the test type (*magic*)
and transform the reference given into its **url**:

.. literalinclude:: ../../../../../examples/plugins/tests/magic/avocado_magic/resolver.py

Tests contained in files and associated data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``magic`` test does *not* depend on a file, only on the "magic" word
(either "pass" or "fail").  Because of that, there's no need to
provide information at resolution time about the file(s) comprising
the magic tests.

For most other test types, though, the test will be contained within a
file, and/or may be comprised by many supplemental files containing
test specific data.  While local execution of a test will easily find
those files, in order to be prepared for the execution of a test in
different environments (by different spawners), it's recommended that
the resolver (and discoverer) provide that kind of information.

A feature that is strongly recommended to be implemented by resolvers
and discoverers of tests that are file-based is the ``.data``
directory support.  Whenever a test contained in a file has a matching
directory with the ``.data`` :data:`suffix
<avocado.core.test.TestData.SUFFIX>`, the test can get quick access to
these files with the :meth:`get_data
<avocado.core.test.TestData.get_data>` method.

To do so, use the ``assets`` keyword argument when creating
:class:`Runnable <avocado.core.nrunner.runnable.Runnable>` instances.
The ``assets`` keyword argument takes a list of tuples with ``(type,
path)`` tuples, which will then be available at the :data:`Runnable
<avocado.core.nrunner.runnable.Runnable.assets>` attribute.
Actual examples are available in the implementation of the
``exec-test`` and similar builtin resolvers.

For the file that contains the test, it's recommended that resolvers
and discoverers use the type
:data:`avocado.core.resolver.ReferenceResolutionAssetType.TEST_FILE`.
For other data files, use the
:data:`avocado.core.resolver.ReferenceResolutionAssetType.DATA_FILE`.

Runner example
--------------

The runner will receive the
:class:`avocado.core.nrunner.runnable.Runnable` information
created by the resolver plugin.  Runners can be written in any
language, but this implementation reuses some base Python classes.

First, :class:`avocado.core.nrunner.runner.BaseRunner` is used to write the
runner **class**.  And second, the
:class:`avocado.core.nrunner.app.BaseRunnerApp` is used to create the command
line application, which uses the previously implemented runner class
for ``magic`` test types.

.. literalinclude:: ../../../../../examples/plugins/tests/magic/avocado_magic/runner.py

A runner is free to make use of all the information in the
:class:`avocado.core.nrunner.runnable.Runnable` that the resolver
implementation populates.  In this particular example it only makes
use of the :attr:`uri <avocado.core.nrunner.runnable.Runnable.uri>`
attribute.  If a runner needs to behave accordingly to some
Avocado configuration, you need to declare that configuration in
the :attr:`CONFIGURATION_USED
<avocado.core.nrunner.runner.BaseRunner.CONFIGURATION_USED>` class
attribute and then you can access it in :attr:`config
<avocado.core.nrunner.runnable.Runnable.config>`.

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
can be seen by running ``avocado list magic:pass magic:fail``::

  magic magic:pass
  magic magic:fail

And you may get more insight into the resolution results, by adding a
verbose parameter and another reference.  Try running ``avocado -V
list magic:pass magic:fail magic:foo something-else``::

  Reference magic:foo might be resolved by magic resolver, but the file is corrupted: Word "magic:foo" is magic type but the foo is not a valid magic word
  Type  Test       Tag(s)
  magic magic:pass
  magic magic:fail

  Resolver             Reference      Info
  avocado-instrumented magic:pass     File name "magic" does not end with suffix ".py"
  golang               magic:pass     go binary not found
  avocado-instrumented magic:fail     File name "magic" does not end with suffix ".py"
  golang               magic:fail     go binary not found
  avocado-instrumented magic:foo    File name "magic" does not end with suffix ".py"
  golang               magic:foo    go binary not found
  magic                magic:foo    Word "magic:foo" is magic type but the foo is not a valid magic word
  avocado-instrumented something-else File name "something-else" does not end with suffix ".py"
  golang               something-else go binary not found
  magic                something-else Word "something-else" is not a valid magic word
  python-unittest      something-else File name "something-else" does not end with suffix ".py"
  robot                something-else File name "something-else" does not end with suffix ".robot"
  rogue                something-else Word "something-else" is not the magic word
  exec-test            something-else File "something-else" does not exist or is not a executable file
  tap                  something-else File "something-else" does not exist or is not a executable file

  TEST TYPES SUMMARY
  ==================
  magic: 2

It's worth realizing that magic (and other plugins) were asked to
resolve the ``magic:foo`` and ``something-else`` references, but couldn't::

  Resolver             Reference      Info
  ...
  magic                magic:foo    Word "magic:foo" is magic type but the foo is not a valid magic word
  ...
  magic                something-else Word "something-else" is not a valid magic word
  ...

We can see that the reference "magic:foo" resembles the magic words by
type but it is not magic words ``pass`` or ``fail``.  Consequently,
the resolver can provide the user with information about potentially
corrupted references.  This can assist the user in identifying typos
or reference mistakes. As the creator of the resolver, you can use the
:data:`avocado.core.resolver.ReferenceResolutionResult.CORRUPT` variable
to notify the user of such a situation.

Running magic tests
-------------------

The common way of running Avocado tests is to run them through
``avocado run``.  To run both the ``pass`` and ``fail`` magic tests,
you'd run ``avocado run -- magic:pass magic:fail``::

  $ avocado run -- magic:pass magic:fail
  JOB ID     : 86fd45f8c1f2fe766c252eefbcac2704c2106db9
  JOB LOG    : $HOME/avocado/job-results/job-2021-02-05T12.43-86fd45f/job.log
   (1/2) magic:pass: STARTED
   (1/2) magic:pass: PASS (0.00 s)
   (2/2) magic:fail: STARTED
   (2/2) magic:fail: FAIL (0.00 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : $HOME/avocado/job-results/job-2021-02-05T12.43-86fd45f/results.html
  JOB TIME   : 1.83 s
