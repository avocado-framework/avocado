from .utils import json_loads


class StatusMsgMissingDataError(Exception):
    """Status message does not contain the required data."""


class StatusRepo:
    """Maintains tasks' status related data and provides aggregated info."""

    def __init__(self):
        #: Contains all received messages by a given task (by its ID)
        self._all_data = {}
        #: Contains the most up to date status of a task, and the time
        #: it was set in a tuple (status, time).  This is keyed
        #: by the task ID, and the most up to date status is determined by
        #: the "timestamp" in the "time" field of the message, that is,
        #: it's *not* based by the order it was received.
        self._status = {}
        #: Contains a global journal of status updates to be picked, each
        #: entry containing a tuple with (task_id, status, time).  It discards
        #: status that have been superseded by newer status.
        self._status_journal_summary = []
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
        if task_id not in self._all_data:
            self._all_data[task_id] = []
        self._all_data[task_id].append(message)

    def get_all_task_data(self, task_id):
        """Returns all data on a given task, by its ID."""
        return self._all_data.get(task_id)

    def get_task_data(self, task_id, index):
        """Returns the data on the index of a given task, by its ID."""
        task_data = self._all_data.get(task_id)
        return task_data[index]

    def get_latest_task_data(self, task_id):
        """Returns the latest data on a given task, by its ID."""
        task_data = self._all_data.get(task_id)
        if task_data is None:
            return None
        return task_data[-1]

    def _update_status(self, message):
        """Update the latest status of a task (by time, not by message)."""
        task_id = message.get('id')
        status = message.get('status')
        time = message.get('time')
        if not all((task_id, status, time)):
            return
        if task_id not in self._status:
            self._status[task_id] = (status, time)
            self._status_journal_summary.append((task_id, status, time, 0))
        else:
            _, current_time = self._status[task_id]
            if time >= current_time:
                index = len(self.get_all_task_data(task_id))
                self._status_journal_summary.append((task_id, status, time,
                                                     index))
            if time > current_time:
                self._status[task_id] = (status, time)

    def process_message(self, message):
        if 'id' not in message:
            raise StatusMsgMissingDataError('id')

        self._update_status(message)
        handlers = {'started': self._handle_task_started,
                    'finished': self._handle_task_finished}
        meth = handlers.get(message.get('status'),
                            self._set_task_data)
        meth(message)

    def process_raw_message(self, raw_message):
        raw_message = raw_message.strip()
        message = json_loads(raw_message)
        self.process_message(message)

    @property
    def result_stats(self):
        return {key: len(value) for key, value in self._by_result.items()}

    def get_task_status(self, task_id):
        return self._status.get(task_id, (None, None))[0]

    @property
    def status_journal_summary(self):
        return self._status_journal_summary
