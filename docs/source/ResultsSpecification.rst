=====================
Results Specification
=====================

On a machine that executed tests, job results are available under
``[logdir]/run-[timestamp]``, where ``logdir`` is the configured avocado
logs directory (see the data dir plugin), and the directory name includes
a timestamp, such as ``run-2014-06-13-19.30.43``. A typical
results directory structure can be seen below ::

    run-2014-06-13-19.30.43
    |-- debug.log
    |-- results.json
    |-- results.xml
    |-- sleeptest.1
    |   |-- debug.log
    |   `-- sysinfo
    |       |-- post
    |       `-- pre
    |-- sysinfo
    |   |-- post
    |   `-- pre


From what you can see, the results dir has:

1) A human readable 'debug.log' in the top level, with human readable logs of
   the task
2) A machine readable 'results.xml' in the top level, with a summary of the
   job information in xUnit format.
3) A top level 'sysinfo' dir, with sub directories 'pre' and 'post', that store
   sysinfo files pre job and post job, respectively.
4) Subdirectory with any number of tagged testnames. Those tagged testnames
   represent instances of test execution results.

Test execution instances specification
======================================

The instances should have:

1) A top level human readable debug.log, with test debug information
2) A 'sysinfo' subdir, with sub directories 'pre' and 'post, that store
   sysinfo files pre test and post test, respectively.
