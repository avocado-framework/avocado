:title: avocado
:subtitle: test runner command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

avocado [-h] [-v] [--config [CONFIG_FILE]] [--show [STREAM[:LVL]]] [-s]
 {config,diff,distro,exec-path,list,multiplex,plugins,run,sysinfo} ...

DESCRIPTION
===========

Avocado is a modern test framework that is built on the experience
accumulated with `autotest` (https://autotest.github.io).

`avocado` is also the name of its test runner command line tool,
described in this man page.

For more information about the Avocado project, please check its
website: https://avocado-framework.github.io/

OPTIONS
=======

The following list of options are builtin, application level `avocado`
options. Most other options are implemented via plugins and will depend
on them being loaded (`avocado --help`)::

    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    --config [CONFIG_FILE]
                          Use custom configuration from a file
    --enable-paginator    Turn the paginator on. Useful when output is too long.
    -V, --verbose         Some commands can produce more information. This
                          option will enable the verbosity when applicable.
    --show CORE.SHOW      List of comma separated builtin logs, or logging
                          streams optionally followed by LEVEL (DEBUG,INFO,...).
                          Builtin streams are: "app": application output;
                          "test": test output; "debug": tracebacks and other
                          debugging info; "early": early logging of other
                          streams, including test (very verbose); "all": all
                          builtin streams; "none": disables regular output
                          (leaving only errors enabled). By default: 'app'

Real use of avocado depends on running avocado subcommands. This a
typical list of avocado subcommands::

    assets              Manage assets
    config              Shows avocado config keys
    diff                Shows the difference between 2 jobs.
    distro              Shows detected Linux distribution
    exec-path           Returns path to avocado bash libraries and exits.
    jobs                Manage Avocado jobs
    list                List available tests
    plugins             Displays plugin information
    replay              Runs a new job using a previous job as its
                        configuration
    run                 Runs one or more tests (native test, test alias,
                        binary or script)
    sysinfo             Collect system information
    variants            Tool to analyze and visualize test variants and params
    vmimage             Provides VM images acquired from official repositories


To get usage instructions for a given subcommand, run it with `--help`.
Example::

    $ avocado run --help

Options for subcommand `run` (`avocado run --help`)::

    positional arguments:
      TEST_REFERENCE        List of test references (aliases or paths)

    optional arguments:
      -h, --help            show this help message and exit
      -p NAME_VALUE, --test-parameter NAME_VALUE
                            Parameter name and value to pass to all tests. This is
                            only applicable when not using a varianter plugin.
                            This option format must be given in the NAME=VALUE
                            format, and may be given any number of times, or per
                            parameter.
      --suite-runner SUITE_RUNNER
                            Selects the runner implementation from one of the
                            installed and active implementations.  You can run
                            "avocado plugins" and find the list of valid runners
                            under the "Plugins that run test suites on a job
                            (runners) section.  Defaults to "nrunner", which is
                            the new runner and only runner supported at this moment.

      -d, --dry-run         Instead of running the test only list them and log
                            their params.
      --dry-run-no-cleanup  Do not automatically clean up temporary directories
                            used by dry-run
      --force-job-id UNIQUE_JOB_ID
                            Forces the use of a particular job ID. Used internally
                            when interacting with an avocado server. You should
                            not use this option unless you know exactly what
                            you're doing
      --job-results-dir DIRECTORY
                            Forces to use of an alternate job results directory.
      --job-category CATEGORY
                            Categorizes this within a directory with the same
                            name, by creating a link to the job result directory
      --job-timeout SECONDS
                            Set the maximum amount of time (in SECONDS) that tests
                            are allowed to execute. Values <= zero means "no
                            timeout". You can also use suffixes, like: s
                            (seconds), m (minutes), h (hours).
      --failfast            Enable the job interruption on first failed test.
      --keep-tmp            Keep job temporary files (useful for avocado
                            debugging).
      --ignore-missing-references
                            Force the job execution, even if some of the test.
      --disable-sysinfo     Enable or disable sysinfo information. Like hardware
                            details, profiles, etc.
      --execution-order RUN.EXECUTION_ORDER
                            Defines the order of iterating through test suite and
                            test variants
      --log-test-data-directories
                            Logs the possible data directories for each test. This
                            is helpful when writing new tests and not being sure
                            where to put data files. Look for "Test data
                            directories" in your test log
      --journal             Records test status changes (for use with avocado-
                            journal-replay and avocado-server)
      --json FILE           Enable JSON result format and write it to FILE. Use
                            "-" to redirect to the standard output.
      --disable-json-job-result
                            Enables default JSON result in the job results
                            directory. File will be named "results.json".
      --tap FILE            Enable TAP result output and write it to FILE. Use "-"
                            to redirect to standard output.
      --disable-tap-job-result
                            Enables default TAP result in the job results
                            directory. File will be named "results.tap"
      --tap-include-logs    Include test logs as comments in TAP output.
      -z, --archive         Archive (ZIP) files generated by tests

    output and result format:
      --store-logging-stream LOGGING_STREAM
                            Store given logging STREAMs in
                            "$JOB_RESULTS_DIR/$STREAM.$LEVEL."
      --xunit FILE          Enable xUnit result format and write it to FILE. Use
                            "-" to redirect to the standard output.
      --disable-xunit-job-result
                            Enables default xUnit result in the job results
                            directory. File will be named "results.xml".
      --xunit-job-name XUNIT_JOB_NAME
                            Override the reported job name. By default uses the
                            Avocado job name which is always unique. This is
                            useful for reporting in Jenkins as it only evaluates
                            first-failure from jobs of the same name.
      --xunit-max-test-log-chars SIZE
                            Limit the attached job log to given number of
                            characters (k/m/g suffix allowed)

    filtering parameters:
      -t TAGS, --filter-by-tags TAGS
                            Filter tests based on tags
      --filter-by-tags-include-empty
                            Include all tests without tags during filtering. This
                            effectively means they will be kept in the test suite
                            found previously to filtering.
      --filter-by-tags-include-empty-key
                            Include all tests that do not have a matching key in
                            its key:val tags. This effectively means those tests
                            will be kept in the test suite found previously to
                            filtering.

    JSON serialized based varianter options:
      --json-variants-load FILE
                            Load the Variants from a JSON serialized file

    nrunner specific options:
      --shuffle             Shuffle the tasks to be executed
      --status-server-disable-auto
                            If the status server should automatically choose a
                            "status_server_listen" and "status_server_uri"
                            configuration. Default is to auto configure a status
                            server.
      --status-server-listen HOST_PORT
                            URI where status server will listen on. Usually a
                            "HOST:PORT" string. This is only effective if
                            "status_server_auto" is disabled
      --status-server-uri HOST_PORT
                            URI for connecting to the status server, usually a
                            "HOST:PORT" string. Use this if your status server is
                            in another host, or different port. This is only
                            effective if "status_server_auto" is disabled
      --max-parallel-tasks NUMBER_OF_TASKS
                            Number of maximum number tasks running in parallel.
                            You can disable parallel execution by setting this to
                            1. Defaults to the amount of CPUs on this machine.
      --spawner SPAWNER     Spawn tasks in a specific spawner. Available spawners:
                            'process' and 'podman'

    podman spawner specific options:
      --spawner-podman-bin PODMAN_BIN
                            Path to the podman binary
      --spawner-podman-image CONTAINER_IMAGE
                            Image name to use when creating the container

    job replay:
      --replay JOB_ID       Replay a job identified by its (partial) hash id. Use
                            "--replay" latest to replay the latest job.
      --replay-test-status TEST_STATUS
                            Filter tests to replay by test status.
      --replay-ignore IGNORE
                            Ignore variants and/or configuration from the source
                            job.
      --replay-resume       Resume an interrupted job

    wrapper support:
      --wrapper SCRIPT[:EXECUTABLE]
                            Use a script to wrap executables run by a test. The
                            wrapper is either a path to a script (AKA a global
                            wrapper) or a path to a script followed by colon
                            symbol (:), plus a shell like glob to the target
                            EXECUTABLE. Multiple wrapper options are allowed, but
                            only one global wrapper can be defined.

Options for subcommand `assets` (`avocado assets --help`)::

    positional arguments:
      {fetch,register,purge,list}
        fetch               Fetch assets from test source or config file if it's
                            not already in the cache
        register            Register an asset directly to the cacche
        purge               Removes assets cached locally.
        list                List all cached assets.

    optional arguments:
      -h, --help            show this help message and exit

Options for subcommand `config` (`avocado config --help`)::

    positional arguments:
      sub-command
        reference  Show a configuration reference with all registered options

    optional arguments:
      -h, --help   show this help message and exit
      --datadir    Shows the data directories currently being used by Avocado

Options for subcommand `diff` (`avocado diff --help`)::

    positional arguments:
      JOB                   A job reference, identified by a (partial) unique ID
                            (SHA1) or test results directory.

    optional arguments:
      -h, --help            show this help message and exit
      --html FILE           Enable HTML output to the FILE where the result should
                            be written.
      --open-browser        Generate and open a HTML report in your preferred
                            browser. If no --html file is provided, create a
                            temporary file.
      --diff-filter DIFF_FILTER
                            Comma separated filter of diff sections:
                            (no)cmdline,(no)time,(no)variants,(no)results,
                            (no)config,(no)sysinfo (defaults to all enabled).
      --diff-strip-id       Strip the "id" from "id-name;variant" when comparing
                            test results.
      --create-reports      Create temporary files with job reports to be used by
                            other diff tools

    By default, a textual diff report is generated in the standard output.

Options for subcommand `distro` (`avocado distro --help`)::

    optional arguments:
      -h, --help            show this help message and exit
      --distro-def-create   Creates a distro definition file based on the path
                            given.
      --distro-def-name DISTRO_DEF_NAME
                            Distribution short name
      --distro-def-version DISTRO_DEF_VERSION
                            Distribution major version name
      --distro-def-release DISTRO_DEF_RELEASE
                            Distribution release version number
      --distro-def-arch DISTRO_DEF_ARCH
                            Primary architecture that the distro targets
      --distro-def-path DISTRO.DISTRO_DEF_PATH
                            Top level directory of the distro installation files
      --distro-def-type {rpm,deb}
                            Distro type (one of: rpm, deb)

Options for subcommand `exec-path` (`avocado exec-path --help`)::

    optional arguments:
      -h, --help  show this help message and exit

Options for subcommand `jobs` (`avocado jobs --help`)::

    positional arguments:
      sub-command
        list            List all known jobs by Avocado
        show            Show details about a specific job. When passing a Job ID,
                        you can use any Job Reference (job_id, "latest", or job
                        results path).
        get-output-files
                        Download output files generated by tests on
                        AVOCADO_TEST_OUTPUTDIR

    optional arguments:
      -h, --help        show this help message and exit

Options for subcommand `list` (`avocado list --help`)::

    positional arguments:
      TEST_REFERENCE        List of test references (aliases or paths)

    optional arguments:
      -h, --help            show this help message and exit
      --write-recipes-to-directory DIRECTORY
                            Writes runnable recipe files to a directory. Valid
                            only when using --resolver.
      --json JSON_FILE      Writes output to a json file.

    filtering parameters:
      -t TAGS, --filter-by-tags TAGS
                            Filter tests based on tags
      --filter-by-tags-include-empty
                            Include all tests without tags during filtering. This
                            effectively means they will be kept in the test suite
                            found previously to filtering.
      --filter-by-tags-include-empty-key
                            Include all tests that do not have a matching key in
                            its key:val tags. This effectively means those tests
                            will be kept in the test suite found previously to
                            filtering.

Options for subcommand `plugins` (`avocado plugins --help`)::

    optional arguments:
      -h, --help            show this help message and exit

Options for subcommand `replay` (`avocado reply --help`)::

    positional arguments:
      SOURCE_JOB_ID  Replays a job, identified by: complete or partial Job ID,
                     "latest" for the latest job, the job results path.

    optional arguments:
      -h, --help     show this help message and exit

Options for subcommand `sysinfo` (`avocado sysinfo --help`)::

    positional arguments:
      sysinfodir  Directory where Avocado will dump sysinfo data. If one is not
                  given explicitly, it will default to a directory named
                  "sysinfo-" followed by a timestamp in the current working
                  directory.

    optional arguments:
      -h, --help  show this help message and exit

Options for subcommand `variants` (`avocado variants --help`)::

    optional arguments:
      -h, --help            show this help message and exit
      --summary SUMMARY     Verbosity of the variants summary. (positive integer -
                            0, 1, ... - or none, brief, normal, verbose, full,
                            max)
      --variants VARIANTS   Verbosity of the list of variants. (positive integer -
                            0, 1, ... - or none, brief, normal, verbose, full,
                            max)
      -c, --contents        [obsoleted by --variants] Shows the node content
                            (variables)
      --json-variants-dump FILE
                            Dump the Variants to a JSON serialized file

    environment view options:
      -d, --debug           Use debug implementation to gather more information.

    tree view options:
      -t, --tree            [obsoleted by --summary] Shows the multiplex tree
                            structure
      -i, --inherit         [obsoleted by --summary] Show the inherited values

    JSON serialized based varianter options:
      --json-variants-load FILE
                            Load the Variants from a JSON serialized file

Options for subcommand `vmimage` (`avocado vmimage --help`)::

    positional arguments:
      {list,get}
        list      List of all downloaded images
        get       Downloads chosen VMimage if it's not already in the cache

    optional arguments:
      -h, --help  show this help message and exit

RUNNING A TEST
==============

The most common use of the `avocado` command line tool is to run a
test::

    $ avocado run examples/tests/sleeptest.py

This command will run the `sleeptest.py` test, as found on the standard
test directories. The output should be similar to::

    JOB ID    : <id>
    JOB LOG   : /home/user/avocado/job-results/job-<date>-<shortid>/job.log
     (1/1) sleeptest.py:SleepTest.test: PASS (1.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.11 s

The test directories will vary depending on you system and installation
method used. Still, it's pretty easy to find that out as shown in the
next section.

DEBUGGING TESTS
===============

When you are developing new tests, frequently you want to look at the
straight output of the job log in the stdout, without having to tail the
job log. In order to do that, you can use `--show=test` to the avocado
test runner::

    $ avocado --show=test run examples/tests/sleeptest.py
    ...
    PARAMS (key=timeout, path=*, default=None) => None
    Test metadata:
      filename: /home/user/avocado/examples/tests/sleeptest.py
      teststmpdir: /var/tmp/avocado_o98elmi0
      workdir: /var/tmp/avocado_iyzcj3hn/avocado_job_mwikfsnl/1-examples_tests_sleeptest.py_SleepTest.test
    START 1-examples/tests/sleeptest.py:SleepTest.test
    DATA (filename=output.expected) => NOT FOUND (data sources: variant, test, file)
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    DATA (filename=output.expected) => NOT FOUND (data sources: variant, test, file)
    DATA (filename=stdout.expected) => NOT FOUND (data sources: variant, test, file)
    DATA (filename=stderr.expected) => NOT FOUND (data sources: variant, test, file)
    PASS 1-examples/tests/sleeptest.py:SleepTest.test
    ...

Let's say you are debugging a test particularly large, with lots of
debug output and you want to reduce this output to only messages with
level 'INFO' and higher. You can set job-log-level to info to reduce the
amount of output.

Edit your `~/.config/avocado/avocado.conf` file and add::

    [job.output]
    loglevel = INFO

Running the same example with this option will give you::

    $ avocado --show=test run examples/tests/sleeptest.py
    ...
    START 1-examples/tests/sleeptest.py:SleepTest.test
    PASS 1-examples/tests/sleeptest.py:SleepTest.test
    ...

The levels you can choose are the levels available in the python logging
system `https://docs.python.org/3/library/logging.html#logging-levels`,
so 'NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', in order
of severity.

As you can see, the UI output is suppressed and only the job log goes to
stdout, making this a useful feature for test development/debugging.

SILENCING RUNNER STDOUT
=======================

You may specify `--show=none`, that means avocado will turn off all
runner stdout.  Note that `--show=none` does not affect on disk
job logs, those continue to be generated normally.

SILENCING SYSINFO REPORT
========================

You may specify `--disable-sysinfo` and avocado will not collect profilers,
hardware details and other system information, inside the job result
directory.

LISTING TESTS
=============

The `avocado` command line tool also has a `list` command, that lists
the known tests in a given path, be it a path to an individual test, or
a path to a directory. If no arguments provided, avocado will inspect
the contents of the test location being used by avocado (if you are in
doubt about which one is that, you may use `avocado config --datadir`).
The output looks like::

    $ avocado list
    INSTRUMENTED /usr/share/doc/avocado/tests/abort.py
    INSTRUMENTED /usr/share/doc/avocado/tests/datadir.py
    INSTRUMENTED /usr/share/doc/avocado/tests/doublefail.py
    INSTRUMENTED /usr/share/doc/avocado/tests/errortest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/failtest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/fiotest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/gendata.py
    INSTRUMENTED /usr/share/doc/avocado/tests/linuxbuild.py
    INSTRUMENTED /usr/share/doc/avocado/tests/multiplextest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/passtest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/skiptest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/whiteboard.py

Here, `INSTRUMENTED` means that the files there are python files with an
avocado test class in them, therefore, that they are what we call
instrumented tests. This means those tests can use all avocado APIs and
facilities. Let's try to list a directory with a bunch of executable
shell scripts::

    $ avocado list examples/wrappers/
    SIMPLE examples/wrappers/bind_cpu0.sh
    SIMPLE examples/wrappers/dummy.sh
    SIMPLE examples/wrappers/ltrace.sh
    SIMPLE examples/wrappers/perf.sh
    SIMPLE examples/wrappers/rr.sh
    SIMPLE examples/wrappers/strace.sh
    SIMPLE examples/wrappers/time.sh
    SIMPLE examples/wrappers/valgrind.sh

Here, `SIMPLE` means that those files are executables, that avocado will
simply execute and return PASS or FAIL depending on their return codes
(PASS -> 0, FAIL -> any integer different than 0). You can also provide
the `--verbose`, or `-V` flag to display files that were detected but
are not avocado tests, along with summary information::

    $ avocado -V list examples/gdb-prerun-scripts/
    Type       Test                                     Tag(s)
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    TEST TYPES SUMMARY
    ==================
    not_a_test: 2

That summarizes the basic commands you should be using more frequently
when you start with avocado. Let's talk now about how avocado stores
test results.

EXPLORING RESULTS
=================

When `avocado` runs tests, it saves all its results on your system::

    JOB ID    : <id>
    JOB LOG   : /home/user/avocado/job-results/job-<date>-<shortid>/job.log

For your convenience, `avocado` maintains a link to the latest job run
(an `avocado run` command in this context), so you can always use
`"latest"` to browse your test results::

    $ ls /home/user/avocado/job-results/latest
    id
    jobdata
    job.log
    results.html
    results.json
    results.tap
    results.xml
    sysinfo
    test-results

The main log file is `job.log`, but every test has its own results
directory::

    $ ls -1 ~/avocado/job-results/latest/test-results/
    1-sleeptest.py:SleepTest.test

Since this is a directory, it should have content similar to::

    $ ls -1 ~/avocado/job-results/latest/test-results/1-sleeptest.py\:SleepTest.test/
    data
    debug.log
    stderr
    stdout
    whiteboard

MULTIPLEX FILE
==============

Avocado has a powerful tool that enables multiple test scenarios to be
run using a single, unmodified test. This mechanism uses a YAML file
called the 'multiplex file', that tells avocado how to multiply all
possible test scenarios automatically.

This is a sample that varies the parameter `sleep_length` through the
scenarios ``/run/short`` (sleeps for 0.5 s), ``/run/medium`` (sleeps for
1 s), ``/run/long`` (sleeps for 5s), ``/run/longest`` (sleeps for 10s).
The YAML file (multiplex file) that produced the output above is::

    !mux
    short:
        sleep_length: 0.5
    medium:
        sleep_length: 1
    long:
        sleep_length: 5
    longest:
        sleep_length: 10

You can execute `sleeptest` in all variations exposed above with::

    $ avocado run examples/tests/sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml

And the output should look like::

    JOB ID    : <id>
    JOB LOG   : /home/user/avocado/job-results/job-<date>-<shortid>/job.log
     (1/4) examples/tests/sleeptest.py:SleepTest.test;run-short-beaf: PASS (0.50 s)
     (2/4) examples/tests/sleeptest.py:SleepTest.test;run-medium-5595: PASS (1.01 s)
     (3/4) examples/tests/sleeptest.py:SleepTest.test;run-long-f397: PASS (5.01 s)
     (4/4) examples/tests/sleeptest.py:SleepTest.test;run-longest-efc4: PASS (10.01 s)
    RESULTS    : PASS 4 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 16.65 s

The test runner supports two kinds of global filters, through the command
line options `--mux-filter-only` and `--mux-filter-out`.
The `mux-filter-only` exclusively includes one or more paths and the
`mux-filter-out` removes one or more paths from being processed.

From the previous example, if we are interested to use the variants
`/run/medium` and `/run/longest`, we do the following command line::

    $ avocado run examples/tests/sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml \
          --mux-filter-only /run/medium /run/longest

And if you want to remove `/small` from the variants created,
we do the following::

    $ avocado run examples/tests/sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml \
          --mux-filter-out /run/medium

Note that both `--mux-filter-only` and `--mux-filter-out` filters can be
arranged in the same command line.

The multiplexer also supports default paths. The base path is ``/run/*``
but it can be overridden by ``--mux-path``, which accepts multiple
arguments. What it does: it splits leaves by the provided paths. Each
query goes one by one through those sub-trees and first one to hit the
match returns the result. It might not solve all problems, but it can
help to combine existing YAML files with your ones::

    qa: # large and complex read-only file, content injected into /qa
        tests:
            timeout: 10
        ...
    my_variants: !mux # your YAML file injected into /my_variants
        short:
            timeout: 1
        long:
            timeout: 1000

You want to use an existing test which uses
``params.get('timeout', '*')``.  Then you can use
``--mux-path '/my_variants/*' '/qa/*'`` and it'll first look in your
variants. If no matches are found, then it would proceed to ``/qa/*``

Keep in mind that only slices defined in mux-path are taken into account
for relative paths (the ones starting with ``*``).


WRAP EXECUTABLE RUN BY TESTS
============================

Avocado allows the instrumentation of executables being run by a test
in a transparent way. The user specifies a script ("the wrapper") to be
used to run the actual program called by the test.

If the instrumentation script is implemented correctly, it should not
interfere with the test behavior. That is, the wrapper should avoid
changing the return status, standard output and standard error messages
of the original executable.

The user can be specific about which program to wrap (with a shell-like
glob), or if that is omitted, a global wrapper that will apply to all
programs called by the test.

So, for every executable run by the test, the program name will be
compared to the pattern to decide whether to wrap it or not. You can
have multiples wrappers and patterns defined.

Examples::

    $ avocado run examples/tests/datadir.py --wrapper examples/wrappers/strace.sh

Any command created by the test datadir will be wrapped on
``strace.sh``. ::

    $ avocado run examples/tests/datadir.py \
            --wrapper examples/wrappers/ltrace.sh:*make \
            --wrapper examples/wrappers/perf.sh:*datadir

Any command that matches the pattern `*make` will be wrapper on
``ltrace.sh`` and the pattern ``*datadir`` will trigger the execution of
``perf.sh``.

LINUX DISTRIBUTION UTILITIES
============================

Avocado has some planned features that depend on knowing the Linux
Distribution being used on the system. The most basic command prints the
detected Linux Distribution::

    $ avocado distro
    Detected distribution: fedora (x86_64) version 21 release 0

Other features are available with the same command when command line
options are given, as shown by the `--help` option.

For instance, it possible to create a so-called "Linux Distribution
Definition" file, by inspecting an installation tree. The installation
tree could be the contents of the official installation ISO or a local
network mirror.

These files let Avocado pinpoint if a given installed package is part of
the original Linux Distribution or something else that was installed
from an external repository or even manually. This, in turn, can help
detecting regressions in base system packages that affected a given test
result.

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

    System wide configuration file
        /etc/avocado/avocado.conf

    Extra configuration files
        /etc/avocado/conf.d/

    User configuration file
        ~/.config/avocado/avocado.conf

BUGS
====

If you find a bug, please report it over our github page as an issue:
https://github.com/avocado-framework/avocado/issues

LICENSE
=======

Avocado is released under GPLv2 (explicit version)
https://gnu.org/licenses/gpl-2.0.html. Even though most of the current
code is licensed under a "and any later version" clause, some parts are
specifically bound to the version 2 of the license and therefore that's
the official license of the project itself. For more details, please see
the LICENSE file in the project source code directory.

MORE INFORMATION
================

For more information please check Avocado's project website, located at
https://avocado-framework.github.io/. There you'll find links to online
documentation, source code and community resources.

AUTHOR
======

Avocado Development Team <avocado-devel@redhat.com>
