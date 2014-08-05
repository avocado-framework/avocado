"""
funcatexit.py - allow programmer to define multiple exit functions to be
executed upon normal cases termination. Can be used for the environment clean
up functions. The basic idea is like atexit from python libs.
"""

__all__ = ["register", "run_exitfuncs", "unregister"]

from autotest.client.shared import error
import traceback


def run_exitfuncs(env, test_type):
    """
    Run any registered exit functions.
    exithandlers is traversed in reverse order so functions are executed
    last in, first out.

    param env: the global objects used by tests
    param test_type: test type mark for exit functions
    """
    error_message = ""
    if env.data.get("exithandlers__%s" % test_type):
        exithandlers = env.data.get("exithandlers__%s" % test_type)
        while exithandlers:
            func, targs, kargs = exithandlers.pop()
            try:
                func(*targs, **kargs)
            except Exception, details:
                error_message += "Error in %s:" % func.func_name
                error_message += " %s\n" % details
                traceback.print_exc()

    return error_message


def register(env, test_type, func, *targs, **kargs):
    """
    Register a function to be executed upon case termination.
    func is returned to facilitate usage as a decorator.

    param env: the global objects used by tests
    param test_type: test type mark for exit functions
    param func: function to be called at exit
    param targs: optional arguments to pass to func
    param kargs: optional keyword arguments to pass to func
    """
    # Check for unpickable arguments
    if func.func_name not in func.func_globals:
        raise error.TestError("Trying to register function '%s', which is not "
                              "declared at module scope (not in globals). "
                              "Please contact the test developer to fix it."
                              % func)
    for arg in targs:
        if hasattr(arg, '__slots__') and not hasattr(arg, '__getstate__'):
            raise error.TestError("Trying to register exitfunction '%s' with "
                                  "unpickable targument '%s'. Please contact "
                                  "the test developer to fix it."
                                  % (func, arg))
    for key, arg in kargs.iteritems():
        if hasattr(arg, '__slots__') and not hasattr(arg, '__getstate__'):
            raise error.TestError("Trying to register exitfunction '%s' with "
                                  "unpickable kargument '%s=%s'. Please "
                                  "contact the test developer to fix it."
                                  % (func, key, arg))
    exithandlers = "exithandlers__%s" % test_type
    if not env.data.get(exithandlers):
        env.data[exithandlers] = []

    env.data[exithandlers].append((func, targs, kargs))
    return func


def unregister(env, test_type, func, *targs, **kargs):
    """
    Unregister a function to be executed upon case termination.
    func is returned to facilitate usage as a decorator.

    param env: the global objects used by tests
    param test_type: test type mark for exit functions
    param func: function to be called at exit
    param targs: optional arguments to pass to func
    param kargs: optional keyword arguments to pass to func
    """
    exithandlers = "exithandlers__%s" % test_type
    if env.data.get(exithandlers):
        env.data[exithandlers].remove((func, targs, kargs))
    return func
