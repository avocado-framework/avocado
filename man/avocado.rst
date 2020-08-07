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
accumulated with `autotest` (`http://autotest.github.io`).

`avocado` is also the name of its test runner command line tool,
described in this man page.

For more information about the Avocado project, please check its
website: http://avocado-framework.github.io/

OPTIONS
=======

The following list of options are builtin, application level `avocado`
options. Most other options are implemented via plugins and will depend
on them being loaded (`avocado --help`)::

    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    --config [CONFIG_FILE]
                          Use custom configuration from a file
    --paginator {on,off}  Turn the paginator on/off.
    --show [STREAM[:LVL]]
                          List of comma separated builtin logs, or logging
                          streams optionally followed by LEVEL (DEBUG,INFO,...).
                          Builtin streams are: "test": test output; "debug":
                          tracebacks and other debugging info; "app":
                          application output; "early": early logging of other
                          streams, including test (very verbose); "all": all
                          builtin streams; "none": disables regular output
                          (leaving only errors enabled). By default: 'app'

Real use of avocado depends on running avocado subcommands. This a
typical list of avocado subcommands::

    config              Shows avocado config keys
    diff                Shows the difference between 2 jobs.
    distro              Shows detected Linux distribution
    exec-path           Returns path to avocado bash libraries and exits.
    list                List available tests
    multiplex           Tool to analyze and visualize test variants and params
    plugins             Displays plugin information
    run                 Runs one or more tests (native test, test alias,
                        binary or script)
    sysinfo             Collect system information

To get usage instructions for a given subcommand, run it with `--help`.
Example::

    $ avocado run --help

Options for subcommand `run` (`avocado run --help`)::

    positional arguments:
      TEST_REFERENCE        List of test references (aliases or paths)

    optional arguments:
      -h, --help            show this help message and exit
      -d, --dry-run         Instead of running the test only list them and log
                            their params.
      --force-job-id UNIQUE_JOB_ID
                            Forces the use of a particular job ID. Used internally
                            when interacting with an avocado server. You should
                            not use this option unless you know exactly what
                            you're doing
      --job-results-dir DIRECTORY
                            Forces to use of an alternate job results directory.
      --job-timeout SECONDS
                            Set the maximum amount of time (in SECONDS) that tests
                            are allowed to execute. Values <= zero means "no
                            timeout". You can also use suffixes, like: s
                            (seconds), m (minutes), h (hours).
      --failfast            Enable the job interruption on first failed test.
                            test.
      --keep-tmp            Keep job temporary files (useful for avocado
                            debugging).
      --disable-sysinfo     Enable or disable sysinfo information. Like hardware
                            details, profiles, etc.
      --execution-order {tests-per-variant,variants-per-test}
                            How to iterate through test suite and variants

    output and result format:
      --store-logging-stream [STREAM[:LEVEL] [STREAM[:LEVEL] ...]]
                            Store given logging STREAMs in
                            $JOB_RESULTS_DIR/$STREAM.$LEVEL.
      --html FILE           Enable HTML output to the FILE where the result should
                            be written. The value - (output to stdout) is not
                            supported since not all HTML resources can be embedded
                            into a single file (page resources will be copied to
                            the output file dir)
      --open-browser        Open the generated report on your preferred browser.
                            This works even if --html was not explicitly passed,
                            since an HTML report is always generated on the job
                            results dir. Current: False
      --html-job-result {on,off}
                            Enables default HTML result in the job results
                            directory. File will be located at
                            "html/results.html".
      --journal             Records test status changes (for use with avocado-
                            journal-replay and avocado-server)
      --json FILE           Enable JSON result format and write it to FILE. Use
                            '-' to redirect to the standard output.
      --json-job-result {on,off}
                            Enables default JSON result in the job results
                            directory. File will be named "results.json".
      --tap FILE            Enable TAP result output and write it to FILE. Use '-'
                            to redirect to the standard output.
      --tap-job-result {on,off}
                            Enables default TAP result in the job results
                            directory. File will be named "results.tap".
      --tap-include-logs    Include test logs as comments in TAP output. Defaults
                            to False
      --xunit FILE          Enable xUnit result format and write it to FILE. Use
                            '-' to redirect to the standard output.
      --xunit-job-result {on,off}
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
      -z, --archive         Archive (ZIP) files generated by tests

    output check arguments:
      --output-check-record {none,all,stdout,stderr}
                            Record output streams of your tests to reference files
                            (valid options: none (do not record output streams),
                            all (record both stdout and stderr), stdout (record
                            only stderr), stderr (record only stderr). Current:
                            none
      --disable-output-check
                            Disables test output (stdout/stderr) check. If this
                            option is given, no output will be checked, even if
                            there are reference files present for the test.

    loader options:
      --loaders [LOADERS [LOADERS ...]]
                            Overrides the priority of the test loaders. You can
                            specify either @loader_name or TEST_TYPE. By default
                            it tries all available loaders according to priority
                            set in settings->plugins.loaders.
      --external-runner EXECUTABLE
                            Path to an specific test runner that allows the use of
                            its own tests. This should be used for running tests
                            that do not conform to Avocado' SIMPLE testinterface
                            and can not run standalone. Note: the use of
                            --external-runner overwrites the --loaders to
                            "external_runner"
      --external-runner-chdir {runner,test}
                            Change directory before executing tests. This option
                            may be necessary because of requirements and/or
                            limitations of the external test runner. If the
                            external runner requires to be run from its own base
                            directory,use "runner" here. If the external runner
                            runs tests based on files and requires to be run from
                            the directory where those files are located, use
                            "test" here and specify the test directory with the
                            option "--external-runner-testdir". Defaults to "None"
      --external-runner-testdir DIRECTORY
                            Where test files understood by the external test
                            runner are located in the filesystem. Obviously this
                            assumes and only applies to external test runners that
                            run tests from files

    filtering parameters:
      --filter-by-tags TAGS
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

    test execution inside docker container:
      --docker IMAGE        Name of the docker image torun tests on.
      --docker-cmd CMD      Override the docker command, eg. 'sudo docker' or
                            other base docker options like hypervisor. Default:
                            'docker'
      --docker-options OPT  Extra options for docker run cmd. (see: man docker-
                            run)
      --docker-no-cleanup   Preserve container after test

    keep environment variables:
      --env-keep ENV_KEEP   Keep environment variables in remote executions

    GNU Debugger support:
      --gdb-run-bin EXECUTABLE[:BREAKPOINT]
                            Run a given executable inside the GNU debugger,
                            pausing at a given breakpoint (defaults to "main")
      --gdb-prerun-commands EXECUTABLE:COMMANDS
                            After loading an executable in GDB, but before
                            actually running it, execute the GDB commands in the
                            given file. EXECUTABLE is optional, if omitted
                            COMMANDS will apply to all executables
      --gdb-coredump {on,off}
                            Automatically generate a core dump when the inferior
                            process received a fatal signal such as SIGSEGV or
                            SIGABRT

    job replay:
      --replay REPLAY_JOBID
                            Replay a job identified by its (partial) hash id. Use
                            "--replay latest" to replay the latest job.
      --replay-test-status REPLAY_TESTSTATUS
                            Filter tests to replay by test status
      --replay-ignore REPLAY_IGNORE
                            Ignore variants (variants) and/or configuration
                            (config) from the source job

    resultsdb options:
      --resultsdb-api RESULTSDB_API
                            Specify the resultsdb API url
      --resultsdb-logs RESULTSDB_LOGS
                            Specify the URL where the logs are published

    test execution on a Virtual Machine:
      --vm-domain VM_DOMAIN
                            Specify Libvirt Domain Name
      --vm-hypervisor-uri VM_HYPERVISOR_URI
                            Specify hypervisor URI driver connection. Current:
                            qemu:///system
      --vm-hostname VM_HOSTNAME
                            Specify VM hostname to login. By default Avocado
                            attempts to automatically find the VM IP address.
      --vm-port VM_PORT     Specify the port number to login on VM. Current: 22
      --vm-username VM_USERNAME
                            Specify the username to login on VM
      --vm-password VM_PASSWORD
                            Specify the password to login on VM
      --vm-key-file VM_KEY_FILE
                            Specify an identity file with a private key instead of
                            a password (Example: .pem files from Amazon EC2)
      --vm-cleanup          Restore VM to a previous state, before running tests
      --vm-timeout SECONDS  Amount of time (in seconds) to wait for a successful
                            connection to the virtual machine. Defaults to 120
                            seconds.

    wrapper support:
      --wrapper SCRIPT[:EXECUTABLE]
                            Use a script to wrap executables run by a test. The
                            wrapper is either a path to a script (AKA a global
                            wrapper) or a path to a script followed by colon
                            symbol (:), plus a shell like glob to the target
                            EXECUTABLE. Multiple wrapper options are allowed, but
                            only one global wrapper can be defined.

    yaml to mux options:
      -m [FILE [FILE ...]], --mux-yaml [FILE [FILE ...]]
                            Location of one or more Avocado multiplex (.yaml)
                            FILE(s) (order dependent)
      --mux-filter-only [MUX_FILTER_ONLY [MUX_FILTER_ONLY ...]]
                            Filter only path(s) from multiplexing
      --mux-filter-out [MUX_FILTER_OUT [MUX_FILTER_OUT ...]]
                            Filter out path(s) from multiplexing
      --mux-path [MUX_PATH [MUX_PATH ...]]
                            List of default paths used to determine path priority
                            when querying for parameters
      --mux-inject [MUX_INJECT [MUX_INJECT ...]]
                            Inject [path:]key:node values into the final multiplex
                            tree.

Options for subcommand `config` (`avocado config --help`)::

    optional arguments:
      -h, --help            show this help message and exit
      --datadir             Shows the data directories currently being used by
                            avocado

Options for subcommand `diff` (`avocado diff --help`)::

    positional arguments:
      <JOB>                 A job reference, identified by a (partial) unique ID
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
      --create-reports      Create temporary files with job reports (to be used by
                            other diff tools)

Options for subcommand `distro` (`avocado distro --help`)::

    optional arguments:
      -h, --help            show this help message and exit
      --distro-def-create   Creates a distro definition file based on the path
                            given
      --distro-def-name DISTRO_DEF_NAME
                            Distribution short name
      --distro-def-version DISTRO_DEF_VERSION
                            Distribution major version number
      ---distro-def-release DISTRO_DEF_RELEASE
                            Distribution release version number
      --distro-def-arch DISTRO_DEF_ARCH
                            Primary architecture that the distro targets
      --distro-def-path DISTRO_DEF_PATH
                            Top level directory of the distro installation files
      --distro-def-type {deb,rpm}
                            Distro type (one of: deb, rpm)

Options for subcommand `exec-path` (`avocado exec-path --help`)::

    optional arguments:
      -h, --help  show this help message and exit

Options for subcommand `list` (`avocado list --help`)::

    positional arguments:
      reference             List of test references (aliases or paths). If empty,
                            avocado will list tests on the configured test source,
                            (see 'avocado config --datadir') Also, if there are
                            other test loader plugins active, tests from those
                            plugins might also show up (behavior may vary among
                            plugins)

    optional arguments:
      -h, --help            show this help message and exit
      -V, --verbose         Whether to show extra information (headers and
                            summary). Current: False

    loader options:
      --loaders [LOADERS [LOADERS ...]]
                            Overrides the priority of the test loaders. You can
                            specify either @loader_name or TEST_TYPE. By default
                            it tries all available loaders according to priority
                            set in settings->plugins.loaders.
      --external-runner EXECUTABLE
                            Path to an specific test runner that allows the use of
                            its own tests. This should be used for running tests
                            that do not conform to Avocado' SIMPLE testinterface
                            and can not run standalone. Note: the use of
                            --external-runner overwrites the --loaders to
                            "external_runner"
      --external-runner-chdir {runner,test}
                            Change directory before executing tests. This option
                            may be necessary because of requirements and/or
                            limitations of the external test runner. If the
                            external runner requires to be run from its own base
                            directory,use "runner" here. If the external runner
                            runs tests based on files and requires to be run from
                            the directory where those files are located, use
                            "test" here and specify the test directory with the
                            option "--external-runner-testdir". Defaults to "None"
      --external-runner-testdir DIRECTORY
                            Where test files understood by the external test
                            runner are located in the filesystem. Obviously this
                            assumes and only applies to external test runners that
                            run tests from files

    filtering parameters:
      --filter-by-tags TAGS
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

Options for subcommand `multiplex` (`avocado multiplex --help`)::

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

    environment view options:
      -d, --debug           Debug the multiplex tree.

    tree view options:
      -t, --tree            [obsoleted by --summary] Shows the multiplex tree
                            structure
      -i, --inherit         [obsoleted by --summary] Show the inherited values

    yaml to mux options:
      -m [FILE [FILE ...]], --mux-yaml [FILE [FILE ...]]
                            Location of one or more Avocado multiplex (.yaml)
                            FILE(s) (order dependent)
      --mux-filter-only [MUX_FILTER_ONLY [MUX_FILTER_ONLY ...]]
                            Filter only path(s) from multiplexing
      --mux-filter-out [MUX_FILTER_OUT [MUX_FILTER_OUT ...]]
                            Filter out path(s) from multiplexing
      --mux-path [MUX_PATH [MUX_PATH ...]]
                            List of default paths used to determine path priority
                            when querying for parameters
      --mux-inject [MUX_INJECT [MUX_INJECT ...]]
                            Inject [path:]key:node values into the final multiplex
                            tree.

Options for subcommand `plugins` (`avocado plugins --help`)::

    optional arguments:
      -h, --help            show this help message and exit

Options for subcommand `sysinfo` (`avocado sysinfo --help`)::

    positional arguments:
      sysinfodir  Dir where to dump sysinfo

    optional arguments:
      -h, --help  show this help message and exit

RUNNING A TEST
==============

The most common use of the `avocado` command line tool is to run a
test::

    $ avocado run sleeptest.py

This command will run the `sleeptest.py` test, as found on the standard
test directories. The output should be similar to::

    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
     (1/1) sleeptest.py:SleepTest.test: PASS (1.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 1.11 s

The test directories will vary depending on you system and installation
method used. Still, it's pretty easy to find that out as shown in the
next section.

DEBUGGING TESTS
===============

When you are developing new tests, frequently you want to look at the
straight output of the job log in the stdout, without having to tail the
job log. In order to do that, you can use --show=test to the avocado
test runner::

    $ avocado --show=test run examples/tests/sleeptest.py
    ...
    PARAMS (key=timeout, path=*, default=None) => None
    START 1-sleeptest.py:SleepTest.test
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    Not logging /var/log/messages (lack of permissions)
    PASS 1-sleeptest.py:SleepTest.test
    ...

Let's say you are debugging a test particularly large, with lots of
debug output and you want to reduce this output to only messages with
level 'INFO' and higher. You can set job-log-level to info to reduce the
amount of output.

Edit your `~/.config/avocado/avocado.conf` file and add::

    [job.output]
    loglevel = info

Running the same example with this option will give you::

    $ avocado --show=test run sleeptest.py
    ...
    START 1-sleeptest.py:SleepTest.test
    PASS 1-sleeptest.py:SleepTest.test
    ...

The levels you can choose are the levels available in the python logging
system `https://docs.python.org/2/library/logging.html#logging-levels`,
translated to lowercase strings, so 'notset', 'debug', 'info',
'warning', 'error', 'critical', in order of severity.

As you can see, the UI output is suppressed and only the job log goes to
stdout, making this a useful feature for test development/debugging.

SILENCING RUNNER STDOUT
=======================

You may specify `--show=none`, that means avocado will turn off all
runner stdout.  Note that `--show=none` does not affect on disk
job logs, those continue to be generated normally.

SILENCING SYSINFO REPORT
========================

You may specify --sysinfo=off and avocado will not collect profilers,
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
    INSTRUMENTED /usr/share/doc/avocado/tests/doublefree.py
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
    SIMPLE examples/wrappers/dummy.sh
    SIMPLE examples/wrappers/ltrace.sh
    SIMPLE examples/wrappers/perf.sh
    SIMPLE examples/wrappers/strace.sh
    SIMPLE examples/wrappers/time.sh
    SIMPLE examples/wrappers/valgrind.sh

Here, `SIMPLE` means that those files are executables, that avocado will
simply execute and return PASS or FAIL depending on their return codes
(PASS -> 0, FAIL -> any integer different than 0). You can also provide
the `--verbose`, or `-V` flag to display files that were detected but
are not avocado tests, along with summary information::

    $ avocado list examples/gdb-prerun-scripts/ -V
    Type       Test                                     Tag(s)
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    TEST TYPES SUMMARY
    ==================
    SIMPLE: 0
    INSTRUMENTED: 0
    MISSING: 0
    NOT_A_TEST: 2

That summarizes the basic commands you should be using more frequently
when you start with avocado. Let's talk now about how avocado stores
test results.

EXPLORING RESULTS
=================

When `avocado` runs tests, it saves all its results on your system::

    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log

For your convenience, `avocado` maintains a link to the latest job run
(an `avocado run` command in this context), so you can always use
`"latest"` to browse your test results::

    $ ls /home/<user>/avocado/job-results/latest
    id
    jobdata
    job.log
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
    sysinfo
    whiteboard

MULTIPLEX
=========

Avocado has a powerful tool that enables multiple test scenarios to be
run using a single, unmodified test. This mechanism uses a YAML file
called the 'multiplex file', that tells avocado how to multiply all
possible test scenarios automatically.

A command by the same name, `multiplex`, is available on the `avocado`
command line tool, and enables you to see all the test scenarios that
can be run::

    $ avocado multiplex -m examples/tests/sleeptest.py.data/sleeptest.yaml -c
    Variants generated:

    Variant 1:    /run/short
        /run/short:sleep_length => 0.5

    Variant 2:    /run/medium
        /run/medium:sleep_length => 1

    Variant 3:    /run/long
        /run/long:sleep_length => 5

    Variant 4:    /run/longest
        /run/longest:sleep_length => 10

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

    $ avocado run sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml

And the output should look like::

    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
     (1/4) sleeptest.py:SleepTest.test;1: PASS (0.51 s)
     (2/4) sleeptest.py:SleepTest.test;2: PASS (1.01 s)
     (3/4) sleeptest.py:SleepTest.test;3: PASS (5.02 s)
     (4/4) sleeptest.py:SleepTest.test;4: PASS (10.01 s)
    RESULTS    : PASS 4 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 16.65 s

The `multiplex` plugin and the test runner supports two kinds of global
filters, through the command line options `--mux-filter-only` and
`--mux-filter-out`.
The `mux-filter-only` exclusively includes one or more paths and the
`mux-filter-out` removes one or more paths from being processed.

From the previous example, if we are interested to use the variants
`/run/medium` and `/run/longest`, we do the following command line::

    $ avocado run sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml \
          --mux-filter-only /run/medium /run/longest

And if you want to remove `/small` from the variants created,
we do the following::

    $ avocado run sleeptest.py -m examples/tests/sleeptest.py.data/sleeptest.yaml \
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

    $ avocado run --gdb-run-bin=convert:convert_ppm_to_raw converttest.py

The job starts running just as usual, and so does your test::

    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS     : 1
     (1/1) converttest.py:ConvertTest.test: /

The `convert` executable though, automatically runs inside GDB. Avocado
will stop when the given breakpoint is reached::

    TEST PAUSED because of debugger breakpoint. To DEBUG your application run:
    /home/<user>/avocado/job-results/job-<date>-<shortid>/test-results/converttest.py/data/convert.gdb.sh

    NOTE: please use *disconnect* command in gdb before exiting, or else the debugged process will be KILLED

From this point, you can run the generated script (`convert.gdb.sh`) to
debug you application.

As noted, it is strongly recommended that you *disconnect* from gdb
while your executable is still running. That is, if the executable
finished running while you are debugging it, avocado has no way to know
about its status.

Avocado will automatically send a `continue` command to the debugger
when you disconnect from and exit gdb.

If, for some reason you have a custom GDB, or your system does not put
GDB on what avocado believes to be the standard location
(`/usr/bin/gdb`), you can override that in the section `gdb.paths` of
your documentation::

    [gdb.paths]
    gdb = /usr/bin/gdb
    gdbserver = /usr/bin/gdbserver

So running avocado after setting those will use the appropriate
gdb/gdbserver path.

If you are debugging a special application and need to setup GDB in
custom ways by running GDB commands, you can do that with the
`--gdb-prerun-commands` option::

    $ avocado run --gdb-run-bin=foo:bar --gdb-prerun-commands=/tmp/disable-signals footest.py

In this example, `/tmp/disable-signals` is a simple text file containing
two lines::

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

The user can be specific about which program to wrap (with a shell-like
glob), or if that is omitted, a global wrapper that will apply to all
programs called by the test.

So, for every executable run by the test, the program name will be
compared to the pattern to decide whether to wrap it or not. You can
have multiples wrappers and patterns defined.

Examples::

    $ avocado run datadir.py --wrapper examples/wrappers/strace.sh

Any command created by the test datadir will be wrapped on
``strace.sh``. ::

    $ avocado run datadir.py --wrapper examples/wrappers/ltrace.sh:*make \
                             --wrapper examples/wrappers/perf.sh:*datadir

Any command that matches the pattern `*make` will be wrapper on
``ltrace.sh`` and the pattern ``*datadir`` will trigger the execution of
``perf.sh``.

Note that it is not possible to use ``--gdb-run-bin`` together with
``--wrapper``, they are incompatible.

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

Avocado makes that possible by means of its "external runner" feature.
The most basic way of using it is::

    $ avocado run --external-runner=/path/to/external_runner foo bar baz

In this example, Avocado will report individual test results for tests
`foo`, `bar` and `baz`. The actual results will be based on the return
code of individual executions of `/path/to/external_runner foo`,
`/path/to/external_runner bar` and finally
`/path/to/external_runner baz`.

As another way to explain an show how this feature works, think of the
"external runner" as some kind of interpreter and the individual tests
as anything that this interpreter recognizes and is able to execute. A
UNIX shell, say `/bin/sh` could be considered an external runner, and
files with shell code could be considered tests::

    $ echo "exit 0" > /tmp/pass
    $ echo "exit 1" > /tmp/fail
    $ avocado run --external-runner=/bin/sh /tmp/pass /tmp/fail
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS      : 2
    (1/2) /tmp/pass: PASS (0.01 s)
    (2/2) /tmp/fail: FAIL (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.11 s

This example is pretty obvious, and could be achieved by giving
`/tmp/pass` and `/tmp/fail` shell "shebangs" (`#!/bin/sh`), making
them executable (`chmod +x /tmp/pass /tmp/fail)`, and running them as
"SIMPLE" tests.

But now consider the following example::

    $ avocado run --external-runner=/bin/curl http://local-avocado-server:9405/jobs/ \
                                              http://remote-avocado-server:9405/jobs/
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    TESTS      : 2
    (1/2) http://local-avocado-server:9405/jobs/: PASS (0.02 s)
    (2/2) http://remote-avocado-server:9405/jobs/: FAIL (3.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 3.14 s

This effectively makes `/bin/curl` an "external test runner",
responsible for trying to fetch those URLs, and reporting PASS or FAIL
for each of them.

RECORDING TEST REFERENCE OUTPUT
===============================

As a tester, you may want to check if the output of a given application
matches an expected output. In order to help with this common use case,
we offer the option ``--output-check-record [mode]`` to the test runner.
If this option is used, it will store the stdout or stderr of the
process (or both, if you specified ``all``) being executed to reference
files: ``stdout.expected`` and ``stderr.expected``.

Those files will be recorded in the test data dir. The data dir is in
the same directory as the test source file, named
``[source_file_name.data]``. Let's take as an example the test
``synctest.py``. In a fresh checkout of avocado, you can see::

        examples/tests/synctest.py.data/stderr.expected
        examples/tests/synctest.py.data/stdout.expected

From those 2 files, only stdout.expected is non empty::

    $ cat examples/tests/synctest.py.data/stdout.expected
    PAR : waiting
    PASS : sync interrupted

The output files were originally obtained using the test runner and
passing the option --output-check-record all to the test runner::

    $ avocado run --output-check-record all examples/tests/synctest.py
    JOB ID    : <id>
    JOB LOG   : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
     (1/1) examples/tests/synctest.py:SyncTest.test: PASS (4.00 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 4.10 s

After the reference files are added, the check process is transparent,
in the sense that you do not need to provide special flags to the test
runner. Now, every time the test is executed, after it is done running,
it will check if the outputs are exactly right before considering the
test as PASSed. If you want to override the default behavior and skip
output check entirely, you may provide the flag ``--output-check=off``
to the test runner.

The ``avocado.utils.process`` APIs have a parameter
``allow_output_check`` (defaults to ``all``), so that you can select
which process outputs will go to the reference files, should you chose
to record them. You may choose ``all``, for both stdout and stderr,
``stdout``, for the stdout only, ``stderr``, for only the stderr only,
or ``none``, to allow neither of them to be recorded and checked.

This process works fine also with simple tests, executables that return
0 (PASSed) or != 0 (FAILed). Let's consider our bogus example::

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
    JOB TIME   : 0.11 s

After this is done, you'll notice that a the test data directory
appeared in the same level of our shell script, containing 2 files::

    $ ls output_record.sh.data/
    stderr.expected  stdout.expected

Let's look what's in each of them::

    $ cat output_record.sh.data/stdout.expected
    Hello, world!
    $ cat output_record.sh.data/stderr.expected
    $

Now, every time this test runs, it'll take into account the expected
files that were recorded, no need to do anything else but run the test.

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
detecting regressions in base system pacakges that affected a given test
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
`https://github.com/avocado-framework/avocado/issues`

LICENSE
=======

Avocado is released under GPLv2 (explicit version)
`http://gnu.org/licenses/gpl-2.0.html`. Even though most of the current
code is licensed under a "and any later version" clause, some parts are
specifically bound to the version 2 of the license and therefore that's
the official license of the prject itself. For more details, please see
the LICENSE file in the project source code directory.

MORE INFORMATION
================

For more information please check Avocado's project website, located at
`http://avocado-framework.github.io/`. There you'll find links to online
documentation, source code and community resources.

AUTHOR
======

Avocado Development Team <avocado-devel@redhat.com>
