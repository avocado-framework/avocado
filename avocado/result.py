"""Test result module."""


class TestResult(object):

    """
    Test result class, holder for test result information.
    """

    def __init__(self, stream, debuglog, loglevel, tests_total):
        self.stream = stream
        self.debuglog = debuglog
        self.loglevel = loglevel
        self.tests_run = 0
        self.tests_total = tests_total
        self.total_time = 0.0
        self.passed = []
        self.failed = []
        self.skipped = []
        self.warned = []

    def start_tests(self):
        'Called once before any tests are executed.'
        self.stream.start_file_logging(self.debuglog, self.loglevel)
        self.stream.log_header("DEBUG LOG: %s" % self.debuglog)
        self.stream.log_header("TOTAL TESTS: %s" % self.tests_total)
        self.tests_run += 1

    def end_tests(self):
        'Called once after all tests are executed.'
        self.stream.log_header("TOTAL PASSED: %d" % len(self.passed))
        self.stream.log_header("TOTAL FAILED: %d" % len(self.failed))
        self.stream.log_header("TOTAL SKIPPED: %d" % len(self.skipped))
        self.stream.log_header("TOTAL WARNED: %d" % len(self.warned))
        self.stream.log_header("ELAPSED TIME: %.2f s" % self.total_time)
        self.stream.stop_file_logging()

    def start_test(self, test):
        'Called when the given test is about to be run.'
        self.test_label = '(%s/%s) %s: ' % (self.tests_run,
                                            self.tests_total,
                                            test.tagged_name)

    def end_test(self, test):
        'Called when the given test has been run.'
        self.tests_run += 1
        self.total_time += test.time_elapsed

    def add_pass(self, test):
        'Called when a test succeed.'
        self.stream.log_pass(self.test_label, test.time_elapsed)
        self.passed.append(test)

    def add_fail(self, test):
        'Called when a test fails.'
        self.stream.log_fail(self.test_label, test.time_elapsed)
        self.failed.append(test)

    def add_skip(self, test):
        'Called when a test is skipped.'
        self.stream.log_skip(self.test_label, test.time_elapsed)
        self.skipped.append(test)

    def add_warn(self, test):
        'Called when a test warns.'
        self.stream.log_warn(self.test_label, test.time_elapsed)
        self.warned.append(test)

    def check_test(self, test):
        'Called once for a test to check status and report.'
        self.start_test(test)
        status_map = {'PASS': self.add_pass,
                      'FAIL': self.add_fail,
                      'TEST_NA': self.add_skip,
                      'WARN': self.add_warn}
        add = status_map[test.status]
        add(test)
        self.end_test(test)
