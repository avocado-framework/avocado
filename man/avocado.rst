:title: avocado
:subtitle: test runner command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

 avocado [-h] [-v] [--logdir LOGDIR] [--loglevel LOG_LEVEL] [--plugins PLUGINS_DIR]
 {run,list,sysinfo,multiplex,plugins,datadir} ...

DESCRIPTION
===========

Avocado is an experimental test framework that is built on the experience
accumulated with `autotest` (`http://autotest.github.io`).

`avocado` is also the name of its test runner command line tool.

OPTIONS
=======

The following list of options are builtin, application level `avocado`
options. Most other options are implemented via plugins and will depend
on them being loaded::

 -h, --help             show this help message and exit
 -v, --version          show program's version number and exit
 --logdir LOGDIR        Alternate logs directory
 --plugins PLUGINS_DIR  Load extra plugins from directory

Real use of avocado depends on running avocado subcommands. This a typical list
of avocado subcommands::

 run         Run one or more tests (test module in .py, test alias or dropin)
 list        List available test modules
 sysinfo     Collect system information
 multiplex   Generate a list of dictionaries with params from a multiplex file
 plugins     List all plugins loaded
 datadir     List all relevant directories used by avocado

To get usage instructions for a given subcommand, run it with `--help`. Example::

 $ avocado multiplex --help
 usage: avocado multiplex [-h] [--filter-only [FILTER_ONLY [FILTER_ONLY ...]]]
                          [--filter-out [FILTER_OUT [FILTER_OUT ...]]] [-t]
                          [-c]
                          [multiplex_file]

 positional arguments:
   multiplex_file        Path to a multiplex file

 optional arguments:
   -h, --help            show this help message and exit
   --filter-only [FILTER_ONLY [FILTER_ONLY ...]]
                         Filter only path(s) from multiplexing
   --filter-out [FILTER_OUT [FILTER_OUT ...]]
                         Filter out path(s) from multiplexing
   -t, --tree            Shows the multiplex tree structure
   -c, --contents        Shows the variant's content (variables)


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

DEBUGGING TESTS
===============

When you are developing new tests, frequently you want to look at the straight
output of the job log in the stdout, without having to tail the job log.
In order to do that, you can use --show-job-log to the avocado test runner::

    $ scripts/avocado run examples/tests/sleeptest.py --show-job-log
    Not logging /proc/slabinfo (lack of permissions)
    START examples/tests/sleeptest.py

    Test instance parameters:
        id = examples/tests/sleeptest.py

    Default parameters:
        sleep_length = 1.0

    Test instance params override defaults whenever available

    Sleeping for 1.00 seconds
    Not logging /var/log/messages (lack of permissions)
    PASS examples/tests/sleeptest.py

    Not logging /proc/slabinfo (lack of permissions)

Let's say you are debugging a test particularly large, with lots of debug
output and you want to reduce this output to only messages with level 'INFO'
and higher. You can use the option --job-log-level info to reduce the output.
Running the same example with this option::

    $ scripts/avocado run sleeptest --show-job-log --job-log-level info
    START sleeptest.py
    PASS sleeptest.py

The levels you can choose are the levels available in the python logging system
`https://docs.python.org/2/library/logging.html#logging-levels`, translated
to lowercase strings, so 'notset', 'debug', 'info', 'warning', 'error',
'critical', in order of severity.

As you can see, the UI output is suppressed and only the job log goes to
stdout, making this a useful feature for test development/debugging.

SILENCING RUNNER STDOUT
=======================

You may specify --silent, that means avocado will turn off all runner
stdout. Even if you specify things like --show-job-log in the CLI, --silent
will have precedence and you will not get application stdout. Note that --silent
does not affect on disk job logs, those continue to be generated normally.


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

 $ avocado multiplex examples/tests/sleeptest.py.data/sleeptest.yaml
 Variants generated:
 Variant 1:    /short
     sleep_length: 0.5
 Variant 2:    /medium
     sleep_length: 1
 Variant 3:    /long
     sleep_length: 5
 Variant 4:    /longest
     sleep_length: 10

 $ avocado run --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml sleeptest

And the output should look like::

 JOB ID    : <id>
 JOB LOG   : /home/<user>/avocado/job-results/job-<date-<shortid>/job.log
 TESTS     : 4
 (1/4) sleeptest.py.1:  PASS (0.50 s)
 (2/4) sleeptest.py.2:  PASS (1.00 s)
 (3/4) sleeptest.py.3:  PASS (5.01 s)
 (4/4) sleeptest.py.4:  PASS (10.01 s)
 PASS      : 4
 ERROR     : 0
 FAIL      : 0
 SKIP      : 0
 WARN      : 0
 NOT FOUND : 0
 TIME      : 16.53 s

The `multiplex` plugin and the test runner supports two kinds of global
filters, through the command line options `--filter-only` and `--filter-out`.
The `filter-only` exclusively includes one or more paths and
the `filter-out` removes one or more paths from being processed.

From the previous example, if we are interested to use the variants `/medium`
and `longest`, we do the following command line::

 $ avocado run --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml sleeptest \
       --filter-only /medium /longest

And if you want to remove `/small` from the variants created,
we do the following::

 $ avocado run --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml sleeptest \
       --filter-out /medium

Note that both filters can be arranged in the same command line.

DEBUGGING BINARIES RUN AS PART OF A TEST
========================================

One interesting avocado feature is the ability to automatically and
transparently run binaries that are used on a given test inside the
GNU debugger.

Suppose you are running a test that uses an external, compiled, image
converter. Now suppose you're feeding it with different types of images,
including broken image files, and it fails at a given point. You wish
you could connect to the debugger at that given source location while
your test is running. This is how to do just that with avocado::

 $ avocado run --gdb-run-bin=convert:convert_ppm_to_raw converttest

The job starts running just as usual, and so does your test::

 JOB ID    : <id>
 JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
 TESTS     : 1
 (1/1) converttest.py: /

The `convert` binary though, automatically runs inside GDB. Avocado will
stop when the given breakpoint is reached::

 TEST PAUSED because of debugger breakpoint. To DEBUG your application run:
 /home/<user>/avocado/job-results/job-<date>-<shortid>/test-results/converttest.py/data/convert.gdb.sh

 NOTE: please use *disconnect* command in gdb before exiting, or else the debugged process will be KILLED

From this point, you can run the generated script (`convert.gdb.sh`) to
debug you application.

As noted, it is strongly recommended that you *disconnect* from gdb while
your binary is still running. That is, if the binary finished running
while you are debugging it, avocado has no way to know about its status.

Avocado will automatically send a `continue` command to the debugger
when you disconnect from and exit gdb.

If, for some reason you have a custom GDB, or your system does not put
GDB on what avocado believes to be the standard location (`/usr/bin/gdb`),
you can override that with::

 $ avocado run --gdb-path=~/code/gdb/gdb --gdb-run-bin=foo:main footest

The same applies to `gdbserver`, which can be chosen with a command line like::

 $ avocado run --gdbserver-path=~/code/gdb/gdbserver --gdb-run-bin=foo:main footest

RECORDING TEST REFERENCE OUTPUT
===============================

As a tester, you may want to check if the output of a given application matches
an expected output. In order to help with this common use case, we offer the
option ``--output-check-record [mode]`` to the test runner. If this option is
used, it will store the stdout or stderr of the process (or both, if you
specified ``all``) being executed to reference files: ``stdout.expected`` and
``stderr.expected``.

Those files will be recorded in the test data dir. The data dir is in the same
directory as the test source file, named ``[source_file_name.data]``. Let's
take as an example the test ``synctest.py``. In a fresh checkout of avocado,
you can see::

        examples/tests/synctest.py.data/stderr.expected
        examples/tests/synctest.py.data/stdout.expected

From those 2 files, only stdout.expected is non empty::

    $ cat examples/tests/synctest.py.data/stdout.expected
    PAR : waiting
    PASS : sync interrupted

The output files were originally obtained using the test runner and passing the
option --output-check-record all to the test runner::

    $ avocado run --output-check-record all examples/tests/synctest.py
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS     : 1
    (1/1) examples/tests/synctest.py: PASS (2.20 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 0
    SKIP      : 0
    WARN      : 0
    NOT FOUND : 0
    TIME      : 2.20 s

After the reference files are added, the check process is transparent, in the
sense that you do not need to provide special flags to the test runner.
Now, every time the test is executed, after it is done running, it will check
if the outputs are exactly right before considering the test as PASSed. If you
want to override the default behavior and skip output check entirely, you may
provide the flag ``--disable-output-check`` to the test runner.

The ``avocado.utils.process`` APIs have a parameter ``allow_output_check``
(defaults to ``all``), so that you can select which process outputs will go to
the reference files, should you chose to record them. You may choose ``all``,
for both stdout and stderr, ``stdout``, for the stdout only, ``stderr``, for
only the stderr only, or ``none``, to allow neither of them to be recorded and
checked.

This process works fine also with dropin tests (random executables that
return 0 (PASSed) or != 0 (FAILed). Let's consider our bogus example::

    $ cat output_record.sh
    #!/bin/bash
    echo "Hello, world!"

Let's record the output (both stdout and stderr) for this one::

    $ avocado run output_record.sh --output-check-record all
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS     : 1
    (1/1) home/lmr/Code/avocado.lmr/output_record.sh: PASS (0.01 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 0
    SKIP      : 0
    WARN      : 0
    NOT FOUND : 0
    TIME      : 0.01 s

After this is done, you'll notice that a the test data directory
appeared in the same level of our shell script, containing 2 files::

    $ ls output_record.sh.data/
    stderr.expected  stdout.expected

Let's look what's in each of them::

    $ cat output_record.sh.data/stdout.expected
    Hello, world!
    $ cat output_record.sh.data/stderr.expected
    $

Now, every time this test runs, it'll take into account the expected files that
were recorded, no need to do anything else but run the test.

RUNNING REMOTE TESTS
====================

Avocado allows you to execute tests on a remote machine by means of a SSH
network connection. The remote machine must be configured to accept remote
connections and the Avocado framework have to be installed in both origin
and remote machines.

When running tests on remote machine, the test sources and its data (if any present)
are transfered to the remote target, just before the test execution.
After the test execution, all test results are transfered back to the origin machine.

Here is how to run the sleeptest example test in a remote machine with IP
address 192.168.0.123 (standard port 22), remote user name `fedora` and
remote user password `123456`::

 $ avocado run --remote-hostname 192.168.0.123 --remote-username fedora --remote-password 123456

The output should look like::

 REMOTE LOGIN  : fedora@192.168.0.123:22
 JOB ID    : <JOBID>
 JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
 TESTS     : 1
 (1/1) sleeptest.py:  PASS (1.01 s)
 PASS      : 1
 ERROR     : 0
 NOT FOUND : 0
 FAIL      : 0
 SKIP      : 0
 WARN      : 0
 TIME      : 1.01 s

For more information, please consult the topic Remote Machine Plugin
on Avocado's online documentation.

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

Avocado Development Team <avocado-devel@redhat.com>
