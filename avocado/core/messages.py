# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2021
# Authors: Jan Richter <jarichte@redhat.com>

import os
import time

from avocado.core.nrunner import TASK_DEFAULT_CATEGORY
from avocado.core.output import LOG_UI
from avocado.core.test_id import TestID

DEFAULT_LOG_FILE = 'debug.log'


class BaseMessageHandler:
    """
    Base interface for resolving runner messages.

    This is the interface a job uses to deal with messages from runners.
    """

    def handle(self, message, task, job):
        """
        Handle message from runner.

        :param message: message from runner.
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        :param job: job which task is related to
        :type job: :class:`avocado.core.job.Job`
        """

    def process_message(self, message, task, job):
        """
        It transmits the message to the right handler.

        :param message: message from runner
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        :param job: job which task is related to
        :type job: :class:`avocado.core.job.Job`
        """
        self.handle(message, task, job)


class MessageHandler(BaseMessageHandler):
    """Entry point for handling messages."""

    def __init__(self):
        self._handlers = {'started': [StartMessageHandler()],
                          'finished': [FinishMessageHandler()],
                          'running': [RunningMessageHandler()]}

    def process_message(self, message, task, job):
        for handler in self._handlers.get(message.get('status'), []):
            handler.process_message(message, task, job)


class RunningMessageHandler(BaseMessageHandler):
    """Entry point for handling running messages."""

    def __init__(self):
        self._handlers = {'log': [LogMessageHandler()],
                          'stdout': [StdoutMessageHandler()],
                          'stderr': [StderrMessageHandler()],
                          'whiteboard': [WhiteboardMessageHandler()],
                          'output': [OutputMessageHandler()],
                          'file': [FileMessageHandler()]}

    def process_message(self, message, task, job):
        for handler in self._handlers.get(message.get('type'), []):
            handler.process_message(message, task, job)


class StartMessageHandler(BaseMessageHandler):
    """
    Handler for started message.

    It will create the test base directories and triggers the 'start_test'
    event.

    This have to be triggered when the runner starts the test.

    :param status: 'started'
    :param time: start time of the test
    :type time: float

    example: {'status': 'started', 'time': 16444.819830573}
    """

    def handle(self, message, task, job):
        task_id = TestID.from_identifier(task.identifier)
        base_path = job.test_results_path
        task_path = os.path.join(base_path, task_id.str_filesystem)
        logfile = os.path.join(task_path, DEFAULT_LOG_FILE)
        os.makedirs(task_path, exist_ok=True)
        params = []
        if task.runnable.variant is not None:
            # convert variant into the list of parameters
            params = [param for params in
                      task.runnable.variant.get('variant', [])
                      for param in params[1]]

        open(logfile, 'w').close()
        metadata = {'job_logdir': job.logdir,
                    'job_unique_id': job.unique_id,
                    'base_path': base_path,
                    'logfile':  logfile,
                    'task_path': task_path,
                    'time_start': message['time'],
                    'actual_time_start': time.time(),
                    'name': task_id,
                    'params': params}
        if task.category == TASK_DEFAULT_CATEGORY:
            job.result.start_test(metadata)
            job.result_events_dispatcher.map_method('start_test', job.result,
                                                    metadata)
        task.metadata.update(metadata)


class FinishMessageHandler(BaseMessageHandler):
    """
    Handler for finished message.

    It will report the test status and triggers the 'end_test' event.

    This is triggered when the runner ends the test.

    :param status: 'finished'
    :param result: test result
    :type result: `avocado.core.teststatus.STATUSES`
    :param time: end time of the test
    :type time: float
    :param fail_reason: Optional parameter for brief specification, of the
                       failed result.
    :type fail_reason: string

    example: {'status': 'finished', 'result': 'pass', 'time': 16444.819830573}
    """

    def handle(self, message, task, job):
        message.update(task.metadata)
        message['name'] = TestID.from_identifier(task.identifier)
        message['status'] = message.get('result').upper()

        time_start = message['time_start']
        time_end = message['time']
        time_elapsed = time_end - time_start
        message['time_end'] = time_end
        message['actual_time_end'] = time.time()
        message['time_elapsed'] = time_elapsed

        message['logdir'] = task.metadata['task_path']

        if task.category == 'test':
            job.result.check_test(message)
            job.result_events_dispatcher.map_method('end_test', job.result,
                                                    message)


class BaseRunningMessageHandler(BaseMessageHandler):
    """Base interface for resolving running messages."""

    _tag = b''

    def __init__(self):
        self.line_buffer = b''

    def _split_complete_lines(self, data):
        """
        It will split data into list of lines.

        If the data don't finish with the new line character, the last line is
        marked as incomplete, and it is saved to the line buffer for next usage.

        When the buffer is not empty the buffer will be added at the beginning
        of data.

        :param data: massage log
        :type data: bytes
        :return: list of lines
        """
        data_lines = data.splitlines(True)
        if len(data_lines) <= 1 and not data.endswith(b'\n'):
            self.line_buffer += data
            return []
        else:
            data_lines[0] = self.line_buffer + data_lines[0]
            self.line_buffer = b''
            if not data.endswith(b'\n'):
                self.line_buffer = data_lines.pop()
            return data_lines

    def _save_to_default_file(self, message, task):
        """
        It will save message log into the default log file.

        The default log file is based on `DEFAULT_LOG_FILE` variable and every
        line of log will be saved with prefix based on `_tag` variable

        :param message: message from runner
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        """

        if message.get('encoding'):
            data = message.get('log', b'').splitlines(True)
        else:
            data = self._split_complete_lines(message.get('log', b''))

        if data:
            data = self._tag + self._tag.join(data)
            self._save_message_to_file(DEFAULT_LOG_FILE, data, task,
                                       message.get('encoding'))

    @staticmethod
    def _message_to_line(message, encoding):
        """
        Converts the message to string.

        When the message doesn't end with a new line, the new line is added.

        :param message: message for decoding
        :type message: bytes
        :param encoding: encoding of the message
        :type encoding: str
        :return: encoded message with new line character
        :rtype: str
        """
        message = message.decode(encoding)
        if not message.endswith("\n"):
            message = "%s\n" % message
        return message

    @staticmethod
    def _save_message_to_file(filename, buff, task, encoding=None):
        """
        Method for saving messages into the file

        It can decode and save messages.The message will be decoded when
        encoding is not None. When the decoded message doesn't end with a new
        line the new line will be added. Every message is saved in the append
        mode.

        :param filename: name of the file
        :type filename: str
        :param buff: message to be saved
        :type buff: bytes
        :param task: message related task.
        :type task: :class:`avocado.core.nrunner.Task`
        :param encoding: encoding of buff, default is None
        :type encoding: str
        """

        def _save_to_file(file_name, mode):
            with open(file_name, mode) as fp:
                fp.write(buff)

        file = os.path.join(task.metadata['task_path'], filename)
        if encoding:
            buff = BaseRunningMessageHandler._message_to_line(buff, encoding)
            _save_to_file(file, "a")
        else:
            _save_to_file(file, "ab")


class LogMessageHandler(BaseRunningMessageHandler):
    """
    Handler for log message.

    It will save the log to the debug.log file in the task directory.

    :param status: 'running'
    :param type: 'log'
    :param log: log message
    :type log: string
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'log', 'log': 'log message',
             'time': 18405.55351474}
    """

    _tag = b'[stdlog] '

    def handle(self, message, task, job):
        """Logs a textual message to a file.

        This assumes that the log message will not contain a newline, and thus
        one is explicitly added here.
        """
        if task.metadata.get('logfile') is None:
            task.metadata['logfile'] = os.path.join(task.metadata['task_path'],
                                                    'debug.log')
        self._save_to_default_file(message, task)


class StdoutMessageHandler(BaseRunningMessageHandler):
    """
    Handler for stdout message.

    It will save the stdout to the stdout and debug file in the task directory.

    :param status: 'running'
    :param type: 'stdout'
    :param log: stdout message
    :type log: bytes
    :param encoding: optional value for decoding messages
    :type encoding: str
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'stdout', 'log': 'stdout message',
             'time': 18405.55351474}
    """

    _tag = b'[stdout] '

    def handle(self, message, task, job):
        self._save_to_default_file(message, task)
        self._save_message_to_file('stdout', message['log'], task,
                                   message.get('encoding', None))


class StderrMessageHandler(BaseRunningMessageHandler):
    """
    Handler for stderr message.

    It will save the stderr to the stderr and debug file in the task directory.

    :param status: 'running'
    :param type: 'stderr'
    :param log: stderr message
    :type log: bytes
    :param encoding: optional value for decoding messages
    :type encoding: str
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'stderr', 'log': 'stderr message',
             'time': 18405.55351474}
    """

    _tag = b'[stderr] '

    def handle(self, message, task, job):
        self._save_to_default_file(message, task)
        self._save_message_to_file('stderr', message['log'], task,
                                   message.get('encoding', None))


class WhiteboardMessageHandler(BaseRunningMessageHandler):
    """
    Handler for whiteboard message.

    It will save the stderr to the whiteboard file in the task directory.

    :param status: 'running'
    :param type: 'whiteboard'
    :param log: whiteboard message
    :type log: bytes
    :param encoding: optional value for decoding messages
    :type encoding: str
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'whiteboard',
             'log': 'whiteboard message', 'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        encoding = message.get('encoding', 'utf-8')
        whiteboard = task.metadata.get('whiteboard', '')
        whiteboard += message['log'].decode(encoding)
        task.metadata['whiteboard'] = whiteboard
        self._save_message_to_file('whiteboard',
                                   message['log'],
                                   task,
                                   encoding)


class FileMessageHandler(BaseRunningMessageHandler):
    """
    Handler for file message.

    In task directory will save log into the runner specific file. When the
    file doesn't exist, the file will be created. If the file exist,
    the message data will be appended at the end.

    :param status: 'running'
    :param type: 'file'
    :param path: relative path to the file. The file will be created under
                the Task directory and the absolute path will be created
                as `absolute_task_directory_path/relative_file_path`.
    :type path: string
    :param log: data to be saved inside file
    :type log: bytes
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'file', 'path':'foo/runner.log',
             'log': 'this will be saved inside file',
             'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        filename = os.path.relpath(os.path.join("/", message['path']), "/")
        file = os.path.join(task.metadata['task_path'], filename)
        if not os.path.exists(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)
        self._save_message_to_file(filename, message['log'], task,
                                   message.get('encoding', None))


class OutputMessageHandler(BaseRunningMessageHandler):
    """
    Handler for displaying messages in UI.

    It will show the message content in avocado UI.

    :param status: 'running'
    :param type: 'output'
    :param log: output message
    :type log: bytes
    :param encoding: optional value for decoding messages
    :type encoding: str
    :param time: Time stamp of the message
    :type time: float

    example: {'status': 'running', 'type': 'output',
             'log': 'this is the output', 'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        encoding = message.get('encoding', 'utf-8')
        output = message['log'].decode(encoding)
        task_id = TestID.from_identifier(task.identifier)
        output = "%s: %s" % (task_id, output)
        LOG_UI.debug(output)
