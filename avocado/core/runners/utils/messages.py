import logging
import sys
import time

from ... import output


def _prepare_message(status_type, additional_info=None):
    """Prepare a message dict with some basic information.

    This will add the keyword 'status' and 'time' to all messages.

    :param status_type: The type of event ('started', 'running',
                         'finished')
    :param: addional_info: Any additional information that you
                           would like to add to the message.
    :type additional_info: dict

    :rtype: dict
    """
    status = {}
    if isinstance(additional_info, dict):
        status = additional_info
    status.update({'status': status_type,
                   'time': time.monotonic()})
    return status


def _get_running_message(msg, message_type):
    """Prepare a message dict with necessary information for specific type.

    :param msg: message data. If the message is str, it will be encoded
                with utf-8.
    :type msg: str, bytes
    :param message_type: specific type of message
    :type message_type: str
    :return: message dict which can be send to avocado server
    :rtype: dict
    """
    message = {'type': message_type, 'log': msg}
    if type(msg) is not bytes:
        msg = msg.encode('utf-8')
        message.update({'log': msg, 'encoding': 'utf-8'})
    return _prepare_message('running', message)


def get_started_message():
    """Creates the started message.

    :return: started message
    :rtype: dict
    """
    return _prepare_message('started')


def get_finished_message(result, fail_reason=None, returncode=None):
    """Creates finished message with  all necessary information.

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
    message = {'result': result}
    if fail_reason is not None:
        message['fail_reason'] = fail_reason
    if returncode is not None:
        message['returncode'] = returncode
    return _prepare_message('finished', message)


def get_running_message():
    """Creates running message without any additional info.

    :return: running message
    :rtype: dict
    """
    return _prepare_message('running')


def get_log_message(message):
    """Creates log message with  all necessary information.

    :param message: log to be sent. The str will be encoded with utf-8.
    :type message: str, bytes
    :return: log message
    :rtype: dict
    """
    return _get_running_message(message, 'log')


def get_stdout_message(message):
    """Creates stdout message with  all necessary information.

    :param message: data to be sent. The str will be encoded with utf-8.
    :type message: str, bytes
    :return: stdout message
    :rtype: dict
    """
    return _get_running_message(message, 'stdout')


def get_stderr_message(message):
    """Creates stderr message with  all necessary information.

    :param message: data to be sent. The str will be encoded with utf-8.
    :type message: str, bytes
    :return: stderr message
    :rtype: dict
    """
    return _get_running_message(message, 'stderr')


def get_whiteboard_message(message):
    """Creates whiteboard message with  all necessary information.

    :param message: data to be sent. The str will be encoded with utf-8.
    :type message: str, bytes
    :return: whiteboard message
    :rtype: dict
    """
    return _get_running_message(message, 'whiteboard')


class RunnerLogHandler(logging.Handler):

    def __init__(self, queue, message_type):
        """
        Runner logger which will put every log to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        super().__init__()
        self.queue = queue
        self.message_type = message_type

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(_get_running_message(msg, self.message_type))


class StreamToQueue:

    def __init__(self,  queue, message_type):
        """
        Runner Stream which will transfer every  to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        self.queue = queue
        self.message_type = message_type

    def write(self, buf):
        self.queue.put(_get_running_message(buf, self.message_type))

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
    log_level = config.get('job.output.loglevel', logging.DEBUG)
    log_handler = RunnerLogHandler(queue, 'log')
    fmt = ('%(asctime)s %(module)-16.16s L%(lineno)-.4d %('
           'levelname)-5.5s| %(message)s')
    formatter = logging.Formatter(fmt=fmt)
    log_handler.setFormatter(formatter)
    log = output.LOG_JOB
    log.addHandler(log_handler)
    log.setLevel(log_level)
    log.propagate = False
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    output.LOG_UI.addHandler(RunnerLogHandler(queue, 'stdout'))

    sys.stdout = StreamToQueue(queue, "stdout")
    sys.stderr = StreamToQueue(queue, "stderr")
