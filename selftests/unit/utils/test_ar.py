import os
import unittest

from avocado.utils import ar
from selftests.utils import BASEDIR


class ArTest(unittest.TestCase):

    def test_is_ar(self):
        path = os.path.join(BASEDIR, "selftests", ".data", "hello.deb")
        self.assertTrue(ar.Ar(path).is_valid())

    def test_is_not_ar(self):
        path = os.path.join(BASEDIR, "selftests", ".data", "hello.rpm")
        self.assertFalse(ar.Ar(path).is_valid())

    def test_iter(self):
        path = os.path.join(BASEDIR, "selftests", ".data", "hello.deb")
        expected = [("debian-binary", 4, 68),
                    ("control.tar.xz", 1868, 132),
                    ("data.tar.xz", 54072, 2060)]
        for count, member in enumerate(ar.Ar(path)):
            self.assertEqual(expected[count][0], member.identifier)
            self.assertEqual(expected[count][1], member.size)
            self.assertEqual(expected[count][2], member.offset)

    def test_list(self):
        path = os.path.join(BASEDIR, "selftests", ".data", "hello.deb")
        self.assertEqual(ar.Ar(path).list(),
                         ["debian-binary", "control.tar.xz", "data.tar.xz"])

    def test_read_member(self):
        path = os.path.join(BASEDIR, "selftests", ".data", "guaca.a")
        self.assertEqual(ar.Ar(path).read_member('shopping'),
                         b'avocados, salt')
        self.assertEqual(ar.Ar(path).read_member('recipe'),
                         b'cut, mix')
