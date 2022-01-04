import io
import socket
import unittest

from avocado.utils import datadrainer


class Base(unittest.TestCase):

    def test_instantiate(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            datadrainer.BaseDrainer(None)


class Magic(datadrainer.BaseDrainer):

    name = 'test_utils_datadrainer.Magic'
    magic = 'MAGIC_magic_MAGIC'

    def data_available(self):
        return True

    def read(self):
        return self.magic

    def write(self, data):
        self.destination = data  # pylint: disable=W0201
        self._internal_quit = True


class Custom(unittest.TestCase):

    def test(self):
        magic = Magic(None)
        magic.start()
        magic.wait()
        self.assertEqual(Magic.magic, magic.destination)


class Socket(datadrainer.FDDrainer):

    name = 'test_utils_datadrainer.Socket'

    def __init__(self, source):
        super().__init__(source)
        self.data_buffer = io.BytesIO()
        self._write_count = 0

    def write(self, data):
        self.data_buffer.write(data)
        self._write_count += len(data)
        if self._write_count > 2:
            self._internal_quit = True


class CustomSocket(unittest.TestCase):

    def setUp(self):
        self.socket1, self.socket2 = socket.socketpair(socket.AF_UNIX)

    def test(self):
        socket_drainer = Socket(self.socket2.fileno())
        socket_drainer.start()
        self.socket1.send(b'1')
        self.socket1.send(b'2')
        self.socket1.send(b'3')
        socket_drainer.wait()
        self.assertEqual(socket_drainer.data_buffer.getvalue(), b'123')

    def tearDown(self):
        self.socket1.close()
        self.socket2.close()


class SocketBuffer(datadrainer.BufferFDDrainer):

    name = 'test_utils_datadrainer.SocketBuffer'

    def __init__(self, source):
        super().__init__(source)
        self._stop_check = lambda: len(self.data) > 2


class CustomSocketBuffer(unittest.TestCase):

    def setUp(self):
        self.socket1, self.socket2 = socket.socketpair(socket.AF_UNIX)

    def test(self):
        socket_drainer = SocketBuffer(self.socket2.fileno())
        socket_drainer.start()
        self.socket1.send(b'1')
        self.socket1.send(b'2')
        self.socket1.send(b'3')
        socket_drainer.wait()
        self.assertEqual(socket_drainer.data, b'123')

    def tearDown(self):
        self.socket1.close()
        self.socket2.close()
