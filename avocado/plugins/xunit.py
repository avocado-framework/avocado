from avocado.plugins import plugin
from avocado.result import TestResult


class xUnitTestResult(TestResult):

    """
    xUnit Test Result class.
    """

    def __init__(self, filename='result.xml'):
        TestResult.__init__(self)
        self.filename = filename
        self.xml = ['<?xml version="1.0" encoding="UTF-8"?>']

    def start_tests(self):
        TestResult.start_tests(self)
        self.xml.append('<testsuite name="avocado" '
                        'tests="{tests}" errors="{errors}" failures="{failures}" skip="{skip}">')

    def start_test(self, test):
        TestResult.start_test(self, test)

    def end_test(self, test):
        TestResult.end_test(self, test)
        tc = '\t<testcase classname="{class}" name="{name}" time="{time}">'
        tag = test.tag
        if test.tag is None:
            tag = 1
        nametag = '%s.%s' % (test.name, tag)
        values = {'class': test.__class__.__name__,
                  'name': nametag,
                  'time': test.time_elapsed}
        self.xml.append(tc.format(**values))
        self.xml.append('\t</testcase>')

    def end_tests(self):
        TestResult.end_tests(self)
        self.xml.append('</testsuite>')
        xml = '\n'.join(self.xml)
        values = {'tests': self.tests_total,
                  'errors': len(self.errors),
                  'failures': len(self.failed),
                  'skip': len(self.skipped), }
        xml = xml.format(**values)
        with open(self.filename, 'w') as fresult:
            fresult.write(xml)


class XUnit(plugin.Plugin):

    """
    xUnit output
    """

    name = 'xunit'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--xunit', action='store_true')
        app_parser.add_argument('--xunit-output',
                                default='result.xml', type=str,
                                dest='xunit_output',
                                help='the file where the result should be written')
        self.configured = True

    def activate(self, app_args):
        if app_args.xunit:
            self.parser.set_defaults(test_result=xUnitTestResult(filename=app_args.xunit_output))
