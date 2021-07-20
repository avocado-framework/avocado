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

from .test_id import TestID


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
        os.makedirs(task_path, exist_ok=True)
        metadata = {'job_logdir': job.logdir,
                    'job_unique_id': job.unique_id,
                    'base_path': base_path,
                    'task_path': task_path,
                    'time_start': message['time'],
                    'actual_time_start': time.time(),
                    'name': task_id}
        if task.category == 'test':
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

    def handle(self, message, task, job):
        """Logs a textual message to a file.

        This assumes that the log message will not contain a newline, and thus
        one is explicitly added here.
        """
        if task.metadata.get('logfile') is None:
            task.metadata['logfile'] = os.path.join(task.metadata['task_path'],
                                                    'debug.log')
        self._save_message_to_file('debug.log', message['log'], task,
                                   message.get('encoding', None))


class StdoutMessageHandler(BaseRunningMessageHandler):
    """
    Handler for stdout message.

    It will save the stdout to the stdout file in the task directory.

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

    def handle(self, message, task, job):
        self._save_message_to_file('stdout', message['log'], task,
                                   message.get('encoding', None))


class StderrMessageHandler(BaseRunningMessageHandler):
    """
    Handler for stderr message.

    It will save the stderr to the stderr file in the task directory.

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

    def handle(self, message, task, job):
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
            os.makedirs(os.path.dirname(file))
        self._save_message_to_file(filename, message['log'], task,
                                   message.get('encoding', None))
