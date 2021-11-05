Basic Operations
================

Job Replay
----------

The process of replaying an Avocado Job is simply about loading the
source Job's configuration and running a new Job based on that
configuration.

For users, this is available as the ``avocado replay`` command.  Its
usage is straightforward.  Suppose you've just run a simple job, also
from the command line, such as::

  $ avocado run /bin/true /bin/false
  JOB ID     : 42c60bea72e6d55756bfc784eb2b354f788541cf
  JOB LOG    : $HOME/avocado/job-results/job-2020-08-13T11.23-42c60be/job.log
   (1/2) /bin/true: PASS (0.01 s)
   (2/2) /bin/false: FAIL: Exited with status: '1', stdout: '' stderr: '' (0.08 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : $HOME/avocado/job-results/job-2020-08-13T11.23-42c60be/results.html
  JOB TIME   : 0.41 s

To run a new job with the configuration used by the previously executed job,
it's possible to simply execute::

  $ avocado replay latest

Resulting in::

  JOB ID     : f3139826f1b169a0b456e0e880ffb83ed26d9858
  SRC JOB ID : latest
  JOB LOG    : $HOME/avocado/job-results/job-2020-08-13T11.24-f313982/job.log
   (1/2) /bin/true: PASS (0.01 s)
   (2/2) /bin/false: FAIL: Exited with status: '1', stdout: '' stderr: '' (0.07 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : $HOME/avocado/job-results/job-2020-08-13T11.24-f313982/results.html
  JOB TIME   : 0.39 s

It's also possible to use the other types of references to jobs, like
the full directory path of the job results, or the Job IDs.  That is,
you can use the same references used in other commands such as
``avocado jobs show``.

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

.. note:: Avocado Diff will ignore files containing non UTF-8 characters, like
          binaries, as an example.

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

If the option ``--open-browser`` is used without the ``--html``, a temporary html file
will be created.

For those wiling to use a custom diff tool instead of the Avocado Diff tool, there is
an option ``--create-reports`` that will, create two temporary files with
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

There are two ways of discovering the tests. One way is to simulate the execution by
using the ``--dry-run`` argument::

    $ avocado run /bin/true --dry-run
    JOB ID     : 0000000000000000000000000000000000000000
    JOB LOG    : /var/tmp/avocado-dry-run-k2i_uiqx/job-2020-09-02T09.09-0000000/job.log
     (1/1) /bin/true: CANCEL: Test cancelled due to --dry-run (0.01 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 1
    JOB HTML   : /var/tmp/avocado-dry-run-k2i_uiqx/job-2020-09-02T09.09-0000000/results.html
    JOB TIME   : 0.29 s

which supports all ``run`` arguments, simulates the run and even lists the test
params.

The other way is to use ``list`` subcommand that lists the discovered tests If
no arguments provided, Avocado lists "default" tests per each plugin.  The
output might look like this::

    $ avocado list --loader
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
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/doc/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/whiteboard.py
    ...

These Python files are considered by Avocado to contain ``INSTRUMENTED`` tests.

Let's now list only the executable shell scripts::

    $ avocado list --loader | grep ^SIMPLE
    SIMPLE       /usr/share/doc/avocado/tests/env_variables.sh
    SIMPLE       /usr/share/doc/avocado/tests/output_check.sh
    SIMPLE       /usr/share/doc/avocado/tests/simplewarning.sh
    SIMPLE       /usr/share/doc/avocado/tests/failtest.sh
    SIMPLE       /usr/share/doc/avocado/tests/passtest.sh

Here, as mentioned before, ``SIMPLE`` means that those files are executables
treated as simple tests. You can also give the ``--verbose`` or ``-V`` flag to
display files that were found by Avocado, but are not considered Avocado
tests::

    $ avocado --verbose list examples/gdb-prerun-scripts/
    Type       Test                                     Tag(s)
    NOT_A_TEST examples/gdb-prerun-scripts/README: Not an INSTRUMENTED (avocado.Test based), PyUNITTEST (unittest.TestCase based) or SIMPLE (executable) test
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1: Not an INSTRUMENTED (avocado.Test based), PyUNITTEST (unittest.TestCase based) or SIMPLE (executable) test
    !GLIB      examples/gdb-prerun-scripts/: No GLib-like tests found
    !GOLANG    examples/gdb-prerun-scripts/: No test matching this reference.
    !ROBOT     examples/gdb-prerun-scripts/: No robot-like tests found
    NOT_A_TEST examples/gdb-prerun-scripts/README: Not a supported test
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1: Not a supported test

    TEST TYPES SUMMARY
    ==================
    !glib: 1
    !golang: 1
    !robot: 1
    not_a_test: 4

Notice that the verbose flag also adds summary information.

.. seealso:: To read more about test discovery, visit the section
  "Understanding the test discovery (Avocado Loaders)".
