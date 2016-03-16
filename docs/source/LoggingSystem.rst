==============
Logging system
==============

This section describes the logging system used in avocado and avocado tests.


Tweaking the UI
===============

Avocado uses python's logging system to produce UI and to store test's output. The system is quite flexible and allows you to tweak the output to your needs either by built-in stream sets, or directly by using the stream name. To tweak them you can use `avocado --show STREAM[:LEVEL][,STREAM[:LEVEL],...]`. Built-in streams with description (followed by list of associated python streams):

:app: The text based UI (avocado.app)
:test: Output of the executed tests (avocado.test, "")
:debug: Additional messages useful to debug avocado (avocado.app.debug)
:remote: Fabric/paramiko debug messages, useful to analyze remote execution (avocado.fabric, paramiko)
:early: Early logging before the logging system is set. It includes the test output and lots of output produced by used libraries. ("", avocado.test)

Additionally you can specify "all" or "none" to enable/disable all of pre-defined streams and you can also supply custom python logging streams and they will be passed to the standard output.

.. warning:: Messages with importance greater or equal WARN in logging stream "avocado.app" are always enabled and they go to the standard error.


Storing custom logs
===================

When you run a test, you can also store custom logging streams into the results directory by `avocado run --store-logging-stream [STREAM[:LEVEL] [STREAM[:LEVEL] ...]]`, which will produce `$STREAM.$LEVEL` files per each (unique) entry in the test results directory.

.. note:: You have to specify separated logging streams. You can't use the built-in streams in this function.

.. note:: Currently the custom streams are stored only per job, not per each individual test.


Paginator
=========

Some subcommands (list, plugins, ...) support "paginator", which, on compatible terminals, basically pipes the colored output to `less` to simplify browsing of the produced output. One can disable it by `--paginator {on|off}`.
