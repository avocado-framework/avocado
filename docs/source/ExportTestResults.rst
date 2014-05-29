.. _export-test-results:

Exporting Test Results
======================

Sometimes you are not only interested in just run the tests,
but to export the test results in an archive, for easy integration with other tools.
For example, you would like to attach the test results to a ticket in Bugzilla.

To create an archive with test results, start Avocado's runner (``avocado run``) and pass the option ``--export``.
After the execution of the tests -- which is actually silent --
you will get a ZIP file with the test results, their logs and other relevant files.

The created ZIP file will be stored in follow format: ``run-YYYY-MM-DD-HH.MM.SS.zip``. For the next section
you will know in details what is inside this archive.

Here is now an example of how to export the execution of three tests: sleeptest, synctest, failtest::

    $ avocado run --export 'sleeptest synctest failtest'
    $ ls run-*.zip
    run-2014-05-29-14.03.47.zip


Archive Content Format
----------------------

The exported Avocado archive is stored in a compressed ZIP file, inside the file
there is a JSON file (``avocado.json``) with test results summary and all the
logs for all running tests. The ZIP archive will always contains::

    run-YYYY-MM-DD-HH.MM.SS.zip
    |-- avocado.json
    |-- debug.log
    |-- <test1>
    |    |-- debug.log
    |    `-- sysinfo/*
    |-- <test2>
    |    |-- debug.log
    |    `-- sysinfo/*
    ...
    |
    `-- <testN>
         |-- debug.log
         `-- sysinfo/*

Test Result JSON format (``avocado.json``)
------------------------------------------

The test results are described inside a JSON file and always follows the format::

    {
      "tests": [
        {
          "test": "<test>",
          "url": "<test_url>",
          "status": "<PASS|ERROR|FAIL|TEST_NA>",
          "time": <time_in_seconds>
        },
        ...
      ],
      "errors": <number-of-errors>,
      "skip": <number-of-test-skipped>,
      "time": <total-time-in-seconds>,
      "debuglog": "<path-to-debug.log>",
      "pass": <number-of-test-passed>,
      "failures": <number-of-test-failures>,
      "total": <number-of-tests>
    }

Real World Example
------------------

For the execution of the three tests above, the content of the ZIP file is::

    run-2014-05-29-14.03.47.zip
    |-- avocado.json
    |-- debug.log
    |-- failtest.1
    |   |-- debug.log
    |   `-- sysinfo
    |       |-- brctl_show
    |       |-- cmdline
    |       |-- cpuinfo
    |       |-- current_clocksource
    |       |-- df_-mP
    |       |-- dmesg_-c
    |       |-- dmidecode
    |       |-- fdisk_-l
    |       |-- gcc_--version
    |       |-- hostname
    |       |-- ifconfig_-a
    |       |-- interrupts
    |       |-- ip_link
    |       |-- ld_--version
    |       |-- lscpu
    |       |-- lspci_-vvnn
    |       |-- meminfo
    |       |-- modules
    |       |-- mount
    |       |-- mounts
    |       |-- numactl_--hardware_show
    |       |-- partitions
    |       |-- scaling_governor
    |       |-- uname_-a
    |       |-- uptime
    |       `-- version
    |-- sleeptest.1
    |   |-- debug.log
    |   `-- sysinfo
    |       |-- brctl_show
    |       |-- cmdline
    |       |-- cpuinfo
    |       |-- current_clocksource
    |       |-- df_-mP
    |       |-- dmesg_-c
    |       |-- dmidecode
    |       |-- fdisk_-l
    |       |-- gcc_--version
    |       |-- hostname
    |       |-- ifconfig_-a
    |       |-- interrupts
    |       |-- ip_link
    |       |-- ld_--version
    |       |-- lscpu
    |       |-- lspci_-vvnn
    |       |-- meminfo
    |       |-- modules
    |       |-- mount
    |       |-- mounts
    |       |-- numactl_--hardware_show
    |       |-- partitions
    |       |-- scaling_governor
    |       |-- uname_-a
    |       |-- uptime
    |       `-- version
    `-- synctest.1
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

and by looking inside the ``avocado.json``, we get::

    {
      "tests": [
        {
          "test": "sleeptest.1",
          "url": "sleeptest",
          "status": "PASS",
          "time": 1.2336459159851
        },
        {
          "test": "synctest.1",
          "url": "synctest",
          "status": "PASS",
          "time": 1.5318291187286
        },
        {
          "test": "failtest.1",
          "url": "failtest",
          "status": "FAIL",
          "time": 0.22931814193726
        }
      ],
      "errors": 0,
      "skip": 0,
      "time": 2.994793176651,
      "debuglog": "\/home\/user\/avocado\/logs\/run-2014-05-29-14.03.47\/debug.log",
      "pass": 2,
      "failures": 1,
      "total": 3
    }
