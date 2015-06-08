=====================
Results Specification
=====================

On a machine that executed tests, job results are available under
``[job-results]/job-[timestamp]-[short job ID]``, where ``logdir`` is the configured Avocado
logs directory (see the data dir plugin), and the directory name includes
a timestamp, such as ``job-2014-08-12T15.44-565e8de``. A typical
results directory structure can be seen below ::

    $HOME/avocado/job-results/job-2014-08-13T00.45-4a92bc0/
    ├── id
    ├── job.log
    ├── results.json
    ├── results.xml
    ├── sysinfo
    │   ├── post
    │   │   ├── brctl_show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df_-mP
    │   │   ├── dmesg_-c
    │   │   ├── dmidecode
    │   │   ├── fdisk_-l
    │   │   ├── gcc_--version
    │   │   ├── hostname
    │   │   ├── ifconfig_-a
    │   │   ├── interrupts
    │   │   ├── ip_link
    │   │   ├── ld_--version
    │   │   ├── lscpu
    │   │   ├── lspci_-vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mount
    │   │   ├── mounts
    │   │   ├── numactl_--hardware_show
    │   │   ├── partitions
    │   │   ├── scaling_governor
    │   │   ├── uname_-a
    │   │   ├── uptime
    │   │   └── version
    │   └── pre
    │       ├── brctl_show
    │       ├── cmdline
    │       ├── cpuinfo
    │       ├── current_clocksource
    │       ├── df_-mP
    │       ├── dmesg_-c
    │       ├── dmidecode
    │       ├── fdisk_-l
    │       ├── gcc_--version
    │       ├── hostname
    │       ├── ifconfig_-a
    │       ├── interrupts
    │       ├── ip_link
    │       ├── ld_--version
    │       ├── lscpu
    │       ├── lspci_-vvnn
    │       ├── meminfo
    │       ├── modules
    │       ├── mount
    │       ├── mounts
    │       ├── numactl_--hardware_show
    │       ├── partitions
    │       ├── scaling_governor
    │       ├── uname_-a
    │       ├── uptime
    │       └── version
    └── test-results
        └── tests
            ├── sleeptest.py.long
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            ├── sleeptest.py.medium
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            └── sleeptest.py.short
                ├── data
                ├── debug.log
                └── sysinfo
                    ├── post
                    └── pre
    
    20 directories, 59 files


From what you can see, the results dir has:

1) A human readable ``id`` in the top level, with the job SHA1.
2) A human readable ``job.log`` in the top level, with human readable logs of
   the task
3) A machine readable ``results.xml`` in the top level, with a summary of the
   job information in xUnit format.
4) A top level ``sysinfo`` dir, with sub directories ``pre`` and ``post``, that store
   sysinfo files pre job and post job, respectively.
5) Subdirectory ``test-results``, that contains a number of subdirectories
   (tagged testnames). Those tagged testnames represent instances of test
   execution results.

Test execution instances specification
======================================

The instances should have:

1) A top level human readable ``test.log``, with test debug information
2) A ``sysinfo`` subdir, with sub directories ``pre`` and ``post``, that store
   sysinfo files pre test and post test, respectively.
3) A ``data`` subdir, where the test can output a number of files if necessary.
