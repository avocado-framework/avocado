import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch

from avocado.core.status.repo import StatusRepo
from avocado.core.status.server import StatusServer


class StatusServerTest(IsolatedAsyncioTestCase):
    def test_close_before_server_creation(self):
        StatusServer("127.0.0.1:8888", StatusRepo("job")).close()

    def test_close_tcp_server_does_not_unlink_uri(self):
        server = StatusServer("127.0.0.1:8888", StatusRepo("job"))
        server._server_task = Mock()
        with patch(
            "avocado.core.status.server.os.path.exists", return_value=True
        ), patch("avocado.core.status.server.os.unlink") as unlink:
            server.close()
        server._server_task.close.assert_called_once_with()
        unlink.assert_not_called()

    async def test_invalid_status_does_not_discard_following_message(self):
        for invalid_status in (
            b'{"status": "running"}\n',
            b'{"id": "1-foo", "job_id": "job", "status": "started", "time": 1}\n',
        ):
            with self.subTest(invalid_status=invalid_status):
                repo = StatusRepo("job")
                server = StatusServer("127.0.0.1:8888", repo)
                reader = asyncio.StreamReader()
                reader.feed_data(
                    invalid_status
                    + b'{"id": "1-foo", "job_id": "job", "status": "finished", '
                    b'"time": 2, "result": "pass"}\n'
                )
                reader.feed_eof()

                with self.assertLogs("avocado.core.status.server", level="ERROR"):
                    await server.cb(reader, None)

                self.assertEqual(repo.get_task_status("1-foo"), "finished")
                self.assertEqual(repo.get_latest_task_data("1-foo")["result"], "pass")
