========================
Avocado development tips
========================

In tree utils
=============

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

Line-profiler
=============

You can measure line-by-line performance by using line_profiler. You can
install it using pip::

    pip install line_profiler

and then simply mark the desired function with `@profile` (no need to import
it from anywhere). Then you execute::

    kernprof -l -v ./scripts/avocado run ...

and when the process finishes you'll see the profiling information. (sometimes
the binary is called `kernprof.py`)

