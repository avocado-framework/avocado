:title: avocado
:subtitle: test runner command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

 avocado [-h] [-v] [--plugins PLUGINS_DIR]
 {run,list,sysinfo,multiplex,plugins,datadir} ...

DESCRIPTION
===========

Avocado is a modern test framework that is built on the experience
accumulated with `autotest` (`http://autotest.github.io`).

`avocado` is also the name of its test runner command line tool, described in
this man page.

For more information about the Avocado project, please check its website:
http://avocado-framework.github.io/

OPTIONS
=======

The following list of options are builtin, application level `avocado`
options. Most other options are implemented via plugins and will depend
on them being loaded::

 -h, --help             show this help message and exit
 -v, --version          show program's version number and exit
 --plugins PLUGINS_DIR  Load extra plugins from directory

Real use of avocado depends on running avocado subcommands. This a typical list
of avocado subcommands::

 run         Run one or more tests (native test, test alias, binary or script)
 list        List available test modules
 sysinfo     Collect system information
 multiplex   Generate a list of dictionaries with params from multiplex file(s)
 plugins     List all plugins loaded
 distro      Shows detected Linux distribution
 datadir     List all relevant directories used by avocado

To get usage instructions for a given subcommand, run it with `--help`. Example::

 $ avocado multiplex --help
 usage: avocado multiplex [-h] [--filter-only [FILTER_ONLY [FILTER_ONLY ...]]]
                          [--filter-out [FILTER_OUT [FILTER_OUT ...]]] [-t]
                          [-c]
                          multiplex_files [multiplex_files ...]

 positional arguments:
   multiplex_files       Path(s) to a multiplex file(s)

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
and higher. You can set job-log-level to info to reduce the amount of output.

Edit your `~/.config/avocado/avocado.conf` file and add::

    [job.output]
    loglevel = info

Running the same example with this option will give you::

    $ scripts/avocado run sleeptest --show-job-log
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

SILENCING SYSINFO REPORT
========================

You may specify --sysinfo=off and avocado will not collect profilers,
hardware details and other system information, inside the job result directory.

LISTING TESTS
=============

The `avocado` command line tool also has a `list` command, that lists the
known tests in a given path, be it a path to an individual test, or a path
to a directory. If no arguments provided, avocado will inspect the contents
of the test location being used by avocado (if you are in doubt about which
one is that, you may use `avocado config --datadir`). The output looks like::

    $ avocado list
    INSTRUMENTED /usr/share/avocado/tests/abort.py
    INSTRUMENTED /usr/share/avocado/tests/datadir.py
    INSTRUMENTED /usr/share/avocado/tests/doublefail.py
    INSTRUMENTED /usr/share/avocado/tests/doublefree.py
    INSTRUMENTED /usr/share/avocado/tests/errortest.py
    INSTRUMENTED /usr/share/avocado/tests/failtest.py
    INSTRUMENTED /usr/share/avocado/tests/fiotest.py
    INSTRUMENTED /usr/share/avocado/tests/gdbtest.py
    INSTRUMENTED /usr/share/avocado/tests/gendata.py
    INSTRUMENTED /usr/share/avocado/tests/linuxbuild.py
    INSTRUMENTED /usr/share/avocado/tests/multiplextest.py
    INSTRUMENTED /usr/share/avocado/tests/passtest.py
    INSTRUMENTED /usr/share/avocado/tests/skiptest.py
    INSTRUMENTED /usr/share/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/avocado/tests/trinity.py
    INSTRUMENTED /usr/share/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/avocado/tests/whiteboard.py

Here, `INSTRUMENTED` means that the files there are python files with an avocado
test class in them, therefore, that they are what we call instrumented tests.
This means those tests can use all avocado APIs and facilities. Let's try to
list a directory with a bunch of executable shell scripts::

    $ avocado list examples/wrappers/
    SIMPLE examples/wrappers/dummy.sh
    SIMPLE examples/wrappers/ltrace.sh
    SIMPLE examples/wrappers/perf.sh
    SIMPLE examples/wrappers/strace.sh
    SIMPLE examples/wrappers/time.sh
    SIMPLE examples/wrappers/valgrind.sh

Here, `SIMPLE` means that those files are executables, that avocado will simply
execute and return PASS or FAIL depending on their return codes (PASS -> 0,
FAIL -> any integer different than 0). You can also provide the `--verbose`,
or `-V` flag to display files that were detected but are not avocado tests,
along with summary information::

    $ avocado list examples/gdb-prerun-scripts/ -V
    Type       file
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    SIMPLE: 0
    INSTRUMENTED: 0
    BUGGY: 0
    MISSING: 0
    NOT_A_TEST: 2

That summarizes the basic commands you should be using more frequently when
you start with avocado. Let's talk now about how avocado stores test results.

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

 $ avocado run sleeptest --multiplex-files examples/tests/sleeptest.py.data/sleeptest.yaml

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
 TIME      : 16.53 s

The `multiplex` plugin and the test runner supports two kinds of global
filters, through the command line options `--filter-only` and `--filter-out`.
The `filter-only` exclusively includes one or more paths and
the `filter-out` removes one or more paths from being processed.

From the previous example, if we are interested to use the variants `/medium`
and `longest`, we do the following command line::

 $ avocado run sleeptest --multiplex-files examples/tests/sleeptest.py.data/sleeptest.yaml \
       --filter-only /medium /longest

And if you want to remove `/small` from the variants created,
we do the following::

 $ avocado run sleeptest --multiplex-files examples/tests/sleeptest.py.data/sleeptest.yaml \
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
you can override that in the section `gdb.paths` of your documentation::

    [gdb.paths]
    gdb = /usr/bin/gdb
    gdbserver = /usr/bin/gdbserver

So running avocado after setting those will use the appropriate gdb/gdbserver
path.

If you are debugging a special application and need to setup GDB in custom
ways by running GDB commands, you can do that with the `--gdb-prerun-commands`
option::

 $ avocado run --gdb-run-bin=foo:bar --gdb-prerun-commands=/tmp/disable-signals footest

In this example, `/tmp/disable-signals` is a simple text file containing two lines::

 signal SIGUSR1 pass
 signal SIGUSR1 nostop

Each line is a GDB command, so you can have from simple to very complex
debugging environments configured like that.

WRAP PROCESS IN TESTS
=====================

Avocado allows the instrumentation of applications being
run by a test in a transparent way.

The user specify a script ("the wrapper") to be used to run the actual
program called by the test.  If the instrument is
implemented correctly, it should not interfere with the test behavior.

So it means that the wrapper should avoid to change the return status,
standard output and standard error messages of the process.

By using an optional parameter to the wrapper, you can specify the
"target binary" to wrap, so that for every program spawned by the test,
the program name will be compared to the target binary.

If the target binary is absolute path and the program name is absolute,
then both paths should be equal to the wrapper take effect, otherwise
the wrapper will not be used.

For the case that the target binary is not absolute or the program name
is not absolute, then both will be compared by its base name, ignoring paths.

Examples::

 $ avocado run datadir --wrapper examples/wrappers/strace.sh
 $ avocado run datadir --wrapper examples/wrappers/ltrace.sh:make \
                       --wrapper examples/wrappers/perf.sh:datadir

Note that it's not possible to use ``--gdb-run-bin`` together
with ``--wrapper``, they are incompatible.::

 $ avocado run mytest --wrapper examples/wrappers/strace:/opt/bin/foo

In this case, the possible program that can wrapped by ``mytest`` is
``/opt/bin/foo`` (absolute paths equal) and ``foo`` without absolute path
will be wrapped too, but ``/opt/bin/foo`` will never be wrapped, because
the absolute paths are not equal.

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
    TIME      : 2.20 s

After the reference files are added, the check process is transparent, in the
sense that you do not need to provide special flags to the test runner.
Now, every time the test is executed, after it is done running, it will check
if the outputs are exactly right before considering the test as PASSed. If you
want to override the default behavior and skip output check entirely, you may
provide the flag ``--output-check=off`` to the test runner.

The ``avocado.utils.process`` APIs have a parameter ``allow_output_check``
(defaults to ``all``), so that you can select which process outputs will go to
the reference files, should you chose to record them. You may choose ``all``,
for both stdout and stderr, ``stdout``, for the stdout only, ``stderr``, for
only the stderr only, or ``none``, to allow neither of them to be recorded and
checked.

This process works fine also with simple tests, executables that
return 0 (PASSed) or != 0 (FAILed). Let's consider our bogus example::

    $ cat output_record.sh
    #!/bin/bash
    echo "Hello, world!"

Let's record the output (both stdout and stderr) for this one::

    $ avocado run output_record.sh --output-check-record all
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS     : 1
    (1/1) home/$USER/Code/avocado/output_record.sh: PASS (0.01 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 0
    SKIP      : 0
    WARN      : 0
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
 FAIL      : 0
 SKIP      : 0
 WARN      : 0
 TIME      : 1.01 s

For more information, please consult the topic Remote Machine Plugin
on Avocado's online documentation.

LINUX DISTRIBUTION UTILITIES
============================

Avocado has some planned features that depend on knowing the Linux Distribution being used on the sytem.
The most basic command prints the detected Linux Distribution::

  $ avocado distro
  Detected distribution: fedora (x86_64) version 21 release 0

Other features are available with the same command when command line options are given, as shown by the
`--help` option.

For instance, it possible to create a so-called "Linux Distribution Definition" file, by inspecting an installation
tree. The installation tree could be the contents of the official installation ISO or a local network mirror.

These files let Avocado pinpoint if a given installed package is part of the original Linux Distribution or
something else that was installed from an external repository or even manually. This, in turn, can help
detecting regressions in base system pacakges that affected a given test result.

To generate a definition file run::

  $ avocado distro --distro-def-create --distro-def-name avocadix  \
                   --distro-def-version 1 --distro-def-arch x86_64 \
                   --distro-def-type rpm --distro-def-path /mnt/dvd

And the output will be something like::

   Loading distro information from tree... Please wait...
   Distro information saved to "avocadix-1-x86_64.distro"


FILES
=====

::

 /etc/avocado/avocado.conf
    system wide configuration file

BUGS
====

If you find a bug, please report it over our github page as an issue.

LICENSE
=======

Avocado is released under GPLv2 (explicit version)
`http://gnu.org/licenses/gpl-2.0.html`. Even though most of the current code is
licensed under a "and any later version" clause, some parts are specifically
bound to the version 2 of the license and therefore that's the official license
of the prject itself. For more details, please see the LICENSE file in the
project source code directory.

MORE INFORMATION
================

For more information please check Avocado's project website, located at
`http://avocado-framework.github.io/`. There you'll find links to online
documentation, source code and community resources.

AUTHOR
======

Avocado Development Team <avocado-devel@redhat.com>
