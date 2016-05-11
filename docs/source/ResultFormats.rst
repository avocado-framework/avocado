.. _output-plugins:

Result Formats
==============

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines.

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
    TESTS     : 3
     (1/3) sleeptest.py:SleepTest.test: PASS (1.01 s)
     (2/3) failtest.py:FailTest.test: FAIL (0.00 s)
     (3/3) synctest.py:SyncTest.test: PASS (1.98 s)
    RESULTS    : PASS 1 | ERROR 1 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html
    TESTS TIME : 3.17 s

The most important thing is to remember that programs should never need to parse
human output to figure out what happened to a test job run.

HTML report
~~~~~~~~~~~

As can be seen in the previous example, Avocado shows the path to an HTML
report that will be generated as soon as the job finishes running::

    $ avocado run sleeptest.py failtest.py synctest.py
    ...
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html
    ...

You can also request that the report be opened automatically by using the
``--open-browser`` option. For example::

    $ avocado run sleeptest --open-browser

Will show you the nice looking HTML results report right after ``sleeptest``
finishes running.

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

json
~~~~

`JSON <http://www.json.org/>`__ is a widely used data exchange format. The
json Avocado plugin outputs job information, similarly to the xunit output
plugin::

    $ avocado run sleeptest.py failtest.py synctest.py --json -
    {"tests": [{"status": "PASS", "url": "1-sleeptest.py:SleepTest.test", "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/1-sleeptest.py:SleepTest.test/debug.log", "whiteboard": "", "end": 1462366291.95844, "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/1-sleeptest.py:SleepTest.test", "start": 1462366290.957374, "test": "1-sleeptest.py:SleepTest.test", "fail_reason": "None", "time": 1.001065969467163}, {"status": "FAIL", "url": "2-failtest.py:FailTest.test", "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/2-failtest.py:FailTest.test/debug.log", "whiteboard": "", "end": 1462366291.980557, "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/2-failtest.py:FailTest.test", "start": 1462366291.977591, "test": "2-failtest.py:FailTest.test", "fail_reason": "This test is supposed to fail", "time": 0.0029659271240234375}, {"status": "PASS", "url": "3-synctest.py:SyncTest.test", "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/3-synctest.py:SyncTest.test/debug.log", "whiteboard": "", "end": 1462366294.713253, "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/3-synctest.py:SyncTest.test", "start": 1462366291.995889, "test": "3-synctest.py:SyncTest.test", "fail_reason": "None", "time": 2.7173640727996826}], "errors": 0, "job_id": "74e01c82c95009e7d126b4fd60d5e3c615aa7539", "skip": 0, "time": 3.721395969390869, "debuglog": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/job.log", "pass": 2, "failures": 1, "total": 3}

Alternatively human-readable version using `json.tool`::

    $ avocado run sleeptest.py failtest.py synctest.py --json - | python -m json.tool
    {
        "debuglog": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/job.log",
        "errors": 0,
        "failures": 1,
        "job_id": "74e01c82c95009e7d126b4fd60d5e3c615aa7539",
        "pass": 2,
        "skip": 0,
        "tests": [
            {
                "end": 1462366291.95844,
                "fail_reason": "None",
                "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/1-sleeptest.py:SleepTest.test",
                "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/1-sleeptest.py:SleepTest.test/debug.log",
                "start": 1462366290.957374,
                "status": "PASS",
                "test": "1-sleeptest.py:SleepTest.test",
                "time": 1.001065969467163,
                "url": "1-sleeptest.py:SleepTest.test",
                "whiteboard": ""
            },
            {
                "end": 1462366291.980557,
                "fail_reason": "This test is supposed to fail",
                "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/2-failtest.py:FailTest.test",
                "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/2-failtest.py:FailTest.test/debug.log",
                "start": 1462366291.977591,
                "status": "FAIL",
                "test": "2-failtest.py:FailTest.test",
                "time": 0.0029659271240234375,
                "url": "2-failtest.py:FailTest.test",
                "whiteboard": ""
            },
            {
                "end": 1462366294.713253,
                "fail_reason": "None",
                "logdir": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/3-synctest.py:SyncTest.test",
                "logfile": "/home/medic/avocado/job-results/job-2016-05-04T14.51-74e01c8/test-results/3-synctest.py:SyncTest.test/debug.log",
                "start": 1462366291.995889,
                "status": "PASS",
                "test": "3-synctest.py:SyncTest.test",
                "time": 2.7173640727996826,
                "url": "3-synctest.py:SyncTest.test",
                "whiteboard": ""
            }
        ],
        "time": 3.721395969390869,
        "total": 3
    }

.. note:: The dash `-` in the option `--json`, it means that the xunit result
          should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to accommodate
newer Avocado features. A reasonable effort will be made to not break
backwards compatibility with applications that parse the current form of its
JSON result.

Silent result
~~~~~~~~~~~~~

While not a very fancy result format, an application may want nothing but
the exit status code from an Avocado test job run. Example::

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
   {"tests": [{"status": "PASS", "url": "1-sleeptest.py:SleepTest.test",...

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
ORed toghether as a simgle exit code. The final exit code can be debundled so
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
format, you can refer to :mod:`avocado.core.plugins.xunit` and use it as a
starting point.

In a nutshell, you have to implement a class that inherits from
:class:`avocado.core.result.TestResult` and implements all public methods,
that perform actions (write to a file/stream) for each test states. You can
take a look at :doc:`Plugins` for more information on how to write a plugin
that will activate and execute the new result format.
