import glob
import os
import unittest

from avocado.core import jobdata


BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
BASEDIR = os.path.abspath(BASEDIR)


class JobdataTest(unittest.TestCase):

    @staticmethod
    def _check_results(pth):
        msg = "Retrieved %s is not '%s' (%s)"
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
        return errs

    def test_versions(self):
        os.chdir(BASEDIR)
        errs = []
        for pth in sorted(glob.glob(os.path.join(BASEDIR, "selftests",
                                                 ".data", "results-*"))):
            res = self._check_results(pth)
            if res:
                name = os.path.basename(pth)
                errs.append("%s\n%s\n\n  %s\n\n" % (name, "-" * len(name),
                                                    "\n  ".join(res)))
        self.assertFalse(errs, "Some results were not loaded properly:\n%s"
                         % "\n * ".join(errs))


if __name__ == "__main__":
    unittest.main()
