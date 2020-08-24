from .utils import json_loads


class StatusMsgMissingDataError(Exception):
    """Status message does not contain the required data."""


class StatusRepo:
    """Maintains tasks' status related data and provides aggregated info."""

    def __init__(self):
        #: Contains all reveived messages by a given task (by its ID)
        self._all_data = {}
        #: Contains the task IDs keyed by the result received
        self._by_result = {}

    def _handle_task_finished(self, message):
        self._set_by_result(message)
        self._set_task_data(message)

    def _handle_task_started(self, message):
        if 'output_dir' not in message:
            raise StatusMsgMissingDataError('output_dir')
        self._set_task_data(message)

    def _set_by_result(self, message):
        """Sets an entry in the aggregate by result.

        For messages that include a "result" key, expected for example,
        from a "finished" status message, this will allow users to query
        for tasks with a given result."""
        result = message.get('result')
        if result not in self._by_result:
            self._by_result[result] = []
        if message['id'] not in self._by_result[result]:
            self._by_result[result].append(message['id'])

    def _set_task_data(self, message):
        """Appends all data on message to an entry keyed by the task's ID."""
        task_id = message.pop('id')
        if not task_id in self._all_data:
            self._all_data[task_id] = []
        self._all_data[task_id].append(message)

    def get_task_data(self, task_id):
        """Returns all data on a given task, by its ID."""
        return self._all_data.get(task_id)

    def get_latest_task_data(self, task_id):
        """Returns the latest data on a given task, by its ID."""
        task_data = self._all_data.get(task_id)
        if task_data is None:
            return None
        return task_data[-1]

    def process_message(self, message):
        if 'id' not in message:
            raise StatusMsgMissingDataError('id')

        handlers = {'started': self._handle_task_started,
                    'finished': self._handle_task_finished}
        meth = handlers.get(message.get('status'),
                            self._set_task_data)
        meth(message)

    def process_raw_message(self, raw_message):
        raw_message = raw_message.strip()
        message = json_loads(raw_message)
        self.process_message(message)
