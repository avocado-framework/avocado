:title: avocado
:subtitle: test runner command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

 avocado [-h] [-v] [--config CONFIG_FILE]
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
 --config CONFIG_FILE   Use custom configuration from a file

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
 RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
 TESTS TIME : 1.00 s

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
using a single, unmodified test. This mechanism uses a YAML file called the
'multiplex file', that tells avocado how to multiply all possible test scenarios
automatically.

A command by the same name, `multiplex`, is available on the `avocado`
command line tool, and enables you to see all the test scenarios that can
be run::

 $ avocado multiplex -c examples/tests/sleeptest.py.data/sleeptest.yaml
 Variants generated:

 Variant 1:    /run/short
     /run/short:sleep_length => 0.5

 Variant 2:    /run/medium
     /run/medium:sleep_length => 1

 Variant 3:    /run/long
     /run/long:sleep_length => 5

 Variant 4:    /run/longest
     /run/longest:sleep_length => 10

This is a sample that varies the parameter `sleep_length` through the scenarios
``/run/short`` (sleeps for 0.5 s), ``/run/medium`` (sleeps for 1 s),
``/run/long`` (sleeps for 5s), ``/run/longest`` (sleeps for 10s). The YAML
file (multiplex file) that produced the output above is::

 !mux
 short:
     sleep_length: 0.5
 medium:
     sleep_length: 1
 long:
     sleep_length: 5
 longest:
     sleep_length: 10

You can execute `sleeptest` in all variations exposed above with:

 $ avocado run sleeptest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml

And the output should look like::

 JOB ID     : <id>
 JOB LOG    : /home/<user>/avocado/job-results/job-<date-<shortid>/job.log
 TESTS      : 4
 (1/4) sleeptest.py: PASS (0.50 s)
 (2/4) sleeptest.py.1: PASS (1.00 s)
 (3/4) sleeptest.py.2: PASS (5.01 s)
 (4/4) sleeptest.py.3: PASS (10.01 s)
 PASS       : 4
 ERROR      : 0
 FAIL       : 0
 SKIP       : 0
 WARN       : 0
 INTERRUPT  : 0
 TESTS TIME : 16.52 s

The `multiplex` plugin and the test runner supports two kinds of global
filters, through the command line options `--filter-only` and `--filter-out`.
The `filter-only` exclusively includes one or more paths and
the `filter-out` removes one or more paths from being processed.

From the previous example, if we are interested to use the variants `/run/medium`
and `/run/longest`, we do the following command line::

 $ avocado run sleeptest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml \
       --filter-only /run/medium /run/longest

And if you want to remove `/small` from the variants created,
we do the following::

 $ avocado run sleeptest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml \
       --filter-out /run/medium

Note that both `--filter-only` and `--filter-out` filters can be arranged in
the same command line.

The multiplexer also supports default paths. The base path is ``/run/*`` but it
can be overridden by ``--mux-path``, which accepts multiple arguments. What it
does: it splits leaves by the provided paths. Each query goes one by one through
those sub-trees and first one to hit the match returns the result. It might not
solve all problems, but it can help to combine existing YAML files with your
ones::

    qa:         # large and complex read-only file, content injected into /qa
        tests:
            timeout: 10
        ...
    my_variants: !mux        # your YAML file injected into /my_variants
        short:
            timeout: 1
        long:
            timeout: 1000

You want to use an existing test which uses ``params.get('timeout', '*')``.  Then you
can use ``--mux-path '/my_variants/*' '/qa/*'`` and it'll first look in your
variants. If no matches are found, then it would proceed to ``/qa/*``

Keep in mind that only slices defined in mux-path are taken into account for
relative paths (the ones starting with ``*``).

DEBUGGING EXECUTABLES RUN AS PART OF A TEST
===========================================

One interesting avocado feature is the ability to automatically and
transparently run executables that are used on a given test inside the
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

The `convert` executable though, automatically runs inside GDB. Avocado will
stop when the given breakpoint is reached::

 TEST PAUSED because of debugger breakpoint. To DEBUG your application run:
 /home/<user>/avocado/job-results/job-<date>-<shortid>/test-results/converttest.py/data/convert.gdb.sh

 NOTE: please use *disconnect* command in gdb before exiting, or else the debugged process will be KILLED

From this point, you can run the generated script (`convert.gdb.sh`) to
debug you application.

As noted, it is strongly recommended that you *disconnect* from gdb while
your executable is still running. That is, if the executable finished running
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

WRAP EXECUTABLE RUN BY TESTS
============================

Avocado allows the instrumentation of executables being run by a test
in a transparent way. The user specifies a script ("the wrapper") to be
used to run the actual program called by the test.

If the instrumentation script is implemented correctly, it should not
interfere with the test behavior. That is, the wrapper should avoid
changing the return status, standard output and standard error messages
of the original executable.

The user can be specific about which program to wrap (with a shell-like glob),
or if that is omitted, a global wrapper that will apply to all
programs called by the test.

So, for every executable run by the test, the program name will be
compared to the pattern to decide whether to wrap it or not. You can
have multiples wrappers and patterns defined.

Examples::

 $ avocado run datadir --wrapper examples/wrappers/strace.sh

Any command created by the test datadir will be wrapped on ``strace.sh``. ::

 $ avocado run datadir --wrapper examples/wrappers/ltrace.sh:*make \
                       --wrapper examples/wrappers/perf.sh:*datadir

Any command that matches the pattern `*make` will
be wrapper on ``ltrace.sh`` and the pattern ``*datadir`` will trigger
the execution of ``perf.sh``. ::

Note that it is not possible to use ``--gdb-run-bin`` together
with ``--wrapper``, they are incompatible.

RUNNING TESTS WITH AN EXTERNAL RUNNER
=====================================

It's quite common to have organically grown test suites in most
software projects. These usually include a custom built, very specific
test runner that knows how to find and run their own tests.

Still, running those tests inside Avocado may be a good idea for
various reasons, including being able to have results in different
human and machine readable formats, collecting system information
alongside those tests (the Avocado's `sysinfo` functionality), and
more.

Avocado makes that possible by means of its "external runner" feature. The
most basic way of using it is::

    $ avocado run --external-runner=/path/to/external_runner foo bar baz

In this example, Avocado will report individual test results for tests
`foo`, `bar` and `baz`. The actual results will be based on the return
code of individual executions of `/path/to/external_runner foo`,
`/path/to/external_runner bar` and finally `/path/to/external_runner baz`.

As another way to explain an show how this feature works, think of the
"external runner" as some kind of interpreter and the individual tests as
anything that this interpreter recognizes and is able to execute. A
UNIX shell, say `/bin/sh` could be considered an external runner, and
files with shell code could be considered tests::

    $ echo "exit 0" > /tmp/pass
    $ echo "exit 1" > /tmp/fail
    $ avocado run --external-runner=/bin/sh /tmp/pass /tmp/fail
    JOB ID     : 4a2a1d259690cc7b226e33facdde4f628ab30741
    JOB LOG    : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS      : 2
    (1/2) /tmp/pass: PASS (0.01 s)
    (2/2) /tmp/fail: FAIL (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 0.01 s
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html

This example is pretty obvious, and could be achieved by giving
`/tmp/pass` and `/tmp/fail` shell "shebangs" (`#!/bin/sh`), making
them executable (`chmod +x /tmp/pass /tmp/fail)`, and running them as
"SIMPLE" tests.

But now consider the following example::

    $ avocado run --external-runner=/bin/curl http://local-avocado-server:9405/jobs/ \
                                           http://remote-avocado-server:9405/jobs/
    JOB ID     : 56016a1ffffaba02492fdbd5662ac0b958f51e11
    JOB LOG    : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS      : 2
    (1/2) http://local-avocado-server:9405/jobs/: PASS (0.02 s)
    (2/2) http://remote-avocado-server:9405/jobs/: FAIL (3.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 3.04 s
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html

This effectively makes `/bin/curl` an "external test runner", responsible for
trying to fetch those URLs, and reporting PASS or FAIL for each of them.

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
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 2.20 s

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
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 0.01 s

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
 RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
 TESTS TIME : 1.01 s

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
