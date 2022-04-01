import tempfile
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.core.parser import HintParser
from avocado.core.resolver import ReferenceResolution
from avocado.core.settings import SettingsError
from selftests.utils import TestCaseTmpDir, skipUnlessPathExists

BAD = """[kinds]
tap = ./tests/*.t
"""

GOOD = """[kinds]
exec-test = /bin/true
[exec-test]
uri = $testpath
"""


class HintTest(TestCaseTmpDir):
    def setUp(self):
        super().setUp()

        self.wrong_file = tempfile.NamedTemporaryFile('w', dir=self.tmpdir.name, delete=False)
        self.wrong_file.write(BAD)
        self.wrong_file.close()

        self.good_file = tempfile.NamedTemporaryFile('w', dir=self.tmpdir.name, delete=False)
        self.good_file.write(GOOD)
        self.good_file.close()

        self.wrong_hint = HintParser(self.wrong_file.name)
        self.good_hint = HintParser(self.good_file.name)

    def test_wrong_parser(self):
        with self.assertRaises(SettingsError) as context:
            self.wrong_hint.validate_kind_section('tap')
        self.assertTrue('Section tap is not defined' in str(context.exception))

    @skipUnlessPathExists('/bin/true')
    def test_types(self):
        res = self.good_hint.get_resolutions()
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], ReferenceResolution)

        resolutions = res[0].resolutions
        self.assertEqual(len(resolutions), 1)
        self.assertIsInstance(resolutions[0], Runnable)

    @skipUnlessPathExists('/bin/true')
    def test_reference_names(self):
        res = self.good_hint.get_resolutions()[0]
        self.assertEqual(res.reference, '/bin/true')
        self.assertEqual(res.resolutions[0].uri, '/bin/true')


if __name__ == '__main__':
    unittest.main()
