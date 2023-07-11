import logging
import time

LOG = logging.getLogger(__name__)


def wait_for(func, timeout, first=0.0, step=1.0, text=None, *args, **kwargs):
    """
    Wait until func() evaluates to True.

    If func() evaluates to True before timeout expires, return the
    value of func(). Otherwise return None.

    :param func: The function to be evaluated.
    :param timeout: Timeout in seconds.
    :param first: Time to sleep before the first attempt.
    :param step: Time to sleep between attempts in seconds.
    :param text: Text to print while waiting, for debug purposes.
    :param args: Positional arguments to func.
    :param kwargs: Keyword arguments to func.
    :return: The value returned by func() if it evaluates to True within the timeout, otherwise None.
    """
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