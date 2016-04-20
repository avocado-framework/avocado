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

    $ avocado run sleeptest failtest synctest
    JOB ID    : 5ffe479262ea9025f2e4e84c4e92055b5c79bdc9
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/job.log
    TESTS     : 3
     (1/3) sleeptest.1: PASS (1.01 s)
     (2/3) failtest.1: FAIL (0.00 s)
     (3/3) synctest.1: PASS (1.98 s)
    RESULTS    : PASS 1 | ERROR 1 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html
    TIME      : 3.17 s

The most important thing is to remember that programs should never need to parse
human output to figure out what happened to a test job run.

HTML report
~~~~~~~~~~~

As can be seen in the previous example, Avocado shows the path to an HTML
report that will be generated as soon as the job finishes running::

    $ avocado run sleeptest failtest synctest
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

Out of the box, Avocado supports a couple of machine readable results.

xunit
~~~~~

The default machine readable output in Avocado is
`xunit <http://help.catchsoftware.com/display/ET/JUnit+Format>`__.

xunit is an XML format that contains test results in a structured form, and
are used by other test automation projects, such as `jenkins
<http://jenkins-ci.org/>`__. If you want to make Avocado to generate xunit
output in the standard output of the runner, simply use::

    $ scripts/avocado --xunit - run "sleeptest failtest synctest"
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="avocado" tests="3" errors="0" failures="1" skipped="0" time="2.88632893562" timestamp="2014-04-24 18:25:39.545588">
        <testcase classname="sleeptest" name="sleeptest.1" time="1.10091400146"/>
        <testcase classname="failtest" name="failtest.1" time="0.0921177864075">
            <failure><![CDATA[This test is supposed to fail]]></failure>
        </testcase>
        <testcase classname="synctest" name="synctest.1" time="1.69329714775"/>

Note the dash `-` in the option `--xunit`, it means that the xunit result
should go to the standard output.

json
~~~~

`JSON <http://www.json.org/>`__ is a widely used data exchange format. The
json Avocado plugin outputs job information, similarly to the xunit output
plugin::

    $ scripts/avocado --json - run "sleeptest failtest synctest"
    {"tests": [{"test": "sleeptest.1", "url": "sleeptest", "status": "PASS", "time": 1.4282619953155518}, {"test": "failtest.1", "url": "failtest", "status": "FAIL", "time": 0.34017300605773926}, {"test": "synctest.1", "url": "synctest", "status": "PASS", "time": 2.109131097793579}], "errors": 0, "skip": 0, "time": 3.87756609916687, "debuglog": "$HOME/avocado/logs/run-2014-06-11-01.35.15/debug.log", "pass": 2, "failures": 1, "total": 3}

Note the dash `-` in the option `--json`, it means that the xunit result
should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to acommodate
newer Avocado features. A reasonable effort will be made to not break
backwards compatibility with applications that parse the current form of its
JSON result.

Silent result
~~~~~~~~~~~~~

While not a very fancy result format, an application may want nothing but
the exit status code from an Avocado test job run. Example::

    $ avocado --silent run failtest
    $ echo $?
    1

In practice, this would usually be used by scripts that will in turn run
Avocado and check its results::

    #!/bin/bash
    ...
    avocado run /path/to/my/test.py --silent
    if [ $? == 0 ]; then
       echo "great success!"
    elif
       ...

Multiple results at once
------------------------

You can have multiple results formats at once, as long as only one of them
uses the standard output. For example, it is fine to use the xunit result on
stdout and the JSON result to output to a file::

    $ scripts/avocado --xunit - --json /tmp/result.json run "sleeptest synctest"
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="avocado" tests="2" errors="0" failures="0" skipped="0" time="3.21392536163" timestamp="2014-06-11 01:49:35.858187">
        <testcase classname="sleeptest" name="sleeptest.1" time="1.34533214569"/>
        <testcase classname="synctest" name="synctest.1" time="1.86859321594"/>
    </testsuite>

    $ cat /tmp/result.json
    {"tests": [{"test": "sleeptest.1", "url": "sleeptest", "status": "PASS", "time": 1.345332145690918}, {"test": "synctest.1", "url": "synctest", "status": "PASS", "time": 1.8685932159423828}], "errors": 0, "skip": 0, "time": 3.213925361633301, "debuglog": "$HOME/avocado/logs/run-2014-06-11-01.49.35/debug.log", "pass": 2, "failures": 0, "total": 2}

But you won't be able to do the same without the --json flag passed to
the program::

    $ scripts/avocado --xunit - --json - run "sleeptest synctest"
    Avocado could not set --json and --xunit both to output to stdout.
    Please set the output flag of one of them to a file to avoid conflicts.

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
