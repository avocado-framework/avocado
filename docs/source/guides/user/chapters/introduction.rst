Introduction
============

Avocado Hello World
-------------------

You should first experience Avocado by using the test runner, that is, the
command line tool that will conveniently run your tests and collect their
results.

To do so, please run ``avocado`` with the ``run`` sub-command followed by a
test reference, which could be either a path to the file, or a recognizable
name::

    $ avocado run /bin/true
    JOB ID     : 3a5c4c51ceb5369f23702efb10b4209b111141b2
    JOB LOG    : $HOME/avocado/job-results/job-2019-10-31T10.34-3a5c4c5/job.log
     (1/1) /bin/true: PASS (0.04 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.15 s

You probably noticed that we used ``/bin/true`` as a test, and in accordance
with our expectations, it passed! These are known as `simple tests`, but there
is also another type of test, which we call `instrumented tests`. See more at
`test-types` or just keep reading.


Running a job with multiple tests
---------------------------------

You can run any number of test in an arbitrary order, as well as mix and match
instrumented and simple tests::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py examples/tests/synctest.py /tmp/simple_test.sh 
    JOB ID     : 2391dddf53b950631589bd1d44a5a6fdd023b400
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.35-2391ddd/job.log
     (1/4) examples/tests/sleeptest.py:SleepTest.test: STARTED
     (2/4) examples/tests/failtest.py:FailTest.test: STARTED
     (3/4) examples/tests/synctest.py:SyncTest.test: STARTED
     (4/4) /tmp/simple_test.sh: STARTED
     (4/4) /tmp/simple_test.sh: PASS (0.01 s)
     (2/4) examples/tests/failtest.py:FailTest.test: FAIL: This test is supposed to fail (0.05 s)
     (1/4) examples/tests/sleeptest.py:SleepTest.test: PASS (1.02 s)
     (3/4) examples/tests/synctest.py:SyncTest.test: PASS (1.39 s)
    RESULTS    : PASS 3 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 3.25 s

.. note:: Although in most cases running ``avocado run $test1 $test3 ...`` is
          fine, it can lead to argument vs. test name clashes. The safest
          way to execute tests is ``avocado run --$argument1 --$argument2
          -- $test1 $test2``. Everything after ``--`` will be considered
          positional arguments, therefore test names (in case of
          ``avocado run``)


Using a different runner
------------------------

Currently Avocado has two test runners: ``nrunner`` (the new runner) and
``runner`` (legacy).  You can find a list of current runners installed with the
``avocado plugins`` command::

  $ avocado plugins
  Plugins that run test suites on a job (runners):
  nrunner nrunner based implementation of job compliant runner
  runner  The conventional test runner

During the test execution, you can select the runner using the option
``--test-runner``, where the default is the nrunner one::

  $ avocado run --test-runner='runner' /bin/true


Interrupting tests
------------------

.. _signal_hanlders:

Sending Signals
~~~~~~~~~~~~~~~

To interrupt a job execution a user can press ``ctrl+c`` which after a single
press sends ``SIGTERM`` to the main test's process and waits for it to finish.  If
this does not help user can press ``ctrl+c`` again (after 2s grace period)
which destroys the test's process ungracefully and safely finishes the job
execution always providing the test results.

To pause the test execution a user can use ``ctrl+z`` which sends ``SIGSTOP``
to all processes inherited from the test's PID. We do our best to stop all
processes, but the operation is not atomic and some new processes might not be
stopped. Another ``ctrl+z`` sends ``SIGCONT`` to all processes inherited by the
test's PID resuming the execution. Note the test execution time (concerning the
test timeout) are still running while the test's process is stopped.

Interrupting the job on first fail (failfast)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado ``run`` command has the option ``--failfast`` to exit the job as
soon as possible.

Due to our current runner architecture, tests are executed in parallel by
default.  The ``--failfast`` option work on the best effort to cancel tests
that have not started yet. To replicate the same behavior as the legacy runner,
use ``--max-parallel-tasks=1`` to limit the number of tasks executed in
parallel::

    $ avocado run --failfast --max-parallel-tasks=1 /bin/true /bin/false /bin/true /bin/true
    JOB ID     : 76bfe0e5cfa5efac3ab6881ee501cc5d4b69f913
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.41-76bfe0e/job.log
     (1/4) /bin/true: STARTED
     (1/4) /bin/true: PASS (0.01 s)
     (2/4) /bin/false: STARTED
     (2/4) /bin/false: FAIL (0.01 s)
    Interrupting job (failfast).
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 2 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.57 s

The default behavior, that is, when ``--failfast`` is **not** set, is
to try to execute all tests in a job, regardless individual of test failures.

.. note:: Avocado versions 80.0 and earlier allowed replayed jobs to override
          the failfast configuration by setting ``--failfast=off`` in a
          ``avocado replay ..`` command line.  This is no longer possible.

.. _the_hint_files:

The hint files
--------------

Avocado team has added support to the "hint files". This feature is present
since Avocado #78 and is a configuration file that you can add to your project
root folder to help Avocado on the "test resolution" phase.

The idea is that, you know more about your tests than anybody else. And you can
specify where your tests are, and what type (kind) they are. You just have to
add a ``.avocado.hint`` in your root folder with the section ``[kinds]`` and one
section for each kind that you are using.

On the specific test type section, you can specify 3 options: ``uri``, ``args`` and
``kwargs``.

.. note:: Some test types will convert ``kwargs`` into variable environments.
 Please check the documentation of the test type that you are using.

You can also use the keyword ``$testpath`` in any of the options inside the test
type section. Avocado will replace ``$testpath`` with your test path, after the
expansion.

For instance, below you will find a hint file example where we have only one
test type ``TAP``:

.. literalinclude:: ../../../../../examples/hint-files/.avocado.hint.example

Let's suppose that you have 2 tests that matches ``./tests/unit/*.sh``:

* ``./tests/unit/foo.sh``
* ``./tests/unit/bar.sh``

Avocado will run each one as a ``TAP`` test, as you desired.

.. note:: Please, keep in mind that hint files needs absolute paths when
   defining tests inside the ``[kinds]`` section.

Since Avocado's next runner is capable of running tests not only in a
subprocess but also in more isolated environments such as Podman containers,
sending custom environment variables to the task executor can be achieved by
using the ``kwargs`` parameter. Use a comma-separated list of variables here
and Avocado will make sure your tests will receive those variables (regardless
of the spawner type).

Ignoring missing test references
--------------------------------

When you provide a list of test references, Avocado will try to resolve all of
them to tests. If one or more test references can not be resolved to tests, the
Job will not be created. Example::

    $ avocado run examples/tests/passtest.py badtest.py
    Unable to resolve reference(s) 'badtest.py' with plugins(s) 'file', 'robot', try running 'avocado -V list badtest.py' to see the details.

But if you want to execute the Job anyway, with the tests that could be
resolved, you can use ``--ignore-missing-references``, a boolean command-line
option. The same message will appear in the UI, but the Job will be executed::

    $ avocado run examples/tests/passtest.py badtest.py --ignore-missing-references
    JOB ID     : e6d1f4d21d6a5e2e039f1acd1670a6882144c189
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.50-e6d1f4d/job.log
     (1/1) examples/tests/passtest.py:PassTest.test: STARTED
     (1/1) examples/tests/passtest.py:PassTest.test: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.49 s

Runner outputs
--------------

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines.

.. note:: There are several optional result plugins, you can find them in
   :ref:`result-plugins`.

Results for human beings
~~~~~~~~~~~~~~~~~~~~~~~~

Avocado has two different result formats that are intended for human beings:

* Its default UI, which shows the live test execution results on a command
  line, text based, UI.
* The HTML report, which is generated after the test job finishes running.

.. note:: The HTML report needs the ``html`` plugin enabled that is an optional
  plugin.

A regular run of Avocado will present the test results in a live fashion, that
is, the job and its test(s) results are constantly updated::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py examples/tests/synctest.py
    JOB ID     : 2e83086e5d3f82dd68bdc8885e7cce1cebec5f27
    JOB LOG    : $HOME/wrampazz/avocado/job-results/job-2021-09-27T17.00-2e83086/job.log
     (3/3) examples/tests/synctest.py:SyncTest.test: STARTED
     (1/3) examples/tests/sleeptest.py:SleepTest.test: STARTED
     (2/3) examples/tests/failtest.py:FailTest.test: STARTED
     (2/3) examples/tests/failtest.py:FailTest.test: FAIL: This test is supposed to fail (0.02 s)
     (1/3) examples/tests/sleeptest.py:SleepTest.test: PASS (1.01 s)
     (3/3) examples/tests/synctest.py:SyncTest.test: PASS (1.24 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-09-27T17.00-2e83086/results.html
    JOB TIME   : 2.80 s

The most important thing is to remember that programs should never need to
parse human output to figure out what happened to a test job run.

As you can see, Avocado will print a nice UI with the job summary on the
console. If you would like to inspect a detailed output of your tests, you can
visit the folder: ``$HOME/avocado/job-results/latest/`` or a specific job
folder.

Results for machine
~~~~~~~~~~~~~~~~~~~

Another type of results are those intended to be parsed by other applications.
Several standards exist in the test community, and Avocado can in theory
support pretty much every result standard out there.

Out of the box, Avocado supports a couple of machine readable results. They are
always generated and stored in the results directory in ``results.$type`` files,
but you can ask for a different location too.

Currently, you can find three different formats available on this folder:
**xUnit (XML)**, **JSON** and **TAP**.

 **1. xUnit:**

The default machine readable output in Avocado is `xunit
<http://help.catchsoftware.com/display/ET/JUnit+Format>`__.

xUnit is an XML format that contains test results in a structured form, and are
used by other test automation projects, such as `jenkins
<http://jenkins-ci.org/>`__ or `GitLabCI <https://docs.gitlab.com/ee/ci/>`__.
If you want to make Avocado to generate xunit output in the standard output of
the runner, simply use::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py examples/tests/synctest.py --xunit -
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="job-2021-09-27T17.01-2dd7837" tests="3" errors="0" failures="1" skipped="0" time="2.340" timestamp="2021-09-27T17:01:36.455763">
    	<testcase classname="&lt;unknown&gt;" name="2-examples/tests/failtest.py:FailTest.test" time="0.026">
    		<failure type="&lt;unknown&gt;" message="This test is supposed to fail"><![CDATA[<unknown>]]></failure>
    		<system-out><![CDATA[[stdlog] 2021-09-27 17:01:34,722 test             L0312 INFO | INIT 1-FailTest.test
    [stdlog] 2021-09-27 17:01:34,723 parameters       L0142 DEBUG| PARAMS (key=timeout, path=*, default=None) => None
    [stdlog] 2021-09-27 17:01:34,723 test             L0340 DEBUG| Test metadata:
    [stdlog] 2021-09-27 17:01:34,723 test             L0342 DEBUG|   filename: $HOME/src/avocado/avocado.dev/examples/tests/failtest.py
    [stdlog] 2021-09-27 17:01:34,723 test             L0348 DEBUG|   teststmpdir: /var/tmp/avocado_vi1xpequ
    [stdlog] 2021-09-27 17:01:34,723 test             L0538 INFO | START 1-FailTest.test
    [stdlog] 2021-09-27 17:01:34,724 test             L0207 DEBUG| DATA (filename=output.expected) => NOT FOUND (data sources: variant, test, file)
    [stdlog] 2021-09-27 17:01:34,724 stacktrace       L0039 ERROR|
    [stdlog] 2021-09-27 17:01:34,724 stacktrace       L0041 ERROR| Reproduced traceback from: $HOME/src/avocado/avocado.dev/avocado/core/test.py:794
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR| Traceback (most recent call last):
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR|   File "$HOME/src/avocado/avocado.dev/examples/tests/failtest.py", line 16, in test
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR|     self.fail('This test is supposed to fail')
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR|   File "$HOME/src/avocado/avocado.dev/avocado/core/test.py", line 980, in fail
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR|     raise exceptions.TestFail(message)
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0045 ERROR| avocado.core.exceptions.TestFail: This test is supposed to fail
    [stdlog] 2021-09-27 17:01:34,725 stacktrace       L0046 ERROR|
    [stdlog] 2021-09-27 17:01:34,725 test             L0799 DEBUG| Local variables:
    [stdlog] 2021-09-27 17:01:34,740 test             L0802 DEBUG|  -> self <class 'failtest.FailTest'>: 1-FailTest.test
    [stdlog] 2021-09-27 17:01:34,741 test             L0207 DEBUG| DATA (filename=output.expected) => NOT FOUND (data sources: variant, test, file)
    [stdlog] 2021-09-27 17:01:34,741 test             L0207 DEBUG| DATA (filename=stdout.expected) => NOT FOUND (data sources: variant, test, file)
    [stdlog] 2021-09-27 17:01:34,741 test             L0207 DEBUG| DATA (filename=stderr.expected) => NOT FOUND (data sources: variant, test, file)
    [stdlog] 2021-09-27 17:01:34,741 test             L0957 ERROR| FAIL 1-FailTest.test -> TestFail: This test is supposed to fail
    [stdlog] 2021-09-27 17:01:34,741 test             L0949 INFO |
    ]]></system-out>
    	</testcase>
    	<testcase classname="&lt;unknown&gt;" name="1-examples/tests/sleeptest.py:SleepTest.test" time="1.010"/>
    	<testcase classname="&lt;unknown&gt;" name="3-examples/tests/synctest.py:SyncTest.test" time="1.304"/>
    </testsuite>


.. note:: The dash ``-`` in the option ``--xunit``, it means that the xunit result
          should go to the standard output.

.. note:: In case your tests produce very long outputs, you can limit the
          number of embedded characters by
          ``--xunit-max-test-log-chars``. If the output in the log file is
          longer it only attaches up-to max-test-log-chars characters
          one half starting from the beginning of the content, the other
          half from the end of the content.

.. note:: The avocado xunit format adds some attributes which are not a part of 
          the official format, but they are used by `GitLabCI <https://gitlab.com/gitlab-org/gitlab/-/blob/7826c42924e3ced8ae625fda1ddd4e120492d596/lib/gitlab/ci/parsers/test/junit.rb#L83>`__.


**2. JSON:**

`JSON <https://www.json.org/>`__ is a widely used data exchange format. The JSON
Avocado plugin outputs job information, similarly to the xunit output plugin::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py examples/tests/synctest.py --json -
    {
        "cancel": 0,
        "debuglog": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/job.log",
        "errors": 0,
        "failures": 1,
        "interrupt": 0,
        "job_id": "fd073c26a1e1aacee59bc9e1914b7110e7ac3f8b",
        "pass": 2,
        "skip": 0,
        "tests": [
            {
                "end": 30759.486869323,
                "fail_reason": "This test is supposed to fail",
                "id": "2-examples/tests/failtest.py:FailTest.test",
                "logdir": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/2-examples_tests_failtest.py_FailTest.test",
                "logfile": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/2-examples_tests_failtest.py_FailTest.test/debug.log",
                "start": 30759.456017671,
                "status": "FAIL",
                "tags": {},
                "time": 0.030851651998091256,
                "whiteboard": ""
            },
            {
                "end": 30760.472274292,
                "fail_reason": "<unknown>",
                "id": "1-examples/tests/sleeptest.py:SleepTest.test",
                "logdir": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/1-examples_tests_sleeptest.py_SleepTest.test",
                "logfile": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/1-examples_tests_sleeptest.py_SleepTest.test/debug.log",
                "start": 30759.455787493,
                "status": "PASS",
                "tags": {},
                "time": 1.0164867989988124,
                "whiteboard": ""
            },
            {
                "end": 30760.690585313,
                "fail_reason": "<unknown>",
                "id": "3-examples/tests/synctest.py:SyncTest.test",
                "logdir": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/3-examples_tests_synctest.py_SyncTest.test",
                "logfile": "$HOME/avocado/job-results/job-2021-09-27T17.05-fd073c2/test-results/3-examples_tests_synctest.py_SyncTest.test/debug.log",
                "start": 30759.459244923,
                "status": "PASS",
                "tags": {},
                "time": 1.231340390000696,
                "whiteboard": ""
            }
        ],
        "time": 2.2786788409975998,
        "total": 3,
        "warn": 0
    }

.. note:: The dash ``-`` in the option ``--json``, it means that the xunit result
          should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to accommodate newer
Avocado features. A reasonable effort will be made to not break backwards
compatibility with applications that parse the current form of its JSON result.


 **3. TAP:**

Provides the basic `TAP <https://testanything.org/>`__ (Test Anything Protocol)
results, currently in v12. Unlike most existing Avocado machine readable
outputs this one is streamlined (per test results)::

    $ avocado run examples/tests/sleeptest.py --tap -
    1..1
    ok 1 examples/tests/sleeptest.py:SleepTest.test


 **4. Beaker:**

When avocaodo finds itself running inside a beaker task the
beaker_report plugin will send the test results and log files to the
beaker lab controller.  Happens automatically, no configuration
required.  Check the `project website <https://beaker-project.org/>`__
for more information on beaker.


Using the option --show
~~~~~~~~~~~~~~~~~~~~~~~

Probably, you frequently want to look straight at the job log, without
switching screens or having to "tail" the job log.

In order to do that, you can use ``avocado --show=test run ...``::

    $ avocado --show=test run examples/tests/sleeptest.py
    ...
    Job ID: f9ea1742134e5352dec82335af584d1f151d4b85

    START 1-sleeptest.py:SleepTest.test

    PARAMS (key=timeout, path=*, default=None) => None
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    PASS 1-sleeptest.py:SleepTest.test

    Test results available in $HOME/avocado/job-results/job-2015-06-02T10.45-f9ea174

As you can see, the UI output is suppressed and only the job log is shown,
making this a useful feature for test development and debugging.

It's possible to silence all output to stdout (while keeping the error messages
being printed to stderr). One can then use the return code to learn about the
result::

    $ avocado --show=none run examples/tests/failtest.py
    $ echo $?
    1

In practice, this would usually be used by scripts that will in turn run
Avocado and check its results::

    #!/bin/bash
    ...
    $ avocado --show=none run /path/to/my/test.py
    if [ $? == 0 ]; then
       echo "great success!"
    elif
       ...

more details regarding exit codes in `Exit Codes` section.

Multiple results at once
~~~~~~~~~~~~~~~~~~~~~~~~

You can have multiple results formats at once, as long as only one of them uses
the standard output. For example, it is fine to use the xunit result on stdout
and the JSON result to output to a file::

    $ avocado run examples/tests/sleeptest.py examples/tests/synctest.py --xunit - --json /tmp/result.json
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="job-2021-09-27T17.10-b37e5fe" tests="2" errors="0" failures="0" skipped="0" time="2.220" timestamp="2021-09-27T17:10:28.757207">
    	<testcase classname="&lt;unknown&gt;" name="1-examples/tests/sleeptest.py:SleepTest.test" time="1.011"/>
    	<testcase classname="&lt;unknown&gt;" name="2-examples/tests/synctest.py:SyncTest.test" time="1.209"/>
    </testsuite>

    $ cat /tmp/result.json
    {
        "cancel": 0,
        "debuglog": "$HOME/avocado/job-results/job-2021-09-27T17.10-b37e5fe/job.log",
        "errors": 0,
        "failures": 0,
        "interrupt": 0,
        "job_id": "b37e5fee226e3806c4d73fef180d7d2cee56464e",
        "pass": 2,
        "skip": 0,
    }

But you won't be able to do the same without the ``--json`` flag passed to
the program::

    avocado run examples/tests/sleeptest.py examples/tests/synctest.py --xunit - --json  -
    avocado run: error: argument --json: Options --xunit --json are trying to
    use stdout simultaneously. Please set at least one of them to a file to
    avoid conflicts

That's basically the only rule, and a sane one, that you need to follow.

.. note:: Avocado support "paginator" option, which, on compatible
  terminals, basically pipes the colored output to ``less`` to simplify
  browsing of the produced output. You an enable it with ``--enable-paginator``.

Sysinfo collection
------------------

.. note:: This feature is not fully supported on nrunner runner yet.

Avocado comes with a ``sysinfo`` plugin, which automatically gathers some
system information per each job or even between tests. This is very useful
when later we want to know what caused the test's failure. This system
is configurable but we provide a sane set of defaults for you.

In the default Avocado configuration (``/etc/avocado/avocado.conf``) there
is a section ``sysinfo.collect`` where you can enable/disable the sysinfo
collection as well as configure the basic environment. In
``sysinfo.collectibles`` section you can define basic paths of where
to look for what commands/tasks should be performed before/during
the sysinfo collection. Avocado supports three types of tasks:

1. commands - file with new-line separated list of commands to be executed
   before and after the job/test (single execution commands). It is possible
   to set a timeout which is enforced per each executed command in
   ``[sysinfo.collect]`` by setting "commands_timeout" to a positive number.
   You can also use the environment variable ``AVOCADO_SYSINFODIR`` which points
   to the sysinfo directory in results.
2. fail_commands - similar to commands, but gets executed only when the test
   fails.
3. files - file with new-line separated list of files to be copied.
4. fail_files - similar to files, but copied only when the test fails.
5. profilers - file with new-line separated list of commands to be executed
   before the job/test and killed at the end of the job/test (follow-like
   commands).

Additionally this plugin tries to follow the system log via ``journalctl``
if available.

By default these are collected per-job but you can also run them per-test by
setting ``per_test = True`` in the ``sysinfo.collect`` section.

The sysinfo is enabled by default and can also be disabled on the cmdline if
needed by ``--disable-sysinfo``.

After the job execution you can find the collected information in
``$RESULTS/sysinfo`` of ``$RESULTS/test-results/$TEST/sysinfo``. They
are categorized into ``pre``, ``post`` and ``profile`` folders and
the filenames are safely-escaped executed commands or file-names.
You can also see the sysinfo in html results when you have html
results plugin enabled.

It is also possible to save only the files / commands which were changed
during the course of the test, in the ``post`` directory, using the setting
``optimize = True`` in the ``sysinfo.collect`` section. This collects all
sysinfo on ``pre``, but saves only changed ones on ``post``. It is set to
False by default.

.. warning:: If you are using Avocado from sources, you need to manually place
   the ``commands``/``fail_commands``/``fail_files``/``files``/``profilers``
   into the ``/etc/avocado/sysinfo`` directories or adjust the paths in
   ``$AVOCADO_SRC/etc/avocado/avocado.conf``.
