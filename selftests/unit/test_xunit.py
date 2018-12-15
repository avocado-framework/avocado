import argparse
import os
import shutil
import tempfile
import unittest
from xml.dom import minidom

try:
    from io import BytesIO
except ImportError:
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

from .. import setup_avocado_loggers


setup_avocado_loggers()


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
        self.test_result.logfile = ("/.../avocado/job-results/"
                                    "job-2018-11-28T16.27-8fef221/job.log")
        self.test1 = SimpleTest(job=self.job, base_logdir=self.tmpdir)
        self.test1._Test__status = 'PASS'
        self.test1.time_elapsed = 1.23

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

        junit_xsd = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 os.path.pardir, ".data",
                                                 'jenkins-junit.xsd'))
        with open(junit_xsd, 'r') as f:
            xmlschema = etree.XMLSchema(etree.parse(f))   # pylint: disable=I1101
        # pylint: disable=I1101
        self.assertTrue(xmlschema.validate(etree.parse(BytesIO(xml))),
                        "Failed to validate against %s, content:\n%s\nerror log:\n%s" %
                        (junit_xsd, xml, xmlschema.error_log))

    def test_max_test_log_size(self):
        log = tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False)
        log_content = b"1234567890" * 100
        log_content += b"this should not be present" + b"0987654321" * 100
        log.write(log_content)
        log_path = log.name
        log.close()
        self.test1._Test__status = "ERROR"
        self.test1._Test__logfile = log_path
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        xunit_result = xunit.XUnitResult()
        xunit_result.render(self.test_result, self.job)
        with open(self.job.args.xunit_output, 'rb') as fp:
            unlimited = fp.read()
        self.job.args.xunit_max_test_log_chars = 10
        xunit_result.render(self.test_result, self.job)
        with open(self.job.args.xunit_output, 'rb') as fp:
            limited = fp.read()
        self.assertLess(len(limited), len(unlimited) - 500,
                        "Length of xunit limitted to 10 chars was greater "
                        "than (unlimited - 500). Unlimited output:\n%s\n\n"
                        "Limited output:\n%s" % (unlimited, limited))
        self.assertIn(b"this should not be present", unlimited)
        self.assertNotIn(b"this should not be present", limited)
        self.assertIn(b"1234567890", unlimited)
        self.assertNotIn(b"1234567890", limited)
        self.assertIn(b"12345", limited)
        self.assertIn(b"0987654321", unlimited)
        self.assertNotIn(b"0987654321", limited)
        self.assertIn(b"54321", limited)


if __name__ == '__main__':
    unittest.main()
