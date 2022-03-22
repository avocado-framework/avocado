import logging
import sys
import time

from avocado.core import output
from avocado.core.streams import BUILTIN_STREAMS


class GenericMessage:
    message_status = None

    @classmethod
    def _prepare_message(cls, additional_info=None):
        """Prepare a message dict with some basic information.

        This will add the keyword 'status' and 'time' to all messages.

        :param: addional_info: Any additional information that you
                               would like to add to the message.
        :type additional_info: dict
        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        status = {}
        if additional_info is not None:
            status = additional_info
        status.update({'status': cls.message_status,
                       'time': time.monotonic()})
        return status

    @classmethod
    def get(cls, **kwargs):
        """Creates message base on it's type with all necessary information.

        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        kwargs = {key: value for (key, value) in kwargs.items()
                  if value is not None}
        return cls._prepare_message(additional_info=kwargs)


class StartedMessage(GenericMessage):
    message_status = 'started'


class RunningMessage(GenericMessage):
    """Creates running message without any additional info."""
    message_status = 'running'


class FinishedMessage(GenericMessage):
    message_status = 'finished'

    @classmethod
    def get(cls, result, fail_reason=None, returncode=None):  # pylint: disable=W0221
        """Creates finished message with all necessary information.

        :param result: test result
        :type result values for the statuses defined in
                     :class: avocado.core.teststatus.STATUSES
        :param fail_reason: parameter for brief specification, of the failed
                            result.
        :type fail_reason: str
        :param returncode: exit status of runner
        :return: finished message
        :rtype: dict
        """
        return super().get(result=result,
                           fail_reason=fail_reason,
                           returncode=returncode)


class GenericRunningMessage(GenericMessage):
    message_status = 'running'
    message_type = None

    @classmethod
    def _get_running_message(cls, msg):
        """Prepare a message dict with necessary information for specific type.

        :param msg: message data. If the message is str, it will be encoded
                    with utf-8.
        :type msg: str, bytes
        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        message = {'type': cls.message_type, 'log': msg}
        if type(msg) is not bytes:
            msg = msg.encode('utf-8')
            message.update({'log': msg, 'encoding': 'utf-8'})
        return message

    @classmethod
    def get(cls, msg, **kwargs):  # pylint: disable=W0221
        """Creates running message with all necessary information.

        :param msg: log of running message
        :type msg: str
        :return: running message
        :rtype: dict
        """
        kwargs.update(cls._get_running_message(msg))
        return super().get(**kwargs)


class LogMessage(GenericRunningMessage):
    message_type = 'log'


class StdoutMessage(GenericRunningMessage):
    """Creates stdout message with all necessary information."""
    message_type = 'stdout'


class StderrMessage(GenericRunningMessage):
    """Creates stderr message with all necessary information."""
    message_type = 'stderr'


class WhiteboardMessage(GenericRunningMessage):
    """Creates whiteboard message with all necessary information."""
    message_type = 'whiteboard'


class OutputMessage(GenericRunningMessage):
    """Creates output message with all necessary information."""
    message_type = 'output'


class FileMessage(GenericRunningMessage):
    """Creates file message with all necessary information."""
    message_type = 'file'

    @classmethod
    def get(cls, msg, path):  # pylint: disable=W0221
        return super().get(msg=msg, path=path)


_supported_types = {LogMessage.message_type: LogMessage,
                    StdoutMessage.message_type: StdoutMessage,
                    StderrMessage.message_type: StderrMessage,
                    WhiteboardMessage.message_type: WhiteboardMessage,
                    OutputMessage.message_type: OutputMessage,
                    FileMessage.message_type: FileMessage}


class RunnerLogHandler(logging.Handler):

    def __init__(self, queue, message_type, kwargs=None):
        """
        Runner logger which will put every log to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        super().__init__()
        self.queue = queue
        self.message = _supported_types[message_type]
        self.kwargs = kwargs or {}

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(self.message.get(msg, **self.kwargs))


class StreamToQueue:

    def __init__(self,  queue, message_type):
        """
        Runner Stream which will transfer data to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        self.queue = queue
        self.message = _supported_types[message_type]

    def write(self, buf):
        self.queue.put(self.message.get(buf))

    def flush(self):
        pass


def start_logging(config, queue):
    """Helper method for connecting the avocado logging with avocado messages.

    It will add the logHandlers to the :class: avocado.core.output loggers,
    which will convert the logs to the avocado messages and sent them to
    processing queue.

    :param config: avocado configuration
    :type config: dict
    :param queue: queue for the runner messages
    :type queue: multiprocessing.SimpleQueue
    """
    def split_loggers_and_levels(enabled_loggers, default_level):
        for logger_level_split in map(lambda x: x.split(':'), enabled_loggers):
            logger_name, *level = logger_level_split
            yield logger_name, level[0] if len(level) > 0 else default_level

    log_level = config.get('job.output.loglevel', logging.DEBUG)
    log_handler = RunnerLogHandler(queue, 'log')
    fmt = ('%(asctime)s %(name)s %(levelname)-5.5s| %(message)s')
    formatter = logging.Formatter(fmt=fmt)
    log_handler.setFormatter(formatter)

    # main log = 'avocado'
    logger = logging.getLogger('avocado')
    logger.addHandler(log_handler)
    logger.setLevel(log_level)
    logger.propagate = False

    # LOG_JOB = 'avocado.test'
    log = output.LOG_JOB
    log.addHandler(log_handler)
    log.setLevel(log_level)
    log.propagate = False

    # LOG_UI = 'avocado.app'
    output.LOG_UI.addHandler(RunnerLogHandler(queue, 'stdout'))

    sys.stdout = StreamToQueue(queue, "stdout")
    sys.stderr = StreamToQueue(queue, "stderr")

    # output custom test loggers
    enabled_loggers = config.get('core.show')
    output_handler = RunnerLogHandler(queue, 'output')
    output_handler.setFormatter(logging.Formatter(fmt='%(name)s: %(message)s'))
    user_streams = [user_streams for user_streams in enabled_loggers
                    if user_streams not in BUILTIN_STREAMS]
    for user_stream, level in split_loggers_and_levels(user_streams,
                                                       log_level):
        custom_logger = logging.getLogger(user_stream)
        custom_logger.addHandler(output_handler)
        custom_logger.setLevel(level)

    # store custom test loggers
    enabled_loggers = config.get('job.run.store_logging_stream')
    for enabled_logger, level in split_loggers_and_levels(enabled_loggers,
                                                          log_level):
        store_stream_handler = RunnerLogHandler(queue, 'file',
                                                {'path': enabled_logger})
        store_stream_handler.setFormatter(formatter)
        output_logger = logging.getLogger(enabled_logger)
        output_logger.addHandler(store_stream_handler)
        output_logger.setLevel(level)

        if not enabled_logger.startswith('avocado.'):
            output_logger.addHandler(log_handler)
            output_logger.propagate = False
