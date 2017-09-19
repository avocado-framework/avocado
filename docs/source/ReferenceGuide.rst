.. _reference-guide:

===============
Reference Guide
===============

This guide presents information on the Avocado basic design and its internals.

Job, test and identifiers
=========================

.. _job-id:

Job ID
------

The Job ID is a random SHA1 string that uniquely identifies a given job.

The full form of the SHA1 string is used is most references to a job::

  $ avocado run sleeptest.py
  JOB ID     : 49ec339a6cca73397be21866453985f88713ac34
  ...

But a shorter version is also used at some places, such as in the job
results location::

  JOB LOG    : $HOME/avocado/job-results/job-2015-06-10T10.44-49ec339/job.log


Test References
---------------

A Test Reference is a string that can be resolved into
(interpreted as) one or more tests by the Avocado Test Resolver.
A given resolver plugin is free to interpret a test reference,
it is completely abstract to the other components of Avocado.

.. note:: Mapping the Test References to tests can be affected
   by command-line switches like `--external-runner`, which
   completelly changes the meaning of the given strings.


Test Name
---------

A test name is an arbitrarily long string that unambiguously
points to the source of a single test. In other words the Avocado
Test Resolver, as configured for a particular job, should return
one and only one test as the interpretation of this name.

This name can be as specific as necessary to make it unique.
Therefore it can contain an arbitrary number of variables,
prefixes, suffixes, tags, etc.  It all depends on user
preferences, what is supported by Avocado via its Test Resolvers and
the context of the job.

The output of the Test Resolver when resolving Test References
should always be a list of unambiguous Test Names (for that
particular job).

Notice that although the Test Name has to be unique, one test can
be run more than once inside a job.

By definition, a Test Name is a Test Reference, but the
reciprocal is not necessarily true, as the latter can represent
more than one test.

Examples of Test Names::

   '/bin/true'
   'passtest.py:Passtest.test'
   'file:///tmp/passtest.py:Passtest.test'
   'multiple_tests.py:MultipleTests.test_hello'
   'type_specific.io-github-autotest-qemu.systemtap_tracing.qemu.qemu_free'


Variant IDs
-----------

The varianter component creates different sets of variables
(known as "variants"), to allow tests to be run individually in
each of them.

A Variant ID is an arbitrary and abstract string created by the
varianter plugin to identify each variant. It should be unique per
variant inside a set. In other words, the varianter plugin generates
a set of variants, identified by unique IDs.

A simpler implementation of the varianter uses serial integers
as Variant IDs. A more sophisticated implementation could
generate Variant IDs with more semantic, potentially representing
their contents.


Test ID
--------

A test ID is a string that uniquely identifies a test in the
context of a job. When considering a single job, there are no two
tests with the same ID.

A test ID should encapsulate the Test Name and the Variant ID, to
allow direct identification of a test. In other words, by looking
at the test ID it should be possible to identify:

  - What's the test name
  - What's the variant used to run this test (if any)

Test IDs don't necessarily keep their uniqueness properties when
considered outside of a particular job, but two identical jobs
run in the exact same environment should generate a identical
sets of Test IDs.

Syntax::

   <unique-id>-<test-name>[+<variant-id>]

Example of Test IDs::

   '1-/bin/true'
   '2-passtest.py:Passtest.test+quiet-'
   '3-file:///tmp/passtest.py:Passtest.test'
   '4-multiple_tests.py:MultipleTests.test_hello+maximum_debug-df2f'
   '5-type_specific.io-github-autotest-qemu.systemtap_tracing.qemu.qemu_free'

.. _test-types:

Test Types
==========

Avocado at its simplest configuration can run three different types of tests
[#f1]_. You can mix and match those in a single job.

Instrumented
------------

These are tests written in Python or BASH with the Avocado helpers that use the Avocado test API.

To be more precise, the Python file must contain a class derived from :mod:`avocado.test.Test`.
This means that an executable written in Python is not always an instrumented test, but may work
as a simple test.

The instrumented tests allows the writer finer control over the process
including logging, test result status and other more sophisticated test APIs.

Test statuses ``PASS``, ``WARN``, ``START`` and ``SKIP`` are considered as
successful builds. The ``ABORT``, ``ERROR``, ``FAIL``, ``ALERT``, ``RUNNING``,
``NOSTATUS`` and ``INTERRUPTED`` are considered as failed ones.

Python unittest
---------------

The discovery of classical python unittest is also supported, although unlike
python unittest we still use static analysis to get individual tests so
dynamically created cases are not recognized. Also note that test result SKIP
is reported as CANCEL in Avocado as SKIP test meaning differs from our
definition. Apart from that there should be no surprises when running
unittests via Avocado.

Simple
------

Any executable in your box. The criteria for PASS/FAIL is the return code of the executable.
If it returns 0, the test PASSes, if it returns anything else, it FAILs.

Test Statuses
=============

Avocado sticks to the following definitions of test statuses:

 * ```PASS```: The test passed, which means all conditions being tested have passed.
 * ```FAIL```: The test failed, which means at least one condition being tested has
   failed. Ideally, it should mean a problem in the software being tested has been found.
 * ```ERROR```: An error happened during the test execution. This can happen, for example,
   if there's a bug in the test runner, in its libraries or if a resource breaks unexpectedly.
   Uncaught exceptions in the test code will also result in this status.
 * ```SKIP```: The test runner decided a requested test should not be run. This
   can happen, for example, due to missing requirements in the test environment
   or when there's a job timeout.

.. _libraries-apis:

Libraries and APIs
==================

The Avocado libraries and its APIs are a big part of what Avocado is.

But, to avoid having any issues you should understand what parts of the Avocado
libraries are intended for test writers and their respective API stability promises.

Test APIs
---------

At the most basic level there's the Test APIs which you should use when writing
tests in Python and planning to make use of any other utility library.

The Test APIs can be found in the :mod:`avocado` main module, and its most important
member is the :class:`avocado.Test` class. By conforming to the :class:`avocado.Test`
API, that is, by inheriting from it, you can use the full set of utility libraries.

The Test APIs are guaranteed to be stable across a single major version of Avocado.
That means that a test written for a given version of Avocado should not break on later
minor versions because of Test API changes.

Utility Libraries
-----------------

There are also a large number of utility libraries that can be found under the
:mod:`avocado.utils` namespace. These are very general in nature and can help you
speed up your test development.

The utility libraries may receive incompatible changes across minor versions, but
these will be done in a staged fashion. If a given change to an utility library
can cause test breakage, it will first be documented and/or deprecated, and only
on the next subsequent minor version it will actually be changed.

What this means is that upon updating to later minor versions of Avocado, you
should look at the Avocado Release Notes for changes that may impact your tests.

Core (Application) Libraries
----------------------------

Finally, everything under :mod:`avocado.core` is part of the application's
infrastructure and should not be used by tests.

Extensions and Plugins can use the core libraries, but API stability is not
guaranteed at any level.

Test Resolution
===============

When you use the Avocado runner, frequently you'll provide paths to files,
that will be inspected, and acted upon depending on their contents. The
diagram below shows how Avocado analyzes a file and decides what to do with
it:

.. figure:: diagram.png

It's important to note that the inspection mechanism is safe (that is, python
classes and files are not actually loaded and executed on discovery and
inspection stage). Due to the fact Avocado doesn't actually load the code
and classes, the introspection is simple and will *not* catch things like
buggy test modules, missing imports and miscellaneous bugs in the code you
want to list or run. We recommend only running tests from sources you trust,
use of static checking and reviews in your test development process.

Due to the simple test inspection mechanism, avocado will not recognize test
classes that inherit from a class derived from :class:`avocado.Test`. Please
refer to the :doc:`WritingTests` documentation on how to use the tags functionality
to mark derived classes as avocado test classes.

Results Specification
=====================

On a machine that executed tests, job results are available under
``[job-results]/job-[timestamp]-[short job ID]``, where ``logdir`` is the configured Avocado
logs directory (see the data dir plugin), and the directory name includes
a timestamp, such as ``job-2014-08-12T15.44-565e8de``. A typical
results directory structure can be seen below ::

    $HOME/avocado/job-results/job-2014-08-13T00.45-4a92bc0/
    ├── id
    ├── jobdata
    │   ├── args
    │   ├── cmdline
    │   ├── config
    │   ├── multiplex
    │   ├── pwd
    │   └── test_references
    ├── job.log
    ├── results.json
    ├── results.xml
    ├── sysinfo
    │   ├── post
    │   │   ├── brctl_show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df_-mP
    │   │   ├── dmesg_-c
    │   │   ├── dmidecode
    │   │   ├── fdisk_-l
    │   │   ├── gcc_--version
    │   │   ├── hostname
    │   │   ├── ifconfig_-a
    │   │   ├── interrupts
    │   │   ├── ip_link
    │   │   ├── ld_--version
    │   │   ├── lscpu
    │   │   ├── lspci_-vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mount
    │   │   ├── mounts
    │   │   ├── numactl_--hardware_show
    │   │   ├── partitions
    │   │   ├── scaling_governor
    │   │   ├── uname_-a
    │   │   ├── uptime
    │   │   └── version
    │   ├── pre
    │   │   ├── brctl_show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df_-mP
    │   │   ├── dmesg_-c
    │   │   ├── dmidecode
    │   │   ├── fdisk_-l
    │   │   ├── gcc_--version
    │   │   ├── hostname
    │   │   ├── ifconfig_-a
    │   │   ├── interrupts
    │   │   ├── ip_link
    │   │   ├── ld_--version
    │   │   ├── lscpu
    │   │   ├── lspci_-vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mount
    │   │   ├── mounts
    │   │   ├── numactl_--hardware_show
    │   │   ├── partitions
    │   │   ├── scaling_governor
    │   │   ├── uname_-a
    │   │   ├── uptime
    │   │   └── version
    │   └── profile
    └── test-results
        └── tests
            ├── sleeptest.py.1
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            ├── sleeptest.py.2
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            └── sleeptest.py.3
                ├── data
                ├── debug.log
                └── sysinfo
                    ├── post
                    └── pre
    
    22 directories, 65 files


From what you can see, the results dir has:

1) A human readable ``id`` in the top level, with the job SHA1.
2) A human readable ``job.log`` in the top level, with human readable logs of
   the task
3) Subdirectory ``jobdata``, that contains machine readable data about the job.
4) A machine readable ``results.xml`` and ``results.json`` in the top level,
   with a summary of the job information in xUnit/json format.
5) A top level ``sysinfo`` dir, with sub directories ``pre``, ``post`` and
   ``profile``, that store sysinfo files pre/post/during job, respectively.
6) Subdirectory ``test-results``, that contains a number of subdirectories
   (filesystem-friendly test ids). Those test ids represent instances of test
   execution results.

Test execution instances specification
--------------------------------------

The instances should have:

1) A top level human readable ``job.log``, with job debug information
2) A ``sysinfo`` subdir, with sub directories ``pre``, ``post`` and
   ``profile`` that store sysinfo files pre test, post test and
   profiling info while the test was running, respectively.
3) A ``data`` subdir, where the test can output a number of files if necessary.


Test execution environment
--------------------------

Each test is executed in a separate process.  Due to how the
underlying operating system works, a lot of the attributes of the
parent process (the Avocado test **runner**) are passed down to the
test process.

On GNU/Linux systems, a child process should be *"an exact duplicate
of the parent process, except"* some items that are documented in
the ``fork(2)`` man page.

Besides those operating system exceptions, the Avocado test runner
changes the test process in the following ways:

1) The standard input (``STDIN``) is set to a :data:`null device
   <os.devnull>`.  This is truth both for :data:`sys.stdin` and for
   file descriptor ``0``.  Both will point to the same open null
   device file.

2) The standard output (``STDOUT``), as in :data:`sys.stdout`, is
   redirected so that it doesn't interfere with the test runner's own
   output.  All content written to the test's :data:`sys.stdout` will
   be available in the logs under the ``output`` prefix.

   .. warning:: The file descriptor ``1`` (AKA ``/dev/stdout``, AKA
                ``/proc/self/fd/1``, etc) is **not** currently
                redirected for INSTRUMENTED tests.  Any attempt to
                write directly to the file descriptor will interfere
                with the runner's own output stream.  This behavior
                will be addressed in a future version.

3) The standard error (``STDERR``), as in :data:`sys.stderr`, is
   redirected so that it doesn't interfere with the test runner's own
   errors.  All content written to the test's :data:`sys.stderr` will
   be available in the logs under the ``output`` prefix.

   .. warning:: The file descriptor ``2`` (AKA ``/dev/stderr``, AKA
                ``/proc/self/fd/2``, etc) is **not** currently
                redirected for INSTRUMENTED tests.  Any attempt to
                write directly to the file descriptor will interfere
                with the runner's own error stream.  This behavior
                will be addressed in a future version.

4) A custom handler for signal ``SIGTERM`` which will simply raise an
   exception (with the appropriate message) to be handled by the
   Avocado test runner, stating the fact that the test was interrupted
   by such a signal.

   .. tip:: By following the backtrace that is given alongside the in
            the test log (look for ``RuntimeError: Test interrupted
            by SIGTERM``) a user can quickly grasp at which point the
            test was interrupted.

   .. note:: If the test handles ``SIGTERM`` differently and doesn't
             finish the test process quickly enough, it will receive
             then a ``SIGKILL`` which is supposed to definitely end
             the test process.

5) A number of :ref:`environment variables
   <environment-variables-for-tests>` that are set by Avocado, all
   prefixed with ``AVOCADO_``.

If you want to see for yourself what is described here, you may want
to run the example test ``test_env.py`` and examine its log messages.

Pre and post plugins
====================

Avocado provides interfaces with which custom plugins can register to
be called at various times.  For instance, it's possible to trigger
custom actions before and after the execution of a :class:`job
<avocado.core.job.Job>`, or before and after the execution of the
tests from a job :data:`test suite <avocado.core.job.Job.test_suite>`.

Let's discuss each interface briefly.

Before and after jobs
---------------------

Avocado supports plug-ins which are (guaranteed to be) executed before the
first test and after all tests finished. The interfaces are
:class:`avocado.core.plugin_interfaces.JobPre` and
:class:`avocado.core.plugin_interfaces.JobPost`, respectively.

The :meth:`pre <avocado.core.plugin_interfaces.JobPre.pre>` method of
each installed plugin of type ``job.prepost`` will be called by the
``run`` command, that is, anytime an ``avocado run
<valid_test_reference>`` command is executed.

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

Before and after the execution of tests
---------------------------------------

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
-----------------

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

* ``AVOCADO_JOB_UNIQUE_ID``: the unique `job-id`_.
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

Job Cleanup
===========

It's possible to register a callback function that will be called when
all the tests have finished running. This effectively allows for a
test job to clean some state it may have left behind.

At the moment, this feature is not intended to be used by test writers,
but it's seen as a feature for Avocado extensions to make use.

To register a callback function, your code should put a message in a
very specific format in the "runner queue". The Avocado test runner
code will understand that this message contains a (serialized) function
that will be called once all tests finish running.

Example::

  from avocado import Test

  def my_cleanup(path_to_file):
     if os.path.exists(path_to_file):
        os.unlink(path_to_file)

  class MyCustomTest(Test):
  ...
     cleanup_file = '/tmp/my-custom-state'
     self.runner_queue.put({"func_at_exit": self.my_cleanup,
                            "args": (cleanup_file),
                            "once": True})
  ...

This results in the ``my_cleanup`` function being called with
positional argument ``cleanup_file``.

Because ``once`` was set to ``True``, only one unique combination of
function, positional arguments and keyword arguments will be
registered, not matter how many times they're attempted to be
registered. For more information check
:meth:`avocado.utils.data_structures.CallbackRegister.register`.

.. _docstring-directive-rules:

Docstring Directives Rules
==========================

Avocado INSTRUMENTED tests, those written in Python and using the
:class:`avocado.Test` API, can make use of special directives
specified as docstrings.

To be considered valid, the docstring must match this pattern:
:data:`avocado.core.safeloader.DOCSTRING_DIRECTIVE_RE_RAW`.

An Avocado docstring directive has two parts:

 1) The marker, which is the literal string ``:avocado:``.

 2) The content, a string that follows the marker, separated by at
    least one white space or tab.

The following is a list of rules that makes a docstring directive
be a valid one:

 * It should start with ``:avocado:``, which is the docstring
   directive "marker"

 * At least one whitespace or tab must follow the marker and preceed
   the docstring directive "content"

 * The "content", which follows the marker and the space, must begin
   with an alphanumeric character, that is, characters within "a-z",
   "A-Z" or "0-9".

 * After at least one alphanumeric character, the content may contain
   the following special symbols too: ``_``, ``,``, ``=`` and ``:``.

 * An end of string (or end of line) must immediately follow the
   content.

.. _signal_handlers:

Signal Handlers
===============

Avocado normal operation is related to run code written by
users/test-writers. It means the test code can carry its own handlers
for different signals or even ignore then. Still, as the code is being
executed by Avocado, we have to make sure we will finish all the
subprocesses we create before ending our execution.

Signals sent to the Avocado main process will be handled as follows:

- SIGSTP/Ctrl+Z: On SIGSTP, Avocado will pause the execution of the
  subprocesses, while the main process will still be running,
  respecting the timeout timer and waiting for the subprocesses to
  finish. A new SIGSTP will make the subprocesses to resume the
  execution.
- SIGINT/Ctrl+C: This signal will be forwarded to the test process and
  Avocado will wait until it's finished. If the test process does not
  finish after receiving a SIGINT, user can send a second SIGINT (after
  the 2 seconds ignore period). The second SIGINT will make Avocado
  to send a SIGKILL to the whole subprocess tree and then complete the
  main process execution.
- SIGTERM: This signal will make Avocado to terminate immediately. A
  SIGKILL will be sent to the whole subprocess tree and the main process
  will exit without completing the execution. Notice that it's a
  best-effort attempt, meaning that in case of fork-bomb, newly created
  processes might still be left behind.

.. [#f1] Avocado plugins can introduce additional test types.
