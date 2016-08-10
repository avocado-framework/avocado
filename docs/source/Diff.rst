.. _job_diff_:

========
Job Diff
========

Avocado Diff plugin allows users to easily compare several aspects of
two given jobs. The basic usage is::

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

Only sections with different content will be included in the results. You
can also enable/disable those sections with ``--diff-filter``. Please see
``avocado diff --help`` for more information.

Jobs can be identified by the Job ID, by the results directory or by the
key ``latest``. Example::

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

If the option ``--open-browser`` is used without the ``--html``, we will
create a temporary html file.

For those wiling to use a custom diff tool instead of the Avocado Diff tool,
we offer the option ``--create-reports``, so we create two temporary files
with the relevant content. The file names are printed and user can copy/paste
to the custom diff tool command line::

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
