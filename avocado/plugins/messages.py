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
    """Entry point for handling all types of messages"""

    def __init__(self):
        self._handlers = [StartMessageHandler(),
                          RunningMessageProcessor(),
                          FinishMessageHandler()]

    def process_message(self, message, task, job):
        for handler in self._handlers:
            if handler.handle(message, task, job):
                break


class MessageHandler(metaclass=abc.ABCMeta):
    """Base interface for resolving runner messages.

    This is the interface a job uses to deal with messages form runners.
    """

    @abc.abstractmethod
    def handle(self, message, task, job):
        """Handle message from runner.

        :param message: message from runner.
        :type message: dict
        :param task: runtime_task which message is related to
        :type task: :class:`avocado.core.nrunner.Task`
        :param job: job which task is related to
        :type job: :class: `avocado.core.job.Job`
        """


class StartMessageHandler(MessageHandler):

    def handle(self, message, task, job):
        if message['status'] == 'started':
            base_path = os.path.join(job.logdir, 'test-results')
            task_path = os.path.join(base_path, task.identifier.str_filesystem)
            os.makedirs(task_path, exist_ok=True)
            early_state = {'name': task.identifier, 'job_logdir': job.logdir,
                           'job_unique_id': job.unique_id,
                           'base_path': base_path, 'task_path': task_path,
                           'time_start': message['time']}
            job.result.start_test(early_state)
            job.result_events_dispatcher.map_method('start_test', job.result,
                                                    early_state)
            task.data.update(early_state)
            return True
        return False


class FinishMessageHandler(MessageHandler):

    def handle(self, message, task, job):
        if message['status'] == 'finished':
            message.update(task.data)
            message['status'] = message.get('result').upper()

            time_start = message['time_start']
            time_end = message['time']
            time_elapsed = time_end - time_start
            message['time_end'] = time_end
            message['time_elapsed'] = time_elapsed

            # fake log dir, needed by some result plugins such as HTML
            if 'logdir' not in message:
                message['logdir'] = ''

            job.result.check_test(message)
            job.result_events_dispatcher.map_method('end_test',
                                                    job.result,
                                                    message)
            return True
        return False


class RunningMessageProcessor(MessageHandler):

    def __init__(self):
        self._running_handlers = [LogMessageHandler()]

    def handle(self, message, task, job):
        if message['status'] == 'running':
            for handler in self._running_handlers:
                if handler.handle(message, task, job):
                    break
            return True
        return False


class LogMessageHandler(MessageHandler):

    def handle(self, message, task, job):
        if message.get('type', None) == 'log':
            task_path = task.data['task_path']
            debug = os.path.join(task_path, 'debug.log')
            with open(debug, 'a') as fp:
                fp.write("%s\n" % message['log'])
            return True
        return False
