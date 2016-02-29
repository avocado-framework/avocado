import argparse
import unittest
import os
from xml.dom import minidom
import tempfile
import shutil

from avocado import Test
from avocado.core import xunit
from avocado.core import job


class ParseXMLError(Exception):
    pass


class FakeJob(object):
    def __init__(self, args):
        self.args = args


class xUnitSucceedTest(unittest.TestCase):

    def setUp(self):

        class SimpleTest(Test):

            def test(self):
                pass

        self.tmpfile = tempfile.mkstemp()
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        args = argparse.Namespace()
        args.xunit_output = self.tmpfile[1]
        self.test_result = xunit.xUnitTestResult(FakeJob(args))
        self.test_result.start_tests()
        self.test1 = SimpleTest(job=job.Job(), base_logdir=self.tmpdir)
        self.test1.status = 'PASS'
        self.test1.time_elapsed = 1.23

    def tearDown(self):
        os.close(self.tmpfile[0])
        os.remove(self.tmpfile[1])
        shutil.rmtree(self.tmpdir)

    def testAddSuccess(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        self.assertTrue(self.test_result.xml)
        with open(self.test_result.output) as fp:
            xml = fp.read()
        try:
            dom = minidom.parseString(xml)
        except Exception as details:
            raise ParseXMLError("Error parsing XML: '%s'.\nXML Contents:\n%s" % (details, xml))
        self.assertTrue(dom)
        els = dom.getElementsByTagName('testcase')
        self.assertEqual(len(els), 1)


if __name__ == '__main__':
    unittest.main()
