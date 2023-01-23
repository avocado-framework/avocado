from os import path
from xml.dom import minidom

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class JsonResultTest(TestCaseTmpDir):
    def test_testcase(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/passtest.py "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo"
        )
        process.run(cmd_line, ignore_status=True)
        xunit_path = path.join(self.tmpdir.name, "latest", "results.xml")

        with open(xunit_path, "rb") as fp:
            xml = fp.read()
        try:
            dom = minidom.parseString(xml)
        except Exception as details:
            raise ValueError(f"Error parsing XML: '{details}'.\nXML Contents:\n{xml}")
        self.assertTrue(dom)
        els = dom.getElementsByTagName("testcase")
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].attributes["classname"].value, "PassTest")
        self.assertEqual(
            els[0].attributes["name"].value, "examples/tests/passtest.py:PassTest.test"
        )
        self.assertEqual(els[0].attributes["file"].value, "examples/tests/passtest.py")
        els = dom.getElementsByTagName("failure")
        self.assertEqual(len(els), 0)
