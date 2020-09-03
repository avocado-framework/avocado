Avocado development tips
========================

In tree utils
-------------

You can find handy utils in `avocado.utils.debug`:

measure_duration
----------------

Decorator can be used to print current duration of the executed function
and accumulated duration of this decorated function. It's very handy
when optimizing.

Usage::

    from avocado.utils import debug
    ...
    @debug.measure_duration
    def your_function(...):

During the execution look for::

    PERF: <function your_function at 0x29b17d0>: (0.1s, 11.3s)
    PERF: <function your_function at 0x29b17d0>: (0.2s, 11.5s)


.. note::
   If you are running a test with Avocado, and want to measure the duration
   of a method/function, make sure to enable the `debug` logging stream.
   Example::

    avocado --show avocado.app.debug run examples/tests/assets.py

Line-profiler
-------------

You can measure line-by-line performance by using line_profiler. You can
install it using pip::

    pip install line_profiler

and then simply mark the desired function with `@profile` (no need to import
it from anywhere). Then you execute::

    kernprof -l -v avocado run ...

and when the process finishes you'll see the profiling information. (sometimes
the binary is called `kernprof.py`)

Remote debug with Eclipse
-------------------------

Eclipse is a nice debugging frontend which allows remote debugging. It's very
simple. The only thing you need is Eclipse with pydev plugin. The simplest way
is to use ``pip install pydevd`` and then you set the breakpoint by::

    import pydevd
    pydevd.settrace(host="$IP_ADDR_OF_ECLIPSE_MACHINE", stdoutToServer=False, stderrToServer=False, port=5678, suspend=True, trace_only_current_thread=False, overwrite_prev_trace=False, patch_multiprocessing=False)

Before you run the code, you need to start the Eclipse's debug server. Switch
to `Debug` perspective (you might need to open it first
`Window->Perspective->Open Perspective`). Then start the server from
`Pydev->Start Debug Server`.

Now whenever the pydev.settrace() code is executed, it contacts Eclipse debug
server (port `8000` by default, don't forget to open it) and you can easily
continue in execution. This works on every remote machine which has access to
your Eclipse's port `8000` (you can override it).
