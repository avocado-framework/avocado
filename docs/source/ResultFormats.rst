.. _output-plugins:

Result Formats
==============

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines.

.. note:: There are several optional result plugins, you can find them in
   :ref:`result-plugins`.

Results for human beings
------------------------

Avocado has two different result formats that are intended for human beings:

* Its default UI, which shows the live test execution results on a command
  line, text based, UI.
* The HTML report, which is generated after the test job finishes running.

Avocado command line UI
~~~~~~~~~~~~~~~~~~~~~~~

A regular run of Avocado will present the test results in a live fashion,
that is, the job and its test(s) results are constantly updated::

    $ avocado run sleeptest.py failtest.py synctest.py
    JOB ID    : 5ffe479262ea9025f2e4e84c4e92055b5c79bdc9
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/job.log
     (1/3) sleeptest.py:SleepTest.test: PASS (1.01 s)
     (2/3) failtest.py:FailTest.test: FAIL (0.00 s)
     (3/3) synctest.py:SyncTest.test: PASS (1.98 s)
    RESULTS    : PASS 1 | ERROR 1 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 3.27 s
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html

The most important thing is to remember that programs should never need to parse
human output to figure out what happened to a test job run.

Machine readable results
------------------------

Another type of results are those intended to be parsed by other
applications. Several standards exist in the test community, and Avocado can
in theory support pretty much every result standard out there.

Out of the box, Avocado supports a couple of machine readable results. They
are always generated and stored in the results directory in `results.$type`
files, but you can ask for a different location too.

xunit
~~~~~

The default machine readable output in Avocado is
`xunit <http://help.catchsoftware.com/display/ET/JUnit+Format>`__.

xunit is an XML format that contains test results in a structured form, and
are used by other test automation projects, such as `jenkins
<http://jenkins-ci.org/>`__. If you want to make Avocado to generate xunit
output in the standard output of the runner, simply use::

   $ avocado run sleeptest.py failtest.py synctest.py --xunit -
   <?xml version="1.0" encoding="UTF-8"?>
   <testsuite name="avocado" tests="3" errors="0" failures="1" skipped="0" time="3.5769162178" timestamp="2016-05-04 14:46:52.803365">
           <testcase classname="SleepTest" name="1-sleeptest.py:SleepTest.test" time="1.00204920769"/>
           <testcase classname="FailTest" name="2-failtest.py:FailTest.test" time="0.00120401382446">
                   <failure type="TestFail" message="This test is supposed to fail"><![CDATA[Traceback (most recent call last):
     File "/home/medic/Work/Projekty/avocado/avocado/avocado/core/test.py", line 490, in _run_avocado
       raise test_exception
   TestFail: This test is supposed to fail
   ]]></failure>
                   <system-out><![CDATA[14:46:53 ERROR| 
   14:46:53 ERROR| Reproduced traceback from: /home/medic/Work/Projekty/avocado/avocado/avocado/core/test.py:435
   14:46:53 ERROR| Traceback (most recent call last):
   14:46:53 ERROR|   File "/home/medic/Work/Projekty/avocado/avocado/examples/tests/failtest.py", line 17, in test
   14:46:53 ERROR|     self.fail('This test is supposed to fail')
   14:46:53 ERROR|   File "/home/medic/Work/Projekty/avocado/avocado/avocado/core/test.py", line 585, in fail
   14:46:53 ERROR|     raise exceptions.TestFail(message)
   14:46:53 ERROR| TestFail: This test is supposed to fail
   14:46:53 ERROR| 
   14:46:53 ERROR| FAIL 2-failtest.py:FailTest.test -> TestFail: This test is supposed to fail
   14:46:53 INFO | 
   ]]></system-out>
           </testcase>
           <testcase classname="SyncTest" name="3-synctest.py:SyncTest.test" time="2.57366299629"/>
   </testsuite>


.. note:: The dash `-` in the option `--xunit`, it means that the xunit result
          should go to the standard output.
.. note:: In case your tests produce very long outputs, you can limit the
          number of embedded characters by
          `--xunit-max-test-log-chars`. If the output in the log file is
          longer it only attaches up-to max-test-log-chars characters
          one half starting from the beginning of the content, the other
          half from the end of the content.

JSON
~~~~

`JSON <http://www.json.org/>`__ is a widely used data exchange format. The
JSON Avocado plugin outputs job information, similarly to the xunit output
plugin::

    $ avocado run sleeptest.py failtest.py synctest.py --json -
    {
        "cancel": 0,
        "debuglog": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/job.log",
        "errors": 0,
        "failures": 1,
        "job_id": "10715c4645d2d2b57889d7a4317fcd01451b600e",
        "pass": 2,
        "skip": 0,
        "tests": [
            {
                "end": 1470761623.176954,
                "fail_reason": "None",
                "logdir": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/1-sleeptest.py:SleepTest.test",
                "logfile": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/1-sleeptest.py:SleepTest.test/debug.log",
                "start": 1470761622.174918,
                "status": "PASS",
                "id": "1-sleeptest.py:SleepTest.test",
                "time": 1.0020360946655273,
                "whiteboard": ""
            },
            {
                "end": 1470761623.193472,
                "fail_reason": "This test is supposed to fail",
                "logdir": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/2-failtest.py:FailTest.test",
                "logfile": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/2-failtest.py:FailTest.test/debug.log",
                "start": 1470761623.192334,
                "status": "FAIL",
                "id": "2-failtest.py:FailTest.test",
                "time": 0.0011379718780517578,
                "whiteboard": ""
            },
            {
                "end": 1470761625.656061,
                "fail_reason": "None",
                "logdir": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/3-synctest.py:SyncTest.test",
                "logfile": "/home/cleber/avocado/job-results/job-2016-08-09T13.53-10715c4/test-results/3-synctest.py:SyncTest.test/debug.log",
                "start": 1470761623.208165,
                "status": "PASS",
                "id": "3-synctest.py:SyncTest.test",
                "time": 2.4478960037231445,
                "whiteboard": ""
            }
        ],
        "time": 3.4510700702667236,
        "total": 3
    }

.. note:: The dash `-` in the option `--json`, it means that the xunit result
          should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to accommodate
newer Avocado features. A reasonable effort will be made to not break
backwards compatibility with applications that parse the current form of its
JSON result.


TAP
~~~

Provides the basic `TAP <http://testanything.org/>`__ (Test Anything Protocol) results, currently in v12. Unlike most existing avocado machine readable outputs this one is streamlined (per test results)::

    $ avocado run sleeptest.py --tap -
    1..1
    # debug.log of sleeptest.py:SleepTest.test:
    #   12:04:38 DEBUG| PARAMS (key=sleep_length, path=*, default=1) => 1
    #   12:04:38 DEBUG| Sleeping for 1.00 seconds
    #   12:04:39 INFO | PASS 1-sleeptest.py:SleepTest.test
    #   12:04:39 INFO |
    ok 1 sleeptest.py:SleepTest.test


Silent result
~~~~~~~~~~~~~

This result disables all stdout logging (while keeping the error messages
being printed to stderr). One can then use the return code to learn about
the result::

    $ avocado --silent run failtest.py
    $ echo $?
    1

In practice, this would usually be used by scripts that will in turn run
Avocado and check its results::

    #!/bin/bash
    ...
    $ avocado --silent run /path/to/my/test.py
    if [ $? == 0 ]; then
       echo "great success!"
    elif
       ...

more details regarding exit codes in `Exit Codes`_ section.

Multiple results at once
------------------------

You can have multiple results formats at once, as long as only one of them
uses the standard output. For example, it is fine to use the xunit result on
stdout and the JSON result to output to a file::

   $ avocado run sleeptest.py synctest.py --xunit - --json /tmp/result.json
   <?xml version="1.0" encoding="UTF-8"?>
   <testsuite name="avocado" tests="2" errors="0" failures="0" skipped="0" time="3.64848303795" timestamp="2016-05-04 17:26:05.645665">
           <testcase classname="SleepTest" name="1-sleeptest.py:SleepTest.test" time="1.00270605087"/>
           <testcase classname="SyncTest" name="2-synctest.py:SyncTest.test" time="2.64577698708"/>
   </testsuite>

   $ cat /tmp/result.json
   {
        "debuglog": "/home/cleber/avocado/job-results/job-2016-08-09T13.55-1a94ad6/job.log",
        "errors": 0,
        ...
   }

But you won't be able to do the same without the --json flag passed to
the program::

   $ avocado run sleeptest.py synctest.py --xunit - --json -
   Options --json --xunit are trying to use stdout simultaneously
   Please set at least one of them to a file to avoid conflicts

That's basically the only rule, and a sane one, that you need to follow.

Exit Codes
----------

Avocado exit code tries to represent different things that can happen during
an execution. That means exit codes can be a combination of codes that were
ORed together as a single exit code. The final exit code can be de-bundled so
users can have a good idea on what happened to the job.

The single individual exit codes are:

* AVOCADO_ALL_OK (0)
* AVOCADO_TESTS_FAIL (1)
* AVOCADO_JOB_FAIL (2)
* AVOCADO_FAIL (4)
* AVOCADO_JOB_INTERRUPTED (8)

If a job finishes with exit code `9`, for example, it means we had at least
one test that failed and also we had at some point a job interruption, probably
due to the job timeout or a `CTRL+C`.

Implementing other result formats
---------------------------------

If you are looking to implement a new machine or human readable output
format, you can refer to :mod:`avocado.plugins.xunit` and use it as a
starting point.

If your result is something that is produced at once, based on the
complete job outcome, you should create a new class that inherits from
:class:`avocado.core.plugin_interfaces.Result`  and implements the
:meth:`avocado.core.plugin_interfaces.Result.render` method.

But, if your result implementation is something that outputs
information live before/during/after tests, then the
:class:`avocado.core.plugin_interfaces.ResultEvents` interface is to
one to look at.  It will require you to implement the methods that
will perform actions (write to a file/stream) for each of the defined
events on a Job and test execution.

You can take a look at :doc:`Plugins` for more information on how to
write a plugin that will activate and execute the new result format.
