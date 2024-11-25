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
   (1/2) /bin/true: STARTED
   (2/2) /bin/false: STARTED
   (1/2) /bin/true: PASS (0.01 s)
   (2/2) /bin/false: FAIL (0.01 s)
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
   (1-2/2) /bin/false: STARTED
   (1-1/2) /bin/true: STARTED
   (1-2/2) /bin/false: FAIL (0.01 s)
   (1-1/2) /bin/true: PASS (0.01 s)
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
     (1/1) /bin/true: STARTED
     (1/1) /bin/true: CANCEL: Test cancelled due to --dry-run (0.00 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 1
    JOB HTML   : /var/tmp/avocado-dry-run-k2i_uiqx/job-2020-09-02T09.09-0000000/results.html
    JOB TIME   : 0.29 s

which supports all ``run`` arguments, simulates the run and even lists the test
params.

The other way is to use ``list`` subcommand that lists the discovered
tests If no arguments provided, Avocado can lists tests discovered by
each discovered plugin.

Let's now list only the executable tests::

    $ avocado list /bin/true /bin/false examples/tests/passtest.py | grep ^exec-test
    exec-test /bin/true
    exec-test /bin/false

Here, as mentioned before, ``exec-test`` means that those files are treated as
executable tests. You can also give the ``--verbose`` or ``-V`` flag to
display files that were found by Avocado, but are not considered Avocado
tests::

    $ avocado -V list examples/gdb-prerun-scripts/
    Type Test Tag(s)

    Resolver             Reference                                Info
    avocado-instrumented examples/gdb-prerun-scripts/README       File name "examples/gdb-prerun-scripts/README" does not end with suffix ".py"
    exec-test            examples/gdb-prerun-scripts/README       File "examples/gdb-prerun-scripts/README" does not exist or is not executable
    golang               examples/gdb-prerun-scripts/README
    python-unittest      examples/gdb-prerun-scripts/README       File name "examples/gdb-prerun-scripts/README" does not end with suffix ".py"
    robot                examples/gdb-prerun-scripts/README       File "examples/gdb-prerun-scripts/README" does not end with ".robot"
    tap                  examples/gdb-prerun-scripts/README       File "examples/gdb-prerun-scripts/README" does not exist or is not executable
    avocado-instrumented examples/gdb-prerun-scripts/pass-sigusr1 File name "examples/gdb-prerun-scripts/pass-sigusr1" does not end with suffix ".py"
    exec-test            examples/gdb-prerun-scripts/pass-sigusr1 File "examples/gdb-prerun-scripts/pass-sigusr1" does not exist or is not executable
    golang               examples/gdb-prerun-scripts/pass-sigusr1
    python-unittest      examples/gdb-prerun-scripts/pass-sigusr1 File name "examples/gdb-prerun-scripts/pass-sigusr1" does not end with suffix ".py"
    robot                examples/gdb-prerun-scripts/pass-sigusr1 File "examples/gdb-prerun-scripts/pass-sigusr1" does not end with ".robot"
    tap                  examples/gdb-prerun-scripts/pass-sigusr1 File "examples/gdb-prerun-scripts/pass-sigusr1" does not exist or is not executable

    TEST TYPES SUMMARY
    ==================

Notice that the verbose flag also adds summary information.

.. seealso:: To read more about test discovery, visit the section
  :ref:`finding_tests`.
