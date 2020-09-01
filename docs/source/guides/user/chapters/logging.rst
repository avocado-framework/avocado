Avocado logging system
======================

This section describes the logging system used in Avocado.

Tweaking the UI
---------------

Avocado uses Python's logging system to produce UI and to store test's output.
The system is quite flexible and allows you to tweak the output to your needs
either by built-in stream sets, or directly by using the stream name.

To tweak them you can use::

  $ avocado --show STREAM[:LEVEL][,STREAM[:LEVEL],...]

Built-in streams with description (followed by list of associated Python
streams) are listed below:

:app: The text based UI (avocado.app)
:test: Output of the executed tests (avocado.test, "")
:debug: Messages useful to debug the Avocado Framework (avocado.app.debug)
:early: Early logging before the logging system is set. It includes the test
        output and lots of output produced by used libraries. ("",
        avocado.test)

Additionally you can specify "all" or "none" to enable/disable all of
pre-defined streams and you can also supply custom Python logging streams and
they will be passed to the standard output.

.. warning:: Messages with importance greater or equal WARN in logging stream
  "avocado.app" are always enabled and they go to the standard error output.

Storing custom logs
-------------------

When you run a test, you can also store custom logging streams into the results
directory by running::

  $ avocado run --store-logging-stream [STREAM[:LEVEL][STREAM[:LEVEL] ...]]
 
This will produce `$STREAM.$LEVEL` files per each (unique) entry in the test
results directory.

.. note:: You have to specify separated logging streams. You can't use the
 built-in streams in this function.

.. note:: Currently the custom streams are stored only per job, not per each
 individual test.
