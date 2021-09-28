import os
import tempfile
import unittest
from xml.dom import minidom

from avocado import Test
from avocado.core import job
from avocado.core.result import Result
from avocado.plugins import xunit
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

try:
    import xmlschema
    SCHEMA_CAPABLE = True
except ImportError:
    SCHEMA_CAPABLE = False


setup_avocado_loggers()


UNIQUE_ID = '0000000000000000000000000000000000000000'
LOGFILE = None


class ParseXMLError(Exception):
    pass


class xUnitSucceedTest(unittest.TestCase):

    def setUp(self):

        class SimpleTest(Test):

            def test(self):
                pass

        self.tmpfile = tempfile.mkstemp()
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        config = {'job.run.result.xunit.output': self.tmpfile[1],
                  'run.results_dir': self.tmpdir.name}
        self.job = job.Job(config)
        self.job.setup()
        self.test_result = Result(UNIQUE_ID, LOGFILE)
        self.test_result.tests_total = 1
        self.test_result.logfile = ("/.../avocado/job-results/"
                                    "job-2018-11-28T16.27-8fef221/job.log")
        self.test1 = SimpleTest(config=self.job.config, base_logdir=self.tmpdir.name)
        self.test1._Test__status = 'PASS'
        self.test1._Test__logfile = ''
        self.test1.time_elapsed = 678.23689

    def tearDown(self):
        self.job.cleanup()
        errs = []
        cleanups = (lambda: os.close(self.tmpfile[0]),
                    lambda: os.remove(self.tmpfile[1]),
                    self.tmpdir.cleanup)
        for cleanup in cleanups:
            try:
                cleanup()
            except Exception as exc:
                errs.append(str(exc))
        self.assertFalse(errs, "Failures occurred during cleanup:\n%s"
                         % "\n".join(errs))

    @unittest.skipUnless(SCHEMA_CAPABLE,
                         'Unable to validate schema due to missing xmlschema library')
    def test_add_success(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        xunit_result = xunit.XUnitResult()
        xunit_result.render(self.test_result, self.job)
        xunit_output = self.job.config.get('job.run.result.xunit.output')
        with open(xunit_output, 'rb') as fp:
            xml = fp.read()
        try:
            dom = minidom.parseString(xml)
        except Exception as details:
            raise ParseXMLError("Error parsing XML: '%s'.\nXML Contents:\n%s" % (details, xml))
        self.assertTrue(dom)

        els = dom.getElementsByTagName('testsuite')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].attributes['time'].value, '678.237')

        els = dom.getElementsByTagName('testcase')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].attributes['time'].value, '678.237')

        junit_xsd = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            os.path.pardir, ".data",
            'jenkins-junit.xsd'))
        xml_schema = xmlschema.XMLSchema(junit_xsd)
        self.assertTrue(xml_schema.is_valid(xunit_output))

    def test_max_test_log_size(self):
        def get_system_out(out):
            return out[out.find(b"<system-out>"):out.find(b"<system-out/>")]
        log = tempfile.NamedTemporaryFile(dir=self.tmpdir.name, delete=False)
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
        # setting the default value
        self.job.config['job.run.result.xunit.max_test_log_chars'] = 100000
        xunit_result.render(self.test_result, self.job)
        xunit_output = self.job.config.get('job.run.result.xunit.output')
        with open(xunit_output, 'rb') as fp:
            unlimited = fp.read()
        # setting a small value
        self.job.config['job.run.result.xunit.max_test_log_chars'] = 10
        xunit_result.render(self.test_result, self.job)
        with open(xunit_output, 'rb') as fp:
            limited = fp.read()
        # back to the default value
        self.job.config['job.run.result.xunit.max_test_log_chars'] = 100000
        xunit_result.render(self.test_result, self.job)
        with open(xunit_output, 'rb') as fp:
            limited_but_fits = fp.read()
        self.assertLess(len(limited), len(unlimited) - 500,
                        "Length of xunit limited to 10 chars was greater "
                        "than (unlimited - 500). Unlimited output:\n%s\n\n"
                        "Limited output:\n%s" % (unlimited, limited))
        unlimited_output = get_system_out(unlimited)
        self.assertIn(log_content, unlimited_output)
        self.assertEqual(unlimited_output, get_system_out(limited_but_fits))
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
