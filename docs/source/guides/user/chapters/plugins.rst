Understanding the plugin system
===============================

Avocado has a plugin system that can be used to extended it in a clean way.

.. note:: A large number of out-of-the-box Avocado features are
  implemented as using the same plugin architecture available to
  third-party extensions.

  This guide considers "core features", even though they're still
  'plugable', those available with an installation of Avocado by itself
  (``pip install avocado-framework``).  If a feature is part of an
  optional or third-party plugin package, this guide will reference it."

Listing plugins
---------------

The ``avocado`` command line tool has a builtin ``plugins`` command that lets
you list available plugins. The usage is pretty simple::

 $ avocado plugins
 Plugins that add new commands (avocado.plugins.cli.cmd):
 exec-path Returns path to Avocado bash libraries and exits.
 run       Run one or more tests (native test, test alias, binary or script)
 sysinfo   Collect system information
 ...
 Plugins that add new options to commands (avocado.plugins.cli):
 journal Journal options for the 'run' subcommand
 ...

Since plugins are (usually small) bundles of Python code, they may fail to load
if the Python code is broken for any reason. Example::

 $ avocado plugins
 Failed to load plugin from module "avocado.plugins.exec_path": ImportError('No module named foo',)
 Plugins that add new commands (avocado.plugins.cli.cmd):
 run       Run one or more tests (native test, test alias, binary or script)
 sysinfo   Collect system information
 ...


Fully qualified named for a plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado plugin system uses namespaces to recognize and categorize plugins.
The namespace separator here is the dot and every plugin that starts with
``avocado.plugins.`` will be recognized by the framework.

An example of a plugin's full qualified name:

``avocado.plugins.result.json``

This plugin will generate the job result in JSON format.

.. note:: Inside Avocado we will omit the prefix 'avocado.plugins' to make the
  things clean.

.. note:: When listing plugins with ``avocado plugins`` pay attention to the
  namespace inside the parenthesis on each category description. You will realize
  that there are, for instance, two plugins with the name 'JSON'. But when you
  concatenate the fully qualified name it will become clear that they are
  actually two  different plugins: ``result.json`` and ``cli.json``.


.. _disabling-a-plugin:

Disabling a plugin
-------------------

If you, as Avocado user, would like to disable a plugin, kkyou can disable on config files:
points`_, it can be explicitly disabled in Avocado.

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

Plugin execution order
----------------------

In many situations, such as result generation, not one, but all of the enabled
plugin types will be executed.  The order in which the plugins are executed
follows the lexical order of the entry point name.

For example, for the JSON result plugin, whose fully qualified name is
``result.json``, has an entry point name of ``json``.

So, plugins of the same type, a plugin named ``automated`` will be executed
before the plugin named ``uploader``.

In the default Avocado set of result plugins, it means that the JSON plugin
(``json``) will be executed before the XUnit plugin (``xunit``).  If the HTML
result plugin is installed and enabled (``html``) it will be executed before
both JSON and XUnit.

Changing the plugin execution order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On some circumstances it may be necessary to change the order in which plugins
are executed.  To do so, add a ``order`` entry a configuration file section
named after the plugin type.  For ``job.prepost`` plugin types, the section
name has to be named ``plugins.job.prepost``, and it would look like this::

  [plugins.job.prepost]
  order = ['myplugin', 'jobscripts']

That configuration sets the ``job.prepost.myplugin`` plugin to execute before
the standard Avocado ``job.prepost.jobscripts`` does.

.. note:: If you are interested on how plugins works and how to create your own
  plugin, visit the Plugin section on Contributor's Guide.

Pre and post plugins
--------------------

Avocado provides interfaces (hooks) with which custom plugins can register to
be called at various times.  For instance, it's possible to trigger custom
actions before and after the execution of a job, or before and after the
execution of the tests from a job.

Let's discuss each interface briefly.

Before and after jobs
~~~~~~~~~~~~~~~~~~~~~

Avocado supports plug-ins which are (guaranteed to be) executed before the
first test and after all tests finished.

.. This is a developer information not useful for user;

.. The interfaces are :class:`avocado.core.plugin_interfaces.JobPre` and
.. :class:`avocado.core.plugin_interfaces.JobPost`, respectively.

The :meth:`pre <avocado.core.plugin_interfaces.JobPre.pre>` method of each
installed plugin of type ``job.prepost`` will be called by the ``run`` command,
that is, anytime an ``avocado run <valid_test_reference>`` command is executed.

.. note:: Conditions such as the :exc:`SystemExit` or
          :exc:`KeyboardInterrupt` execeptions being raised can
          interrupt the execution of those plugins.

Then, immediately after that, the job's :meth:`run
<avocado.core.job.Job.run>` method is called, which attempts to run
all job phases, from test suite creation to test execution.

Unless a :exc:`SystemExit` or :exc:`KeyboardInterrupt` is raised, or
yet another major external event (like a system condition that Avocado
can not control) it will attempt to run the :meth:`post
<avocado.core.plugin_interfaces.JobPre.post>` methods of all the
installed plugins of type ``job.prepost``.  This even includes job
executions where the :meth:`pre
<avocado.core.plugin_interfaces.JobPre.pre>` plugin executions were
interrupted.

Before and after tests
~~~~~~~~~~~~~~~~~~~~~~

If you followed the previous section, you noticed that the job's
:meth:`run <avocado.core.job.Job.run>` method was said to run all the
test phases.  Here's a sequence of the job phases:

1) :meth:`Creation of the test suite <avocado.core.job.Job.create_test_suite>`
2) :meth:`Pre tests hook <avocado.core.job.Job.pre_tests>`
3) :meth:`Tests execution <avocado.core.job.Job.run_tests>`
4) :meth:`Post tests hook <avocado.core.job.Job.post_tests>`

Plugin writers can have their own code called at Avocado during a job
by writing a that will be called at phase number 2 (``pre_tests``) by
writing a method according to the
:meth:`avocado.core.plugin_interfaces.JobPreTests` interface.
Accordingly, plugin writers can have their own called at phase number
4 (``post_tests``) by writing a method according to the
:meth:`avocado.core.plugin_interfaces.JobPostTests` interface.

Note that there's no guarantee that all of the first 3 job phases will
be executed, so a failure in phase 1 (``create_test_suite``), may
prevent the phase 2 (``pre_tests``) and/or 3 (``run_tests``) from from
being executed.

Now, no matter what happens in the *attempted execution* of job phases
1 through 3, job phase 4 (``post_tests``) will be *attempted to be
executed*.  To make it extra clear, as long as the Avocado test runner
is still in execution (that is, has not been terminated by a system
condition that it can not control), it will execute plugin's
``post_tests`` methods.

As a concrete example, a plugin' ``post_tests`` method would not be
executed after a ``SIGKILL`` is sent to the Avocado test runner on
phases 1 through 3, because the Avocado test runner would be promptly
interrupted.  But, a ``SIGTERM`` and ``KeyboardInterrupt`` sent to the
Avocado test runner under phases 1 though 3 would still cause the test
runner to run ``post_tests`` (phase 4).  Now, if during phase 4 a
``KeyboardInterrupt`` or ``SystemExit`` is received, the remaining
plugins' ``post_tests`` methods will **NOT** be executed.

Jobscripts plugin
~~~~~~~~~~~~~~~~~

Avocado ships with a plugin (installed by default) that allows running
scripts before and after the actual execution of Jobs.  A user can be
sure that, when a given "pre" script is run, no test in that job has
been run, and when the "post" scripts are run, all the tests in a
given job have already finished running.

Configuration
^^^^^^^^^^^^^

By default, the script directory location is::

  /etc/avocado/scripts/job

Inside that directory, that is a directory for pre-job scripts::

  /etc/avocado/scripts/job/pre.d

And for post-job scripts::

  /etc/avocado/scripts/job/post.d

All the configuration about the Pre/Post Job Scripts are placed under
the ``avocado.plugins.jobscripts`` config section.  To change the
location for the pre-job scripts, your configuration should look
something like this::

  [plugins.jobscripts]
  pre = /my/custom/directory/for/pre/job/scripts/

Accordingly, to change the location for the post-job scripts, your
configuration should look something like this::

  [plugins.jobscripts]
  post = /my/custom/directory/for/post/scripts/

A couple of other configuration options are available under the same
section:

* ``warn_non_existing_dir``: gives warnings if the configured (or
  default) directory set for either pre or post scripts do not exist
* ``warn_non_zero_status``: gives warnings if a given script (either
  pre or post) exits with non-zero status

Script Execution Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All scripts are run in separate process with some environment
variables set.  These can be used in your scripts in any way you wish:

* ``AVOCADO_JOB_UNIQUE_ID``: the unique `job-id`.
* ``AVOCADO_JOB_STATUS``: the current status of the job.
* ``AVOCADO_JOB_LOGDIR``: the filesystem location that holds the logs
  and various other files for a given job run.

Note: Even though these variables should all be set, it's a good
practice for scripts to check if they're set before using their
values.  This may prevent unintended actions such as writing to the
current working directory instead of to the ``AVOCADO_JOB_LOGDIR`` if
this is not set.

Finally, any failures in the Pre/Post scripts will not alter the
status of the corresponding jobs.

Tests' logs plugin
~~~~~~~~~~~~~~~~~~

It's natural that Avocado will be used in environments where access to
the integral job results won't be easily accessible.

For instance, on Continuous Integration (CI) services, one usually
gets access to the output produced on the console, while access to
other files produced (generally called artifacts) may or may not be
acessible.

For this reason, it may be helpful to simply output the logs for tests
that have "interesting" outcomes, which usually means that fail and
need to be investigated.

To show the content for test that are canceled, skipped and fail, you
can set on your configuration file::

  [job.output.testlogs]
  statuses = ["CANCEL", "SKIP", "FAIL"]

At the end of the job, a header will be printed for each test that
ended with any of the statuses given, followed by the raw content of
its reespective log file.
