Results Specification
=====================

On a machine that executed Avocado, job results are available under
``[job-results]/job-[timestamp]-[short job ID]``, where ``logdir`` is the
configured Avocado logs directory (see the data dir plugin), and the directory
name includes a timestamp, such as ``job-2021-09-28T14.21-e0775d9``. A typical
results directory structure can be seen below ::

    $HOME/avocado/job-results/job-2021-09-28T14.21-e0775d9/
    ├── full.log
    ├── id
    ├── jobdata
    │   ├── args.json
    │   ├── cmdline
    │   ├── config
    │   ├── pwd
    │   ├── test_references
    │   └── variants-1-1.json
    ├── job.log
    ├── results.html
    ├── results.json
    ├── results.tmt
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
        ├── 1-1-_bin_true
        │   ├── debug.log
        │   ├── stderr
        │   └── stdout
        ├── 1-2-_bin_false
        │   ├── debug.log
        │   ├── stderr
        │   └── stdout
        └── by-status
            ├── FAIL
            │   └── 1-2-_bin_false -> ../../1-2-_bin_false
            └── PASS
                └── 1-1-_bin_true -> ../../1-1-_bin_true

From what you can see, the results directory has:

1) A human readable ``id`` in the top level, with the job SHA1.
2) A human readable ``job.log`` in the top level, with human readable logs of
   the task
3) A human readable ``full.log`` in the top level, with human readable logs of
   anything generated inside the job.
4) Subdirectory ``jobdata``, that contains machine readable data about the job.
5) A machine readable ``results.xml`` and ``results.json`` in the top level,
   with a summary of the job information in xUnit/json format.
6) A top level ``sysinfo`` dir, with sub directories ``pre``, ``post`` and
   ``profile``, that store sysinfo files pre/post/during job, respectively.
7) Subdirectory ``test-results``, that contains a number of subdirectories
   (filesystem-friendly test ids). Those test ids represent instances of test
   execution results.

Test execution instances specification
--------------------------------------

The instances should have:

1) A top level human readable ``job.log`` and ``full.log``, with job debug information
2) A ``sysinfo`` subdirectory, with sub directories ``pre``, ``post`` and
   ``profile`` that store sysinfo files pre test, post test and
   profiling info while the test was running, respectively.
3) A ``data`` subdirectory, where the test can output a number of files if necessary.
