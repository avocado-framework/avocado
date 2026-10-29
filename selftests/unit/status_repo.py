from unittest import TestCase

from avocado.core.status import repo, utils


class StatusRepo(TestCase):
    def setUp(self):
        job_id = "0000000000000000000000000000000000000000"
        self.status_repo = repo.StatusRepo(job_id)

    def test_process_raw_message_invalid(self):
        with self.assertRaises(utils.StatusMsgInvalidJSONError):
            self.status_repo.process_raw_message("+-+-InvalidJSON-AFAICT-+-+")

    def test_process_raw_message_no_id(self):
        msg = (
            '{"status": "finished", "time": 1597774000.5140226, '
            '"returncode": 0, '
            '"job_id": "0000000000000000000000000000000000000000"}'
        )
        with self.assertRaises(repo.StatusMsgMissingDataError):
            self.status_repo.process_raw_message(msg)

    def test_process_raw_message_no_job_id(self):
        msg = (
            '{"status": "finished", "time": 1597774000.5140226, '
            '"returncode": 0, "id": "1-foo"}'
        )
        with self.assertRaises(repo.StatusMsgMissingDataError):
            self.status_repo.process_raw_message(msg)

    def test_set_task_data(self):
        self.status_repo._set_task_data({"id": "1-foo", "status": "started"})
        self.assertEqual(self.status_repo._all_data["1-foo"], [{"status": "started"}])

    def test_handle_task_started(self):
        msg = {"id": "1-foo", "status": "started", "output_dir": "/fake/path"}
        self.status_repo._handle_task_started(msg)
        self.assertEqual(
            self.status_repo.get_all_task_data("1-foo"),
            [{"status": "started", "output_dir": "/fake/path"}],
        )

    def test_handle_task_started_no_output_dir(self):
        msg = {"id": "1-foo", "status": "started"}
        with self.assertRaises(repo.StatusMsgMissingDataError):
            self.status_repo._handle_task_started(msg)

    def test_handle_task_finished_invalid_result(self):
        for fields in (
            {},
            {"result": None},
            {"result": 1},
            {"result": False},
            {"result": []},
            {"result": {}},
            {"result": "unsupported"},
        ):
            with self.subTest(fields=fields):
                msg = {"id": "1-foo", "status": "finished", **fields}
                with self.assertLogs(repo.LOG, level="ERROR"):
                    self.status_repo._handle_task_finished(msg)
                data = self.status_repo.get_latest_task_data("1-foo")
                self.assertEqual(data["result"], "error")
                self.assertIn("unsupported status", data["fail_reason"])
                self.assertEqual(self.status_repo._by_result.get("error"), ["1-foo"])

    def test_handle_task_finished_result(self):
        msg = {"id": "1-foo", "status": "finished", "result": "pass"}
        self.status_repo._handle_task_finished(msg)
        self.assertEqual(
            self.status_repo.get_all_task_data("1-foo"),
            [{"status": "finished", "result": "pass"}],
        )
        self.assertEqual(self.status_repo._by_result.get("pass"), ["1-foo"])

    def test_process_message_running(self):
        msg = {
            "id": "1-foo",
            "status": "running",
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(
            self.status_repo.get_all_task_data("1-foo"), [{"status": "running"}]
        )

    def test_process_raw_message_task_started(self):
        msg = (
            '{"id": "1-foo", "status": "started", '
            '"output_dir": "/fake/path", '
            '"job_id": "0000000000000000000000000000000000000000"}'
        )
        self.status_repo.process_raw_message(msg)
        self.assertEqual(
            self.status_repo.get_all_task_data("1-foo"),
            [{"status": "started", "output_dir": "/fake/path"}],
        )

    def test_process_raw_message_task_running(self):
        msg = (
            '{"id": "1-foo", "status": "running", '
            '"job_id": "0000000000000000000000000000000000000000"}'
        )
        self.status_repo.process_raw_message(msg)
        self.assertEqual(
            self.status_repo.get_all_task_data("1-foo"), [{"status": "running"}]
        )

    def test_process_messages_running(self):
        msg = {
            "id": "1-foo",
            "status": "running",
            "time": 1597894378.6080744,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        msg = {
            "id": "1-foo",
            "status": "running",
            "time": 1597894378.6103745,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(
            self.status_repo.get_latest_task_data("1-foo"),
            {"status": "running", "time": 1597894378.6103745},
        )
        self.assertEqual(
            self.status_repo._status["1-foo"], ("running", 1597894378.6103745)
        )
        with self.assertRaises(IndexError):
            self.status_repo.status_journal_summary_pop()

    def test_heartbeat_after_finished(self):
        self.status_repo.process_message(
            {
                "id": "1-foo",
                "status": "finished",
                "result": "pass",
                "time": 1000000001.0,
                "job_id": self.status_repo.job_id,
            }
        )
        self.status_repo.status_journal_summary_pop()
        self.status_repo.process_message(
            {
                "id": "1-foo",
                "status": "running",
                "time": 1000000002.0,
                "job_id": self.status_repo.job_id,
            }
        )
        self.assertEqual(self.status_repo.get_task_status("1-foo"), "finished")
        self.assertEqual(
            self.status_repo.get_latest_task_data("1-foo"),
            {"status": "running", "time": 1000000002.0},
        )
        with self.assertRaises(IndexError):
            self.status_repo.status_journal_summary_pop()

    def test_task_status_time(self):
        msg = {
            "id": "1-foo",
            "status": "running",
            "time": 1597894378.0000002,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(
            self.status_repo._status["1-foo"], ("running", 1597894378.0000002)
        )
        msg = {
            "id": "1-foo",
            "status": "started",
            "time": 1597894378.0000001,
            "output_dir": "/fake/path",
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(
            self.status_repo._status["1-foo"], ("running", 1597894378.0000002)
        )

    def test_no_task_status(self):
        self.assertIsNone(self.status_repo.get_task_status("1-no-existing-id"))

    def test_get_task_status(self):
        msg = {
            "id": "1-foo",
            "status": "running",
            "time": 1597894378.0000002,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(self.status_repo.get_task_status("1-foo"), "running")
        msg = {
            "id": "1-foo",
            "status": "started",
            "time": 1597894378.0000001,
            "output_dir": "/fake/path",
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(self.status_repo.get_task_status("1-foo"), "running")

    def test_get_task_status_journal_summary(self):
        msg = {
            "id": "1-foo",
            "status": "running",
            "type": "log",
            "time": 1000000003.0,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        msg = {
            "id": "1-foo",
            "status": "running",
            "type": "log",
            "time": 1000000002.0,
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        msg = {
            "id": "1-foo",
            "status": "started",
            "time": 1000000001.0,
            "output_dir": "/fake/path",
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        msg = {
            "id": "1-foo",
            "status": "finished",
            "time": 1000000004.0,
            "result": "pass",
            "job_id": "0000000000000000000000000000000000000000",
        }
        self.status_repo.process_message(msg)
        self.assertEqual(self.status_repo.get_task_status("1-foo"), "finished")
        self.assertEqual(
            self.status_repo.status_journal_summary_pop(),
            (1000000001.0, "1-foo", "started", 2),
        )
        self.assertEqual(
            self.status_repo.status_journal_summary_pop(),
            (1000000002.0, "1-foo", "running", 1),
        )
        self.assertEqual(
            self.status_repo.status_journal_summary_pop(),
            (1000000003.0, "1-foo", "running", 0),
        )
        self.assertEqual(
            self.status_repo.status_journal_summary_pop(),
            (1000000004.0, "1-foo", "finished", 3),
        )
        with self.assertRaises(IndexError):
            self.status_repo.status_journal_summary_pop()
