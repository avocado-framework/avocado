import socket
import unittest
from unittest.mock import Mock, patch

from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import Task, TaskStatusService


class TaskTest(unittest.TestCase):
    def test_post_delivers_complete_message(self):
        for reconnect, timeout in (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ):
            with self.subTest(reconnect=reconnect, timeout=timeout):
                service = TaskStatusService("127.0.0.1:8888")
                sent = bytearray()
                connection = Mock()
                # A socket may accept only part of a send() buffer.
                connection.send.side_effect = (
                    lambda data, sent=sent: sent.extend(data[:1]) or 1
                )
                connection.sendall.side_effect = (
                    socket.timeout if timeout else sent.extend
                )
                service._connection = connection
                if reconnect:
                    old = Mock()
                    old.send.side_effect = old.sendall.side_effect = BrokenPipeError
                    service._connection = old

                with patch.object(
                    service,
                    "_create_connection",
                    side_effect=lambda service=service, connection=connection: setattr(
                        service, "_connection", connection
                    ),
                ):
                    self.assertEqual(service.post({}), not timeout)

                connection.sendall.assert_called_once_with(b"{}\n")
                self.assertEqual(sent, b"" if timeout else b"{}\n")

    def test_default_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id")
        self.assertEqual(task.category, "test")

    def test_set_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id", category="new_category")
        self.assertEqual(task.category, "new_category")
