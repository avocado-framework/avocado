import os
import unittest

from six import PY3

from avocado.core import jobdata


BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
BASEDIR = os.path.abspath(BASEDIR)


class JobdataTest(unittest.TestCase):

    def _check_results(self, dirname):
        pth = os.path.join(BASEDIR, "selftests", ".data", dirname)

        # pwd
        self.assertEqual(jobdata.retrieve_pwd(pth),
                         "/home/medic/Work/Projekty/avocado/avocado",
                         "pwd mismatch")

        # references
        self.assertEqual(jobdata.retrieve_references(pth),
                         ["yes", "no"], "references mismatch")

        # variants
        try:
            variants = jobdata.retrieve_variants(pth)
        except Exception as details:
            self.fail("variants: Unable to retrieve: %s" % details)
        act = variants.to_str(0, 99)
        self.assertTrue(act)
        exp = ("\nVariant variant1-6ec4:    /run/variant1\n"
               "    /run/variant1:foo => bar\n\n"
               "Variant variant2-a6fe:    /run/variant2\n"
               "    /run/variant2:foo => baz")
        self.assertIn(exp, act, "variants mismatch")

        # args
        try:
            args = jobdata.retrieve_args(pth)
        except Exception as details:
            self.fail("args: Unable to retrieve: %s" % details)
        self.assertTrue(isinstance(args, dict),
                        "args: Invalid args: %s" % args)
        for scenario in [["loaders", [u"external:/bin/echo"]],
                         ["external_runner", u"/bin/echo"],
                         ["failfast", False, None],
                         ["ignore_missing_references", False, None],
                         ["execution_order", "variants-per-test",
                          None]]:
            act = args.get(scenario[0])
            self.assertIn(act, scenario[1:],
                          "args: Invalid value '%s' of key '%s' '%s'" % (
                              act, scenario[0], scenario[1:]))

        # config
        conf_path = jobdata.retrieve_config(pth)
        self.assertTrue(os.path.exists(conf_path),
                        "config: Retrieved path '%s' does not exists" %
                        conf_path)
        exp = "[avocado.selftest]\njobdata = yes"
        with open(conf_path, "r") as conf:
            act = conf.read()
            self.assertIn(exp, act,
                          "config: Expected string\n%s\n\nNot in:\n%s" % (
                              exp, act))

        # cmdline
        act = jobdata.retrieve_cmdline(pth)
        exp = ['/usr/local/bin/avocado', 'run', '--external-runner',
               '/bin/echo', '-m', 'examples/mux-0.yaml', '--', 'yes', 'no']
        self.assertEqual(exp, act,
                         "cmdline: Invalid cmdline '%s' (%s)" % (act, exp))

    @unittest.skipIf(PY3, "Skipping tests with data pickled on Python 2")
    def setUp(self):
        os.chdir(BASEDIR)

    def test_36_0_lts(self):
        self._check_results("results-36.0lts")

    def test_36_4(self):
        self._check_results("results-36.4")

    def test_37_0(self):
        self._check_results("results-37.0")

    def test_38_0(self):
        self._check_results("results-38.0")

    def test_39_0(self):
        self._check_results("results-39.0")

    def test_40_0(self):
        self._check_results("results-40.0")

    def test_41_0(self):
        self._check_results("results-41.0")

    def test_51_0(self):
        self._check_results("results-51.0")


if __name__ == "__main__":
    unittest.main()
