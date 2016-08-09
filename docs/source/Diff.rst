.. _job_diff_:

========
Job Diff
========

Avocado Diff plugin allows users to easily compare several aspects of
two given jobs.

The basic usage is::

    $ avocado diff 7025aaba 384b949c
    --- 7025aaba9c2ab8b4bba2e33b64db3824810bb5df
    +++ 384b949c991b8ab324ce67c9d9ba761fd07672ff
    @@ -1,15 +1,15 @@
     
     COMMAND LINE
    -/usr/bin/avocado run sleeptest.py
    +/usr/bin/avocado run passtest.py
     
     TOTAL TIME
    -1.00251293182
    +0.000292062759399
     
     VARIANTS
     Variant 1: /
     
     TEST RESULTS
    -1-sleeptest.py:SleepTest.test: PASS
    +1-passtest.py:PassTest.test: PASS
     
     AVOCADO SETTINGS
     [datadir.paths]

Avocado Diff can compare and create an unified diff of:

- Command line.
- Job time.
- Variants and parameters.
- Tests results.
- Configuration.
- Sysinfo pre and post.

You can enable/disable those items with ``--diff-filter``. Avocado Diff
uses ``all,-sysinfo`` as defaults to ``--diff-filter``. Please see
``avocado diff --help`` for more information.

Besides the unified diff, you can also generate an html diff file and,
optionally, open it on your preferred browser::

    $ avocado diff 7025aaba 384b949c --html --open-browser
    --- 7025aaba9c2ab8b4bba2e33b64db3824810bb5df
    +++ 384b949c991b8ab324ce67c9d9ba761fd07672ff
    @@ -1,15 +1,15 @@
     
     COMMAND LINE
    -/usr/bin/avocado run sleeptest.py
    +/usr/bin/avocado run passtest.py
     
     TOTAL TIME
    -1.00251293182
    +0.000292062759399
     
     VARIANTS
     Variant 1: /
     
     TEST RESULTS
    -1-sleeptest.py:SleepTest.test: PASS
    +1-passtest.py:PassTest.test: PASS
     
     AVOCADO SETTINGS
     [datadir.paths]
    --
    /var/tmp/avocado_diff_7025aab_384b949_aeHQ5z.html
