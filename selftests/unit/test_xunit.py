import argparse
import os
import shutil
import tempfile
import unittest
from lxml import etree
from StringIO import StringIO
from xml.dom import minidom

from avocado import Test
from avocado.core import job
from avocado.core.result import Result
from avocado.plugins import xunit


class ParseXMLError(Exception):
    pass


class FakeJob(object):

    def __init__(self, args):
        self.args = args
        self.unique_id = '0000000000000000000000000000000000000000'


class xUnitSucceedTest(unittest.TestCase):

    def setUp(self):

        class SimpleTest(Test):

            def test(self):
                pass

        self.tmpfile = tempfile.mkstemp()
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        args = argparse.Namespace(logdir=self.tmpdir)
        args.xunit_output = self.tmpfile[1]
        self.job = job.Job(args)
        self.test_result = Result(FakeJob(args))
        self.test_result.tests_total = 1
        self.test1 = SimpleTest(job=self.job, base_logdir=self.tmpdir)
        self.test1._Test__status = 'PASS'
        self.test1.time_elapsed = 1.23
        self.junit = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     os.path.pardir, ".data", 'junit-4.xsd'))

    def tearDown(self):
        os.close(self.tmpfile[0])
        os.remove(self.tmpfile[1])
        shutil.rmtree(self.tmpdir)

    def testAddSuccess(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        xunit_result = xunit.XUnitResult()
        xunit_result.render(self.test_result, self.job)
        with open(self.job.args.xunit_output) as fp:
            xml = fp.read()
        try:
            dom = minidom.parseString(xml)
        except Exception as details:
            raise ParseXMLError("Error parsing XML: '%s'.\nXML Contents:\n%s" % (details, xml))
        self.assertTrue(dom)
        els = dom.getElementsByTagName('testcase')
        self.assertEqual(len(els), 1)

        with open(self.junit, 'r') as f:
            xmlschema = etree.XMLSchema(etree.parse(f))
        self.assertTrue(xmlschema.validate(etree.parse(StringIO(xml))),
                        "Failed to validate against %s, content:\n%s" %
                        (self.junit, xml))


if __name__ == '__main__':
    unittest.main()
