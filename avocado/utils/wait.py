import logging
import time

log = logging.getLogger('avocado.test')


def wait_for(func, timeout, first=0.0, step=1.0, text=None, args=None, kwargs=None):
    """
    Wait until func() evaluates to True.

    If func() evaluates to True before timeout expires, return the
    value of func(). Otherwise return None.

    :param timeout: Timeout in seconds
    :param first: Time to sleep before first attempt
    :param step: Time to sleep between attempts in seconds
    :param text: Text to print while waiting, for debug purposes
    :param args: Positional arguments to func
    :param kwargs: Keyword arguments to func
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    start_time = time.monotonic()
    end_time = start_time + timeout

    time.sleep(first)

    while time.monotonic() < end_time:
        if text:
            log.debug("%s (%f secs)", text, (time.monotonic() - start_time))

        output = func(*args, **kwargs)
        if output:
            return output

        time.sleep(step)

    return None
