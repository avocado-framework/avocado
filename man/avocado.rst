:title: avocado
:subtitle: test runner command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

::

 avocado [-h] [-v] [-V] [--logdir LOGDIR] [--loglevel LOG_LEVEL]
         [--plugins PLUGINS_DIR] [--vm]
         [--vm-hypervisor-uri VM_HYPERVISOR_URI] [--vm-domain VM_DOMAIN]
         [--vm-hostname VM_HOSTNAME] [--vm-username VM_USERNAME]
         [--vm-password VM_PASSWORD] [--vm-cleanup] [--json JSON_OUTPUT]
         [--xunit XUNIT_OUTPUT] [--journal]
         {list,sysinfo,run,multiplex,plugins,datadir} ...

DESCRIPTION
===========

Avocado is an experimental test framework that is built on the experience
accumulated with `autotest` (`http://autotest.github.io`).

`avocado` is also the name of its test runner command line tool.

OPTIONS
=======

The following list of options are builtin `avocado` options. Most other options
are implemented via plugins and will depend on them being loaded.

 -h, --help             show a help message and exit
 -v, --version          show program's version number and exit
 -V, --verbose          print extra debug messages
 --logdir LOGDIR        alternate logs directory
 --loglevel LOG_LEVEL   debug level
 --plugins PLUGINS_DIR  Load extra plugins from directory

RUNNING A TEST
==============

The most common use of the `avocado` command line tool is to run a test::

 $ avocado run sleeptest

This command will run the `sleeptest` test, as found on the standard test
directories. The output should be similar to::

 JOB ID    : <id>
 JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
 TESTS     : 1
 (1/1) sleeptest.py: PASS (1.00 s)
 PASS      : 1
 ERROR     : 0
 FAIL      : 0
 SKIP      : 0
 WARN      : 0
 NOT FOUND : 0
 TIME      : 1.00 s

The test directories will vary depending on you system and
installation method used. Still, it's pretty easy to find that out as shown
in the next section.

LISTING TESTS
=============

The `avocado` command line tool also has a `list` command, that lists the
known tests in the standard test directory::

 $ avocado list

The output should be similar to::

 Tests dir: /home/<user>/local/avocado/tests
     Alias         Path
     sleeptest     /home/<user>/local/avocado/tests/sleeptest.py
     ...
     warntest      /home/<user>/local/avocado/tests/warntest.py
     sleeptenmin   /home/<user>/local/avocado/tests/sleeptenmin.py

EXPLORING RESULTS
=================

When `avocado` runs tests, it saves all its results on your system::

 JOB ID    : <id>
 JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log

For your convenience, `avocado` maintains a link to the latest job run
(an `avocado run` command in this context), so you can always use `"latest"`
to browse your test results::

 $ ls /home/<user>/avocado/job-results/latest
 id
 job.log
 results.json
 results.xml
 sysinfo
 test-results

The main log file is `job.log`, but every test has its own results directory::

 $ ls -1 ~/avocado/job-results/latest/test-results/
 sleeptest.py

Since this is a directory, it should have content similar to::

 $ ls -1 ~/avocado/job-results/latest/test-results/sleeptest.py/
 data
 debug.log
 sysinfo

MULTIPLEX
=========

Avocado has a powerful tool that enables multiple test scenarios to be run
using a single, unmodified test. This mechanism uses a multiplex file, that
multiplies all possible variations automatically.

A command by the same name, `multiplex`, is available on the `avocado`
command line tool, and enables you to see all the test scenarios that can
be run::

 $ avocado multiplex tests/sleeptest.py.data/sleeptest.mplx
 Dictionaries generated:
    dict 1:    sleeptest.short
    dict 2:    sleeptest.medium
    dict 3:    sleeptest.long

For the more curious, you can use the `-c` command line option to see what
parameters would be available to each variation of the sleeptest.

To run all the test variations you can use::

 $ avocado run --multiplex tests/sleeptest.py.data/sleeptest.mplx sleeptest

And the output should look like::

 ...
 (1/3) sleeptest.py.short: PASS (0.50 s)
 (2/3) sleeptest.py.medium: PASS (1.00 s)
 (3/3) sleeptest.py.long: PASS (5.00 s)
 ...

FILES
=====

::

 /etc/avocado/settings.ini
    system wide configuration file

BUGS
====

If you find a bug, please report it over our github page as an issue.

MORE INFORMATION
================

For more information check Avocado's online documentation at: `http://avocado-framework.readthedocs.org/`

Or the project github page at: `http://github.com/avocado-framework`


AUTHOR
======

Cleber Rosa <cleber@redhat.com>
