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

"""
Message resolver for runner messages
"""

import abc
import os


class MessageProcessor:
    """Entry point for handling all types of messages."""

    def __init__(self):
        self._handlers = [StartMessageHandler(),
                          RunningMessageHandler(),
                          FinishMessageHandler()]

    def process_message(self, message, task, job):
        """
        It transmits the message to the right handler.

        :param message: message from runner
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        :param job: job which task is related to
        :type job: :class: `avocado.core.job.Job`
        """
        for handler in self._handlers:
            if handler.handle(message, task, job):
                break


class MessageHandler(abc.ABC):
    """
    Base interface for resolving runner messages.

    This is the interface a job uses to deal with messages form runners.
    """

    @abc.abstractmethod
    def handle(self, message, task, job):
        """
        Handle message from runner.

        :param message: message from runner.
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        :param job: job which task is related to
        :type job: :class: `avocado.core.job.Job`
        """

    @staticmethod
    def _save_to_file(filename, buff, mode='a'):
        with open(filename, mode) as fp:
            fp.write("%s\n" % buff)


class StartMessageHandler(MessageHandler):
    """
    Handler for started message. It will create the test base directories
    and triggers the 'start_test' event.

    This is triggered when the runner starts the test.

    The started message properties:
    param status: 'started'
    param time: start time of the test
    type time: float

    example: {'status': 'started', 'time': 16444.819830573}
    """

    def handle(self, message, task, job):
        if message['status'] != 'started':
            return False

        base_path = job.test_results_path
        task_path = os.path.join(base_path, task.identifier.str_filesystem)
        os.makedirs(task_path, exist_ok=True)
        metadata = {'job_logdir': job.logdir, 'job_unique_id': job.unique_id,
                    'base_path': base_path, 'task_path': task_path,
                    'time_start': message['time'], 'name': task.identifier}
        job.result.start_test(metadata)
        job.result_events_dispatcher.map_method('start_test', job.result,
                                                metadata)
        task.metadata.update(metadata)
        return True


class FinishMessageHandler(MessageHandler):
    """
    Handler for finished message. It will report the test status and
    triggers the 'end_test' event.

    This is triggered when the runner ends the test.

    The finished message properties:
    param status: 'finished'
    param result: test result
    type result: `avocado.core.teststatus.user_facing_status`
    param time: end time of the test
    type time: float

    example: {'status': 'finished', 'result': 'pass', 'time': 16444.819830573}
    """

    def handle(self, message, task, job):
        if message['status'] != 'finished':
            return False

        message.update(task.metadata)
        message['name'] = task.identifier
        message['status'] = message.get('result').upper()

        time_start = message['time_start']
        time_end = message['time']
        time_elapsed = time_end - time_start
        message['time_end'] = time_end
        message['time_elapsed'] = time_elapsed

        message['logdir'] = task.metadata['task_path']

        job.result.check_test(message)
        job.result_events_dispatcher.map_method('end_test', job.result, message)
        return True


class RunningMessageHandler(MessageHandler):
    """Entry point for handling running messages."""

    def __init__(self):
        self._running_handlers = [LogMessageHandler(),
                                  StdoutMessageHandler(),
                                  StderrMessageHandler(),
                                  WhiteboardMessageHandler()]

    def handle(self, message, task, job):
        """
        For the messages with status running choose the right handler
        by type.
        """
        if message['status'] != 'running':
            return False

        for handler in self._running_handlers:
            if handler.handle(message, task, job):
                break
        return True


class LogMessageHandler(MessageHandler):
    """
    Handler for log message. It will save the log to the debug.log file in
    the task directory.

    The log message properties:
    param status: 'running'
    param type: 'log'
    param log: log message
    type log: string
    param time: Time stamp of the message
    type time: float

    example: {'status': 'running', 'type': 'log', 'log': 'log message',
             'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        if message.get('type', None) != 'log':
            return False

        task_path = task.metadata['task_path']
        debug = os.path.join(task_path, 'debug.log')
        self._save_to_file(debug, message['log'])
        return True


class StdoutMessageHandler(MessageHandler):
    """
    Handler for stdout message. It will save the stdout to the stdout file in
    the task directory.

    The log message properties:
    param status: 'running'
    param type: 'stdout'
    param log: stdout message
    type log: string
    param time: Time stamp of the message
    type time: float

    example: {'status': 'running', 'type': 'stdout', 'log': 'stdout message',
             'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        if message.get('type', None) != 'stdout':
            return False

        task_path = task.metadata['task_path']
        stdout = os.path.join(task_path, 'stdout')
        self._save_to_file(stdout, message['log'])
        return True


class StderrMessageHandler(MessageHandler):
    """
    Handler for stderr message. It will save the stderr to the stderr file in
    the task directory.

    The log message properties:
    param status: 'running'
    param type: 'stderr'
    param log: stderr message
    type log: string
    param time: Time stamp of the message
    type time: float

    example: {'status': 'running', 'type': 'stderr', 'log': 'stderr message',
             'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        if message.get('type', None) != 'stderr':
            return False

        task_path = task.metadata['task_path']
        stderr = os.path.join(task_path, 'stderr')
        self._save_to_file(stderr, message['log'])
        return True


class WhiteboardMessageHandler(MessageHandler):
    """
    Handler for whiteboard message. It will save the stderr to the whiteboard
    file in the task directory.

    The log message properties:
    param status: 'running'
    param type: 'whiteboard'
    param log: whiteboard message
    type log: string
    param time: Time stamp of the message
    type time: float

    example: {'status': 'running', 'type': 'whiteboard',
             'log': 'whiteboard message', 'time': 18405.55351474}
    """

    def handle(self, message, task, job):
        if message.get('type', None) != 'whiteboard':
            return False

        task_path = task.metadata['task_path']
        whiteboard = os.path.join(task_path, 'whiteboard')
        self._save_to_file(whiteboard, message['log'])
        return True
