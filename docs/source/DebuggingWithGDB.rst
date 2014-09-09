Debugging with GDB
==================

Avocado has support for transparently debugging binaries inside the GNU
Debugger. This means that any test that uses :mod:`avocado.utils.process`
can transparently inspect processes during test run time.

Usage
-----

This feature is implemented as a plugin, that adds the `--gdb-run-bin` option
to the avocado `run` command. For a detailed explanation please consult the
avocado man page.

Caveats
-------

Currently there is one big caveat when running binaries inside GDB: there's
no way to perform input/output with the process `STDIN`, `STDOUT` and `STDERR`.

There are a couple of reasons for that:

* The process that runs inside GDB has, by default, the same controlling `tty` of the `gdb` process that avocado *initially* runs. When avocado reaches a given  breakpoint, it pauses the tests and allows the user to run another `gdb` process. This second `gdb` process is still connected to the same running process by means of a separate `gdbserver`. At this point, the process is still using the original `tty`.

* Even when using a single `tty`, there's no reliable way of separating multiple streams of data, say from `gdb` and from your application, or even `STDOUT` and `STDERR` streams from either one.

The complete resolution to this caveat suggests the creating of a Pseudo `tty`
for the process running inside GDB, so that the process is the only entity reading
and writing to that `tty`. This will be addressed in future avocado versions.

Workaround
~~~~~~~~~~

If the application you're running as part of your test can read input from alternative
sources (including devices, files or the network) and generate output likewise, then
you should not be further limited.
