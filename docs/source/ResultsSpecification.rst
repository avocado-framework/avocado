=====================
Results Specification
=====================

On a machine that executed tests, job results are available under
``[logdir]/run-[timestamp]``, where ``logdir`` is the configured avocado
logs directory (see the data dir plugin), and the directory name includes
a timestamp, such as ``run-2014-06-12-11.51.59``. A typical
results directory structure can be seen below ::

    run-2014-06-12-11.51.59
    |-- debug.log
    |-- results.json
    |-- results.xml
    `-- sleeptest.1
        |-- debug.log
        `-- sysinfo
            |-- brctl_show
            |-- cmdline
            |-- cpuinfo
            |-- current_clocksource
            |-- df_-mP
            |-- dmesg_-c
            |-- dmidecode
            |-- fdisk_-l
            |-- gcc_--version
            |-- hostname
            |-- ifconfig_-a
            |-- interrupts
            |-- ip_link
            |-- ld_--version
            |-- lscpu
            |-- lspci_-vvnn
            |-- meminfo
            |-- modules
            |-- mount
            |-- mounts
            |-- numactl_--hardware_show
            |-- partitions
            |-- scaling_governor
            |-- uname_-a
            |-- uptime
            `-- version

From what you can see, the results dir has:

1) A human readable 'debug.log' in the top level, with human readable logs of
   the task
2) A machine readable 'results.xml' in the top level, with a summary of the
   job information in xUnit format.
3) Subdirectory with any number of tagged testnames. Those tagged testnames
   represent instances of test execution results.

Test execution instances specification
======================================

The instances should have:

1) A top level debug.log, with test debug information
2) A sysinfo subdirectory, with system information pre-test