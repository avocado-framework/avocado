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

