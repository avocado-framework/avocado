import os
import unittest

from six import PY3

from avocado.core import jobdata


BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
BASEDIR = os.path.abspath(BASEDIR)


class JobdataTest(unittest.TestCase):

    def _check_results(self, dirname):
        pth = os.path.join(BASEDIR, "selftests", ".data", dirname)
        errs = []
        # pwd
        exp = "/home/medic/Work/Projekty/avocado/avocado"
        act = jobdata.retrieve_pwd(pth)
        if act != exp:
            errs.append("pwd: '%s' '%s'" % (exp, act))

        # references
        exp = ["yes", "no"]
        act = jobdata.retrieve_references(pth)
        if act != exp:
            errs.append("references: '%s' '%s'" % (exp, act))

        # variants
        try:
            variants = jobdata.retrieve_variants(pth)
            act = variants.to_str(0, 99)
        except Exception as details:
            errs.append("variants: Unable to retrieve: %s" % details)
        else:
            exp = ("\nVariant variant1-6ec4:    /run/variant1\n"
                   "    /run/variant1:foo => bar\n\n"
                   "Variant variant2-a6fe:    /run/variant2\n"
                   "    /run/variant2:foo => baz")
            if not act or exp not in act:
                errs.append("variants:\n%s\n\n%s" % (exp, act))

        # args
        try:
            args = jobdata.retrieve_args(pth)
        except Exception as details:
            errs.append("args: Unable to retrieve: %s" % details)
        else:
            if isinstance(args, dict):
                for scenario in [["loaders", [u"external:/bin/echo"]],
                                 ["external_runner", u"/bin/echo"],
                                 ["failfast", False, None],
                                 ["ignore_missing_references", False, None],
                                 ["execution_order", "variants-per-test",
                                  None]]:
                    act = args.get(scenario[0])
                    for exp in scenario[1:]:
                        if act == exp:
                            break
                    else:
                        errs.append("args: Invalid value '%s' of key '%s' "
                                    "%s" % (act, scenario[0],
                                            scenario[1:]))
            else:
                errs.append("args: Invalid args: %s" % args)

        # config
        conf_path = jobdata.retrieve_config(pth)
        if os.path.exists(conf_path):
            exp = "[avocado.selftest]\njobdata = yes"
            with open(conf_path, "r") as conf:
                act = conf.read()
                if exp not in act:
                    errs.append("config: Expected string\n%s\n\nNot in:\n%s"
                                % (exp, act))

        else:
            errs.append("config: Retrieved path '%s' does not exists"
                        % conf_path)

        # cmdline
        act = jobdata.retrieve_cmdline(pth)
        exp = ['/usr/local/bin/avocado', 'run', '--external-runner',
               '/bin/echo', '-m', 'examples/mux-0.yaml', '--', 'yes', 'no']
        if exp != act:
            errs.append("cmdline: Invalid cmdline '%s' (%s)" % (act, exp))
        self.assertFalse(errs, "Errors: %s" % "\n  ".join(errs))

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
