Basic Operations
================

Job Replay
----------

In order to reproduce a given job using the same data, one can use the
``--replay`` option for the ``run`` command, informing the hash id from the
original job to be replayed. The hash id can be partial, as long as the
provided part corresponds to the initial characters of the original job id and
it is also unique enough. Or, instead of the job id, you can use the string
``latest`` and Avocado will replay the latest job executed.

Let's see an example. First, running a simple job with two test references::

     $ avocado run /bin/true /bin/false
     JOB ID     : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.12 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/html/results.html

Now we can replay the job by running::

     $ avocado run --replay 825b86
     JOB ID     : 55a0d10132c02b8cc87deb2b480bfd8abbd956c3
     SRC JOB ID : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/html/results.html

The replay feature will retrieve the original test references, the variants and
the configuration. Let's see another example, now using a mux YAML file::

     $ avocado run /bin/true /bin/false --mux-yaml mux-environment.yaml
     JOB ID     : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/job.log
      (1/4) /bin/true;first-c49a: PASS (0.01 s)
      (2/4) /bin/true;second-f05f: PASS (0.01 s)
      (3/4) /bin/false;first-c49a: FAIL (0.04 s)
      (4/4) /bin/false;second-f05f: FAIL (0.04 s)
     RESULTS    : PASS 2 | ERROR 0 | FAIL 2 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.19 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/html/results.html

We can replay the job as is, using ``$ avocado run --replay latest``, or replay
the job ignoring the variants, as below::

     $ avocado run --replay bd6aa3b --replay-ignore variants
     Ignoring variants from source job with --replay-ignore.
     JOB ID     : d5a46186ee0fb4645e3f7758814003d76c980bf9
     SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.12 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/html/results.html

Also, it is possible to replay only the variants that faced a given result,
using the option ``--replay-test-status``. See the example below::

    $ avocado run --replay bd6aa3b --replay-test-status FAIL
    JOB ID     : 2e1dc41af6ed64895f3bb45e3820c5cc62a9b6eb
    SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
    JOB LOG    : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/job.log
     (1/4) /bin/true;first-c49a: SKIP
     (2/4) /bin/true;second-f05f: SKIP
     (3/4) /bin/false;first-c49a: FAIL (0.03 s)
     (4/4) /bin/false;second-f05f: FAIL (0.04 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 24 | SKIP 24 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.29 s
    JOB HTML   : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/html/results.html

Of which one special example is ``--replay-test-status INTERRUPTED`` or simply
``--replay-resume``, which SKIPs the executed tests and only executes the ones
which were CANCELED or not executed after a CANCELED test. This feature should
work even on hard interruptions like system crash.

When replaying jobs that were executed with the ``--failfast on`` option, you
can disable the ``failfast`` option using ``--failfast off`` in the replay job.

To be able to replay a job, Avocado records the job data in the same job
results directory, inside a subdirectory named ``replay``. If a given job has a
non-default path to record the logs, when the replay time comes, we need to
inform where the logs are. See the example below::

     $ avocado run /bin/true --job-results-dir /tmp/avocado_results/
     JOB ID     : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/job.log
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/html/results.html

Trying to replay the job, it fails::

     $ avocado run --replay f1b1
     can't find job results directory in '$HOME/avocado/job-results'

In this case, we have to inform where the job results directory is located::

     $ avocado run --replay f1b1 --replay-data-dir /tmp/avocado_results
     JOB ID     : 19c76abb29f29fe410a9a3f4f4b66387570edffa
     SRC JOB ID : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/job.log
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/html/results.html

.. _job-diff:

Job Diff
--------

Avocado Diff plugin allows users to easily compare several aspects of two given
jobs. The basic usage is:

.. code-block:: diff

    $ avocado diff 7025aaba 384b949c
    --- 7025aaba9c2ab8b4bba2e33b64db3824810bb5df
    +++ 384b949c991b8ab324ce67c9d9ba761fd07672ff
    @@ -1,15 +1,15 @@
     
     COMMAND LINE
    -/usr/bin/avocado run sleeptest.py
    +/usr/bin/avocado run passtest.py
     
     TOTAL TIME
    -1.00 s
    +0.00 s
     
     TEST RESULTS
    -1-sleeptest.py:SleepTest.test: PASS
    +1-passtest.py:PassTest.test: PASS
     
     ...

Avocado Diff can compare and create an unified diff of:

- Command line.
- Job time.
- Variants and parameters.
- Tests results.
- Configuration.
- Sysinfo pre and post.

Only sections with different content will be included in the results. You can
also enable/disable those sections with ``--diff-filter``. Please see ``avocado
diff --help`` for more information.

Jobs can be identified by the Job ID, by the results directory or by the key
``latest``. Example:

.. code-block:: diff

    $ avocado diff ~/avocado/job-results/job-2016-08-03T15.56-4b3cb5b/ latest
    --- 4b3cb5bbbb2435c91c7b557eebc09997d4a0f544
    +++ 57e5bbb3991718b216d787848171b446f60b3262
    @@ -1,9 +1,9 @@

     COMMAND LINE
    -/usr/bin/avocado run perfmon.py
    +/usr/bin/avocado run passtest.py

     TOTAL TIME
    -11.91 s
    +0.00 s

     TEST RESULTS
    -1-test.py:Perfmon.test: FAIL
    +1-examples/tests/passtest.py:PassTest.test: PASS



Along with the unified diff, you can also generate the html (option ``--html``)
diff file and, optionally, open it on your preferred browser (option
``--open-browser``)::


    $ avocado diff 7025aaba 384b949c --html /tmp/myjobdiff.html
    /tmp/myjobdiff.html

If the option ``--open-browser`` is used without the ``--html``, we will create
a temporary html file.

For those wiling to use a custom diff tool instead of the Avocado Diff tool, we
offer the option ``--create-reports``, so we create two temporary files with
the relevant content. The file names are printed and user can copy/paste to the
custom diff tool command line::

    $ avocado diff 7025aaba 384b949c --create-reports
    /var/tmp/avocado_diff_7025aab_zQJjJh.txt /var/tmp/avocado_diff_384b949_AcWq02.txt

    $ diff -u /var/tmp/avocado_diff_7025aab_zQJjJh.txt /var/tmp/avocado_diff_384b949_AcWq02.txt
    --- /var/tmp/avocado_diff_7025aab_zQJjJh.txt    2016-08-10 21:48:43.547776715 +0200
    +++ /var/tmp/avocado_diff_384b949_AcWq02.txt    2016-08-10 21:48:43.547776715 +0200
    @@ -1,250 +1,19 @@

     COMMAND LINE
     ============
    -/usr/bin/avocado run sleeptest.py
    +/usr/bin/avocado run passtest.py

     TOTAL TIME
     ==========
    -1.00 s
    +0.00 s

    ...


Listing tests
-------------

Avocado can list your tests without run it. This can be handy sometimes.

You have two ways of discovering the tests. You can simulate the execution by
using the ``--dry-run`` argument::

    avocado run /bin/true --dry-run
    JOB ID     : 0000000000000000000000000000000000000000
    JOB LOG    : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/job.log
     (1/1) /bin/true: SKIP
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 1 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.10 s
    JOB HTML   : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/html/results.html

which supports all ``run`` arguments, simulates the run and even lists the test
params.

The other way is to use ``list`` subcommand that lists the discovered tests If
no arguments provided, Avocado lists "default" tests per each plugin.  The
output might look like this::

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
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/whiteboard.py
    ...

These Python files are considered by Avocado to contain ``INSTRUMENTED`` tests.

Let's now list only the executable shell scripts::

    $ avocado list | grep ^SIMPLE
    SIMPLE       /usr/share/doc/avocado/tests/env_variables.sh
    SIMPLE       /usr/share/doc/avocado/tests/output_check.sh
    SIMPLE       /usr/share/doc/avocado/tests/simplewarning.sh
    SIMPLE       /usr/share/doc/avocado/tests/failtest.sh
    SIMPLE       /usr/share/doc/avocado/tests/passtest.sh

Here, as mentioned before, ``SIMPLE`` means that those files are executables
treated as simple tests. You can also give the ``--verbose`` or ``-V`` flag to
display files that were found by Avocado, but are not considered Avocado
tests::

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

Notice that the verbose flag also adds summary information.

.. seealso:: To read more about test discovery, visit the section
  "Understanding the test discovery (Avocado Loaders)".
