"""
Traceback standard module plus some additional APIs.
"""
from traceback import format_exception
import logging
import inspect


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
    called_from = inspect.currentframe().f_back
    log.error("Reproduced traceback from: %s:%s",
              called_from.f_code.co_filename, called_from.f_lineno)
    for line in tb_info(exc_info):
        for l in line.splitlines():
            log.error(l)
    log.error('')


def log_message(message, logger='root'):
    """
    Log message to logger.

    :param message: Message
    :param logger: Name of the logger (defaults to root)
    """
    log = logging.getLogger(logger)
    for line in message.splitlines():
        log.error(line)
