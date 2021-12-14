Advanced usage
==============

Custom Runnable Identifier
--------------------------

In some cases, you might have a wrapper as an entry point for the tests, so
Avocado will use only the wrapper as test id. For instance, imagine a Makefile
with some targets ('foo', 'bar') and each target is one test. Having a single
test suite with a test calling `foo`, it will make Avocado print something like
this:


```
JOB ID     : b6e5bdf2c891382bbde7f24e906a168af351154a
JOB LOG    : ~/avocado/job-results/job-2021-09-24T17.39-b6e5bdf/job.log
 (1/1) make: STARTED
 (1/1) make: PASS (2.72 s)
RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
JOB HTML   : ~/avocado/job-results/job-2021-09-24T17.39-b6e5bdf/results.html
JOB TIME   : 5.49 s
```

This is happening because Avocado is using the 'uri' as identifier with in the
current Runnables.

You can change that by setting a custom format with the option
`runner.identifier_format` in you `avocado.conf` file. For instance:

```
[runner]
identifier_format = "{uri}-{args[0]}"
```

With the above adjustment, running the same suite it will produce something
like this:

```
JOB ID     : 577b70b079e9a6f325ff3e73fd9b93f80ee7f221
JOB LOG    : /home/local/avocado/job-results/job-2021-11-23T13.12-577b70b/job.log
 (1/1) "/usr/bin/make-foo": STARTED
 (1/1) "/usr/bin/make-foo": PASS (0.01 s)
RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
JOB HTML   : ~/avocado/job-results/job-2021-11-23T13.12-577b70b/results.html
JOB TIME   : 0.97 s
```

For the `identifier_format` you can use any f-string that it will use `{uri}`,
`{args}` or `{kwargs}`. By default it will use `{uri}`.

When using args, since it is a list, you can use in two different ways:
"{args}" for the entire list, or "{args[n]}" for a specific element inside this
list.  The same is valid when using "{kwargs}". With kwargs, since it is a
dictionary, you have to specify a key as index and then the values are used.

For instance if you have a kwargs value named 'DEBUG', a valid usage could be:
"{kwargs[DEBUG]}" and this will print the current value to this variable (i.e:
True or False).


.. note:: Please, keep in mind this is an experimental feature, and for now you
   have to use it in combination with :ref:`documentation<the_hint_files>`.

.. note:: Also, be aware this feature it is meant to set custom Runnable
   identifiers strings only.

Test Runner Selection
---------------------

To effectively run a job with tests, Avocado makes use of a well
described and pluggable interface.  This means that users can choose
(and developers can write) their own runners.

Runner choices can be seen by running ``avocado plugins``::

  ...
  Plugins that run test suites on a job (runners):
  nrunner nrunner based implementation of job compliant runner
  runner  The conventional test runner

And to select a different test runner, say, the legacy ``runner``::

  avocado run --test-runner=runner ...

Wrap executables run by tests
-----------------------------

Avocado allows the instrumentation of executables being run by a test
in a transparent way. The user specifies a script ("the wrapper") to be
used to run the actual program called by the test.

If the instrumentation script is implemented correctly, it should not
interfere with the test behavior. That is, the wrapper should avoid
changing the return status, standard output and standard error messages
of the original executable.

The user can be specific about which program to wrap (with a shell-like glob),
or if that is omitted, a global wrapper that will apply to all
programs called by the test.

Usage
~~~~~

This feature is implemented as a plugin, that adds the ``--wrapper`` option
to the ``avocado run`` command.  For a detailed explanation, please consult the
Avocado man page.

Example of a transparent way of running strace as a wrapper::

    #!/bin/sh
    exec strace -ff -o $AVOCADO_TEST_LOGDIR/strace.log -- $@

This example file is available at ``examples/wrappers/strace.sh``.

To have all programs started by ``test.py`` wrapped with ``~/bin/my-wrapper.sh``::

    $ avocado run --wrapper ~/bin/my-wrapper.sh tests/test.py

To have only ``my-binary`` wrapped with ``~/bin/my-wrapper.sh``::

    $ avocado run --wrapper ~/bin/my-wrapper.sh:*my-binary tests/test.py

The following is a working example::

    $ avocado run --wrapper examples/wrappers/strace.sh /bin/true

The strace file will be located at Avocado log directory, on
``test-results/1-_bin_true/`` subdirectory.

Caveats
~~~~~~~

* You can only set one (global) wrapper. If you need functionality
  present in two wrappers, you have to combine those into a single
  wrapper script.

* Only executables that are run with the :mod:`avocado.utils.process` APIs
  (and other API modules that make use of it, like mod:`avocado.utils.build`)
  are affected by this feature.
