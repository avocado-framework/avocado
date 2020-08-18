from .utils import json_loads


class StatusMsgMissingDataError(Exception):
    """Status message does not contain the required data."""


class StatusRepo:
    """Maintains tasks' status related data and provides aggregated info."""

    def __init__(self):
        self._data = {}
        self._by_result = {}

    def _set_by_result(self, message):
        """Sets an entry in the aggregate by result.

        For messages that include a "result" key, expected for example,
        from a "finished" status message, this will allow users to query
        for tasks with a given result."""
        result = message.get('result')
        if result not in self._by_result:
            self._by_result[result] = []
        self._by_result[result].append(message['id'])

    def _handle_task_running(self, message):
        self._set_task_data(message)

    def _handle_task_started(self, message):
        if 'output_dir' not in message:
            raise StatusMsgMissingDataError('output_dir')
        self._set_task_data(message)

    def _handle_task_finished(self, message):
        self._set_by_result(message)
        self._set_task_data(message)

    def process_raw_message(self, raw_message):
        raw_message = raw_message.strip()
        message = json_loads(raw_message)
        self.process_message(message)

    def process_message(self, message):
        if 'id' not in message:
            raise StatusMsgMissingDataError('id')

        if message.get('status') == 'running':
            self._handle_task_running(message)
        if message.get('status') == 'started':
            self._handle_task_started(message)
        elif message.get('status') == 'finished':
            self._handle_task_finished(message)

    def _set_task_data(self, message):
        """Appends all data on message to an entry keyed by the task's ID."""
        task_id = message.pop('id')
        if not task_id in self._data:
            self._data[task_id] = []
        self._data[task_id].append(message)

    def get_task_data(self, task_id):
        """Returns all data on a given task, by its ID."""
        return self._data.get(task_id)
