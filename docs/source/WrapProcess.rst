Wrap executables run by tests
=============================

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
-----

This feature is implemented as a plugin, that adds the `--wrapper` option
to the Avocado `run` command.  For a detailed explanation, please consult the
Avocado man page.

Example of a transparent way of running strace as a wrapper::

    #!/bin/sh
    exec strace -ff -o $AVOCADO_TEST_LOGDIR/strace.log -- $@

To have all programs started by ``test.py`` wrapped with ``~/bin/my-wrapper.sh``::

    $ scripts/avocado run --wrapper ~/bin/my-wrapper.sh tests/test.py

To have only ``my-binary`` wrapped with ``~/bin/my-wrapper.sh``::

    $ scripts/avocado run --wrapper ~/bin/my-wrapper.sh:*my-binary tests/test.py

Caveats
-------

* It is not possible to debug with GDB (`--gdb-run-bin`) and use
  wrappers (`--wrapper`) at the same time. These two options are
  mutually exclusive.

* You can only set one (global) wrapper. If you need functionality
  present in two wrappers, you have to combine those into a single
  wrapper script.

* Only executables that are run with the :mod:`avocado.utils.process` APIs
  (and other API modules that make use of it, like mod:`avocado.utils.build`)
  are affected by this feature.
