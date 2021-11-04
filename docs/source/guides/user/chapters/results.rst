Results Specification
=====================

On a machine that executed Avocado, job results are available under
``[job-results]/job-[timestamp]-[short job ID]``, where ``logdir`` is the
configured Avocado logs directory (see the data dir plugin), and the directory
name includes a timestamp, such as ``job-2021-09-28T14.21-e0775d9``. A typical
results directory structure can be seen below ::

    $HOME/avocado/job-results/job-2021-09-28T14.21-e0775d9/
    ├── avocado.core.DEBUG
    ├── id
    ├── jobdata
    │   ├── args.json
    │   ├── cmdline
    │   ├── config
    │   ├── pwd
    │   ├── test_references
    │   └── variants-1.json
    ├── job.log
    ├── results.html
    ├── results.json
    ├── results.tap
    ├── results.xml
    ├── sysinfo
    │   ├── post
    │   │   ├── brctl show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df -mP
    │   │   ├── dmesg
    │   │   ├── dmidecode
    │   │   ├── fdisk -l
    │   │   ├── gcc --version
    │   │   ├── hostname
    │   │   ├── ifconfig -a
    │   │   ├── interrupts
    │   │   ├── ip link
    │   │   ├── journalctl.gz
    │   │   ├── ld --version
    │   │   ├── lscpu
    │   │   ├── lspci -vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mounts
    │   │   ├── numactl --hardware show
    │   │   ├── partitions
    │   │   ├── pci
    │   │   ├── scaling_governor
    │   │   ├── sched_features
    │   │   ├── slabinfo
    │   │   ├── uname -a
    │   │   ├── uptime
    │   │   └── version
    │   ├── pre
    │   │   ├── brctl show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df -mP
    │   │   ├── dmesg
    │   │   ├── dmidecode
    │   │   ├── fdisk -l
    │   │   ├── gcc --version
    │   │   ├── hostname
    │   │   ├── ifconfig -a
    │   │   ├── interrupts
    │   │   ├── ip link
    │   │   ├── ld --version
    │   │   ├── lscpu
    │   │   ├── lspci -vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mounts
    │   │   ├── numactl --hardware show
    │   │   ├── partitions
    │   │   ├── pci
    │   │   ├── scaling_governor
    │   │   ├── sched_features
    │   │   ├── slabinfo
    │   │   ├── uname -a
    │   │   ├── uptime
    │   │   └── version
    │   └── profile
    └── test-results
        ├── 1-examples_tests_sleeptest.py_SleepTest.test
        │   ├── debug.log
        │   └── whiteboard
        ├── 2-examples_tests_sleeptest.py_SleepTest.test
        │   ├── debug.log
        │   └── whiteboard
        └── 3-examples_tests_sleeptest.py_SleepTest.test
            ├── debug.log
            └── whiteboard

From what you can see, the results directory has:

1) A human readable ``id`` in the top level, with the job SHA1.
2) A human readable ``job.log`` in the top level, with human readable logs of
   the task
3) Subdirectory ``jobdata``, that contains machine readable data about the job.
4) A machine readable ``results.xml`` and ``results.json`` in the top level,
   with a summary of the job information in xUnit/json format.
5) A top level ``sysinfo`` dir, with sub directories ``pre``, ``post`` and
   ``profile``, that store sysinfo files pre/post/during job, respectively.
6) Subdirectory ``test-results``, that contains a number of subdirectories
   (filesystem-friendly test ids). Those test ids represent instances of test
   execution results.

Test execution instances specification
--------------------------------------

The instances should have:

1) A top level human readable ``job.log``, with job debug information
2) A ``sysinfo`` subdirectory, with sub directories ``pre``, ``post`` and
   ``profile`` that store sysinfo files pre test, post test and
   profiling info while the test was running, respectively.
3) A ``data`` subdirectory, where the test can output a number of files if necessary.


Test execution environment using the legacy runner
--------------------------------------------------

Each test is executed in a separate process.  Due to how the
underlying operating system works, a lot of the attributes of the
parent process (the Avocado test **runner**) are passed down to the
test process.

On GNU/Linux systems, a child process should be *"an exact duplicate
of the parent process, except"* some items that are documented in
the ``fork(2)`` man page.

.. note:: the non-legacy runner (once known as the N(ext) Runner, AKA
          ``nrunner``) has support for different spawners types (podman,
          process, etc..).  For more information, visit the
          ``nrunner.spawner`` configuration option.

Besides those operating system exceptions, the Avocado test runner
changes the test process in the following ways:

1) The standard input (``STDIN``) is set to a :data:`null device
   <os.devnull>`.  This is truth both for :data:`sys.stdin` and for
   file descriptor ``0``.  Both will point to the same open null
   device file.

2) The standard output (``STDOUT``), as in :data:`sys.stdout`, is
   redirected so that it doesn't interfere with the test runner's own
   output.  All content written to the test's :data:`sys.stdout` will
   be available in the logs under the ``output`` prefix.

   .. warning:: The file descriptor ``1`` (AKA ``/dev/stdout``, AKA
                ``/proc/self/fd/1``, etc) is **not** currently
                redirected for INSTRUMENTED tests.  Any attempt to
                write directly to the file descriptor will interfere
                with the runner's own output stream.  This behavior
                will be addressed in a future version.

3) The standard error (``STDERR``), as in :data:`sys.stderr`, is
   redirected so that it doesn't interfere with the test runner's own
   errors.  All content written to the test's :data:`sys.stderr` will
   be available in the logs under the ``output`` prefix.

   .. warning:: The file descriptor ``2`` (AKA ``/dev/stderr``, AKA
                ``/proc/self/fd/2``, etc) is **not** currently
                redirected for INSTRUMENTED tests.  Any attempt to
                write directly to the file descriptor will interfere
                with the runner's own error stream.  This behavior
                will be addressed in a future version.

4) A custom handler for signal ``SIGTERM`` which will simply raise an
   exception (with the appropriate message) to be handled by the
   Avocado test runner, stating the fact that the test was interrupted
   by such a signal.

   .. tip:: By following the backtrace that is given alongside the in
            the test log (look for ``RuntimeError: Test interrupted
            by SIGTERM``) a user can quickly grasp at which point the
            test was interrupted.

   .. note:: If the test handles ``SIGTERM`` differently and doesn't
             finish the test process quickly enough, it will receive
             then a ``SIGKILL`` which is supposed to definitely end
             the test process.

5) A number of :ref:`environment variables
   <environment-variables-for-tests>` that are set by Avocado, all
   prefixed with ``AVOCADO_``.

If you want to see for yourself what is described here, you may want
to run the example test ``test_env.py`` and examine its log messages.
