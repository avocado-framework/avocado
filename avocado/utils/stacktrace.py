"""
Traceback standard module plus some additional APIs.
"""
from traceback import format_exception
import logging
import inspect
import pickle
from pprint import pformat


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


def analyze_unpickable_item(path_prefix, obj):
    """
    Recursive method to obtain unpickable objects along with location

    :param path_prefix: Path to this object
    :param obj: The sub-object under introspection
    :return: [($path_to_the_object, $value), ...]
    """
    _path_prefix = path_prefix
    try:
        if hasattr(obj, "iteritems"):
            subitems = obj.iteritems()
            path_prefix += "[%s]"
        elif hasattr(obj, "items"):
            subitems = obj.items()
            path_prefix += "[%s]"
        elif isinstance(obj, list):
            subitems = enumerate(obj)
            path_prefix += "[%s]"
        elif hasattr(obj, "__iter__"):
            subitems = enumerate(obj.__iter__())
            path_prefix += "<%s>"
        elif hasattr(obj, "__dict__"):
            subitems = obj.__dict__.iteritems()
            path_prefix += ".%s"
        else:
            return [(path_prefix, obj)]
    except Exception:
        return [(path_prefix, obj)]
    unpickables = []
    for key, value in subitems:
        try:
            pickle.dumps(value)
        except Exception:
            ret = analyze_unpickable_item(path_prefix % key, value)
            if ret:
                unpickables.extend(ret)
    if not unpickables:
        return [(_path_prefix, obj)]
    return unpickables


def str_unpickable_object(obj):
    """
    Return human readable string identifying the unpickable objects

    :param obj: The object for analysis
    :raise ValueError: In case the object is pickable
    """
    try:
        pickle.dumps(obj)
    except Exception:
        pass
    else:
        raise ValueError("This object is pickable:\n%s" % pformat(obj))
    unpickables = analyze_unpickable_item("this", obj)
    return ("Unpickable object in:\n  %s\nItems causing troubles:\n  "
            % "\n  ".join(pformat(obj).splitlines()) +
            "\n  ".join("%s => %s" % obj for obj in unpickables))
