"""
Traceback standard module plus some additional APIs.
"""
from traceback import format_exception
import logging


def tb_info(exc_info):
    """
    Prepare traceback info.

    :param exc_info: Exception info produced by sys.exc_info()
    """
    exc_type, exc_value, exc_traceback = exc_info
    return format_exception(exc_type, exc_value, exc_traceback.tb_next)


def prepare_exc_info(exc_info):
    """
    Prepare traceback info.

    :param exc_info: Exception info produced by sys.exc_info()
    """
    return "".join(tb_info(exc_info))


def log_exc_info(exc_info, logger='root'):
    """
    Log exception info to logger_name.

    :param exc_info: Exception info produced by sys.exc_info()
    :param logger: Name of the logger (defaults to root)
    """
    log = logging.getLogger(logger)
    log.error('')
    for line in tb_info(exc_info):
        for l in line.splitlines():
            log.error(l)
    log.error('')
