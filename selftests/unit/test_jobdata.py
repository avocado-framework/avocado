import os
import unittest

from six import PY3

from avocado.core import jobdata

from .. import BASEDIR
from .. import setup_avocado_loggers


setup_avocado_loggers()


class JobdataTest(unittest.TestCase):

    def _check_results(self, dirname):
        pth = os.path.join(BASEDIR, "selftests", ".data", dirname)

        # pwd
        self.assertEqual(jobdata.retrieve_pwd(pth),
                         "/home/user/avocado",
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
        exp = ("\nVariant first-febe:    /run/first\n"
               "    /run/first:variable_one => 1\n\n"
               "Variant second-bafe:    /run/second\n"
               "    /run/second:variable_two => 2")
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
               '/bin/echo', '-m', 'examples/yaml_to_mux/simple_vars.yaml',
               '--', 'yes', 'no']
        self.assertEqual(exp, act,
                         "cmdline: Invalid cmdline '%s' (%s)" % (act, exp))

    @unittest.skipIf(PY3, "Skipping tests with data pickled on Python 2")
    def setUp(self):
        os.chdir(BASEDIR)

    def test_52_0(self):
        self._check_results("results-52.0")


if __name__ == "__main__":
    unittest.main()
