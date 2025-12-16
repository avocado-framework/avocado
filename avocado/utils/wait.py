"""Utilities for waiting for conditions to be met.

This module provides utilities for polling functions until they return
a truthy value or a timeout expires, useful for testing and development
scenarios where you need to wait for system state changes.
"""

import logging
import time

LOG = logging.getLogger(__name__)


# pylint: disable=R0913
def wait_for(func, timeout, first=0.0, step=1.0, text=None, args=None, kwargs=None):
    """Wait until a function returns a truthy value or timeout expires.

    This function repeatedly calls a given function with optional arguments
    until it returns a truthy value (anything that evaluates to True in a
    boolean context) or until the specified timeout expires. It provides
    configurable delays before the first attempt and between subsequent
    attempts, making it useful for polling operations in testing and
    development scenarios.

    The function uses time.monotonic() for reliable timeout calculation that
    is not affected by system clock adjustments. Note that the step sleep
    duration is not interrupted when timeout expires, so actual elapsed time
    may exceed the specified timeout by up to one step duration.

    :param func: Callable to be executed repeatedly until it returns a truthy
                 value. Can be any callable object (function, lambda, method,
                 callable class instance).
    :type func: callable
    :param timeout: Maximum time in seconds to wait for func to return a
                    truthy value. Must be a non-negative number. If timeout
                    expires before func returns truthy, None is returned.
    :type timeout: float or int
    :param first: Time in seconds to sleep before the first attempt to call
                  func. Useful when you know the condition won't be met
                  immediately. Defaults to 0.0 (no initial delay).
    :type first: float or int
    :param step: Time in seconds to sleep between successive calls to func.
                 The actual sleep happens after each failed attempt. Defaults
                 to 1.0 second. Note that this sleep is not interrupted when
                 timeout expires.
    :type step: float or int
    :param text: Optional debug message to log before each attempt. When
                 provided, logs at DEBUG level with elapsed time since start.
                 If None, no logging occurs. Useful for debugging wait
                 operations.
    :type text: str or None
    :param args: Optional list or tuple of positional arguments to pass to
                 func on each call. If None, defaults to empty list.
    :type args: list, tuple, or None
    :param kwargs: Optional dictionary of keyword arguments to pass to func on
                   each call. If None, defaults to empty dict.
    :type kwargs: dict or None
    :return: The truthy return value from func if it succeeds within timeout,
             or None if timeout expires without func returning a truthy value.
             The actual return value from func is preserved (e.g., strings,
             numbers, lists, objects).
    :rtype: Any (return type of func) or None
    :raises: Any exception raised by func will be propagated to the caller.
             No exception handling is performed on func calls.

    Example::

        >>> import os
        >>> # Wait for a file to exist
        >>> wait_for(lambda: os.path.exists("/tmp/myfile"), timeout=30, step=1)
        True
        >>> # Wait for a counter to reach threshold
        >>> counter = [0]
        >>> def check(): counter[0] += 1; return counter[0] >= 5
        >>> wait_for(check, timeout=10, step=0.5)
        True
        >>> # Wait with custom function and arguments
        >>> def check_value(expected, current):
        ...     return current >= expected
        >>> wait_for(check_value, timeout=5, step=0.1, args=[10, 15])
        True
        >>> # Wait with debug logging
        >>> wait_for(lambda: False, timeout=2, step=0.5, text="Waiting for condition")
        None
    """
    args = args or []
    kwargs = kwargs or {}

    start_time = time.monotonic()
    end_time = start_time + timeout

    time.sleep(first)

    while time.monotonic() < end_time:
        if text:
            LOG.debug("%s (%.9f secs)", text, (time.monotonic() - start_time))

        output = func(*args, **kwargs)
        if output:
            return output

        time.sleep(step)

    return None


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("wait")
