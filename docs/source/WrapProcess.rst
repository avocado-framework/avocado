Wrap process in tests
=====================

Avocado allows the instrumentation of applications being
run by a test in a transparent way.

The user specifies a script ("the wrapper") to be used to run the actual
program called by the test.  If the instrument is
implemented correctly, it should not interfere with the test behavior.

So it means that the wrapper should avoid to change the return status,
standard output and standard error messages of the process.

The user can optionally specify a target program to wrap.

Usage
-----

This feature is implemented as a plugin, that adds the `--wrapper` option
to the Avocado `run` command.  For a detailed explanation please consult the     
Avocado man page.

Example of a transparent way of running strace as a wrapper::

    #!/bin/sh
    exec strace -ff -o $AVOCADO_TEST_LOGDIR/strace.log -- $@


Now you can run::

    # run all programs started by test.py with ~/bin/my-wrapper.sh
    $ scripts/avocado run --wrapper ~/bin/my-wrapper.sh tests/test.py

    # run only my-binary (if/when started by a test) with ~/bin/my-wrapper.sh
    $ scripts/avocado run --wrapper ~/bin/my-wrapper.sh:my-binary tests/test.py


Caveats
-------

* It is not possible to debug with GDB (`--gdb-run-bin`) and use
  wrappers (`--wrapper`), both options together are incompatible.

* You cannot set multiples (global) wrappers
  -- like `--wrapper foo.sh --wrapper bar.sh` -- it will trigger an error.
  You should use a single script that performs both things
  you are trying to achieve.

* The only process that can be wrapper are those that uses the Avocado
  module `avocado.utils.process` and the modules that make use of it,
  like `avocado.utils.build` and so on.

* If paths are not absolute, then the process name matches with the base name,
  so `--wrapper foo.sh:make` will match `/usr/bin/make`, `/opt/bin/make`
  and  `/long/path/to/make`.

*  When you use a relative path to a script, it will use the current path
   of the running Avocado program.
   Example: If I'm running Avocado on `/home/user/project/avocado`,
   then `avocado run --wrapper examples/wrappers/strace.sh datadir`  will
   set the wrapper to `/home/user/project/avocado/examples/wrappers/strace.sh`
