import unittest

from avocado.utils import datadrainer


class Base(unittest.TestCase):

    def test_instantiate(self):
        datadrainer.BaseDrainer(None)

    def test_start_wait(self):
        base = datadrainer.BaseDrainer(None, lambda: True)
        base.start()
        base.wait()


class Magic(datadrainer.BaseDrainer):

    name = 'test_utils_datadrainer.Magic'
    magic = 'MAGIC_magic_MAGIC'

    def data_available(self):
        return True

    def read(self):
        return self.magic

    def write(self, data):
        self.destination = data
        self._internal_quit = True


class Custom(unittest.TestCase):

    def test(self):
        magic = Magic(None)
        magic.start()
        magic.wait()
        self.assertEqual(Magic.magic, magic.destination)
