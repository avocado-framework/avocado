from unittest import TestCase

from avocado.core.status import repo, utils


class StatusRepo(TestCase):

    def setUp(self):
        self.status_repo = repo.StatusRepo()

    def test_process_raw_message_invalid(self):
        with self.assertRaises(utils.StatusMsgInvalidJSONError):
            self.status_repo.process_raw_message('+-+-InvalidJSON-AFAICT-+-+')

    def test_process_raw_message_no_id(self):
        msg = ('{"status": "finished", "time": 1597774000.5140226, '
               '"returncode": 0}')
        with self.assertRaises(repo.StatusMsgMissingDataError):
            self.status_repo.process_raw_message(msg)

    def test_set_task_data(self):
        self.status_repo._set_task_data({"id": "1-foo", "status": "started"})
        self.assertEqual(self.status_repo._all_data["1-foo"],
                         [{"status": "started"}])

    def test_handle_task_started(self):
        msg = {"id": "1-foo", "status": "started", "output_dir": "/fake/path"}
        self.status_repo._handle_task_started(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "started", "output_dir": "/fake/path"}])

    def test_handle_task_started_no_output_dir(self):
        msg = {"id": "1-foo", "status": "started"}
        with self.assertRaises(repo.StatusMsgMissingDataError):
            self.status_repo._handle_task_started(msg)

    def test_handle_task_finished_no_result(self):
        msg = {"id": "1-foo", "status": "finished"}
        self.status_repo._handle_task_finished(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "finished"}])
        self.assertEqual(self.status_repo._by_result.get(None), ["1-foo"])

    def test_handle_task_finished_result(self):
        msg = {"id": "1-foo", "status": "finished", "result": "pass"}
        self.status_repo._handle_task_finished(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "finished", "result": "pass"}])
        self.assertEqual(self.status_repo._by_result.get("pass"), ["1-foo"])

    def test_process_message_running(self):
        msg = {"id": "1-foo", "status": "running"}
        self.status_repo.process_message(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "running"}])

    def test_process_raw_message_task_started(self):
        msg = '{"id": "1-foo", "status": "started", "output_dir": "/fake/path"}'
        self.status_repo.process_raw_message(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "started", "output_dir": "/fake/path"}])

    def test_process_raw_message_task_running(self):
        msg = '{"id": "1-foo", "status": "running"}'
        self.status_repo.process_raw_message(msg)
        self.assertEqual(self.status_repo.get_task_data("1-foo"),
                         [{"status": "running"}])
