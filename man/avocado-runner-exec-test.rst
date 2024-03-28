:title: avocado-runner-exec-test
:subtitle: nrunner application for standalone executables treated as tests
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

avocado-runner-exec-test [-h]
{capabilities,runnable-run,runnable-run-recipe,task-run,task-run-recipe} ...

DESCRIPTION
===========

This is similar in concept to the Avocado "SIMPLE" test type, in which an
executable returning 0 means that a test passed, and anything else means
that a test failed.

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
