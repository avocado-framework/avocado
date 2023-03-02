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
        els = dom.getElementsByTagName("failure")
        self.assertEqual(len(els), 0)

    def test_fail_reason(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/failtest.py "
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
        els = dom.getElementsByTagName("failure")
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].attributes["type"].value, "TestFail")
        self.assertEqual(
            els[0].attributes["message"].value, "This test is supposed to fail"
        )
        for child in els[0].childNodes:
            if child.nodeType is child.CDATA_SECTION_NODE:
                self.assertIn("Traceback (most recent call last):", child.nodeValue)

    def test_error_reason(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/errortest.py "
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
        els = dom.getElementsByTagName("error")
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].attributes["type"].value, "TestError")
        self.assertEqual(
            els[0].attributes["message"].value, "This should end with ERROR."
        )
        for child in els[0].childNodes:
            if child.nodeType is child.CDATA_SECTION_NODE:
                self.assertIn("Traceback (most recent call last):", child.nodeValue)

    def test_variant(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/passtest.py "
            "--mux-yaml examples/yaml_to_mux/simple_vars.yaml "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo "
            "--max-parallel-tasks=1"
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
        self.assertEqual(
            els[0].attributes["name"].value,
            "examples/tests/passtest.py:PassTest.test;run-first-febe",
        )
        self.assertEqual(
            els[1].attributes["name"].value,
            "examples/tests/passtest.py:PassTest.test;run-second-bafe",
        )
