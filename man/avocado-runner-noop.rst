:title: avocado-runner-noop
:subtitle: nrunner application that performs no action before reporting FINISHED status
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

avocado-runner-noop [-h]
{capabilities,runnable-run,runnable-run-recipe,task-run,task-run-recipe} ...

DESCRIPTION
===========

Sample runner that performs no action before reporting FINISHED status.

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
