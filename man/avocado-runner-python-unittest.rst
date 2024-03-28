:title: avocado-runner-python-unittest
:subtitle: nrunner application for Python unittests
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

avocado-runner-python-unittest [-h]
{capabilities,runnable-run,runnable-run-recipe,task-run,task-run-recipe} ...

DESCRIPTION
===========

The runnable uri is used as the test name that the native unittest
TestLoader will use to find the test. A native unittest test runner
(TextTestRunner) will be used to execute the test.

OPTIONS
=======

Positional arguments::

    capabilities        Outputs capabilities, including runnables and commands
    runnable-run        Runs a runnable definition from arguments
    runnable-run-recipe Runs a runnable definition from a recipe
    task-run            Runs a task from arguments
    task-run-recipe     Runs a task from a recipe

Optional arguments::

    -h, --help          Show this help message and exit
