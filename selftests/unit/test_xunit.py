import argparse
import os
import shutil
import tempfile
import unittest
from xml.dom import minidom

try:
    from io import BytesIO
except:
    from BytesIO import BytesIO

try:
    from lxml import etree
    SCHEMA_CAPABLE = True
except ImportError:
    SCHEMA_CAPABLE = False

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
        args = argparse.Namespace(base_logdir=self.tmpdir)
        args.xunit_output = self.tmpfile[1]
        self.job = job.Job(args)
        self.test_result = Result(FakeJob(args))
        self.test_result.tests_total = 1
        self.test1 = SimpleTest(job=self.job, base_logdir=self.tmpdir)
        self.test1._Test__status = 'PASS'
        self.test1.time_elapsed = 1.23
        junit_xsd = os.path.join(os.path.dirname(__file__),
                                 os.path.pardir, ".data", 'junit-4.xsd')
        self.junit = os.path.abspath(junit_xsd)

    def tearDown(self):
        errs = []
        cleanups = (lambda: os.close(self.tmpfile[0]),
                    lambda: os.remove(self.tmpfile[1]),
                    lambda: shutil.rmtree(self.tmpdir))
        for cleanup in cleanups:
            try:
                cleanup()
            except Exception as exc:
                errs.append(str(exc))
        self.assertFalse(errs, "Failures occurred during cleanup:\n%s"
                         % "\n".join(errs))

    @unittest.skipUnless(SCHEMA_CAPABLE,
                         'Unable to validate schema due to missing lxml.etree library')
    def test_add_success(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        xunit_result = xunit.XUnitResult()
        xunit_result.render(self.test_result, self.job)
        with open(self.job.args.xunit_output, 'rb') as fp:
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
        self.assertTrue(xmlschema.validate(etree.parse(BytesIO(xml))),
                        "Failed to validate against %s, content:\n%s" %
                        (self.junit, xml))


if __name__ == '__main__':
    unittest.main()
