import json
import sys

from avocado import Test, fail_on
from avocado.utils import process


class Interface(Test):

    def get_runner(self):
        default_runner = "%s -m avocado.core.nrunner" % sys.executable
        return self.params.get("runner", default=default_runner)

    @fail_on(process.CmdError)
    def test_help(self):
        """
        Makes sure a runner can be called with --help and that the
        basic required commands are present in the help message
        """
        cmd = "%s --help" % self.get_runner()
        result = process.run(cmd)
        self.assertIn(b"capabilities", result.stdout,
                      "Mention to capabilities command not found")

    @fail_on(process.CmdError)
    def test_capabilities(self):
        cmd = "%s capabilities" % self.get_runner()
        result = process.run(cmd)
        capabilities = json.loads(result.stdout_text)
        self.assertIn("runnables", capabilities)
        self.assertIn("commands", capabilities)

    def test_runnable_run_no_args(self):
        cmd = "%s runnable-run" % self.get_runner()
        result = process.run(cmd, ignore_status=True)
        expected = self.params.get('runnable-run-no-args-exit-code',
                                   default=2)
        self.assertEqual(result.exit_status, expected)

    def test_runnable_run_uri_only(self):
        cmd = "%s runnable-run -u some_uri" % self.get_runner()
        result = process.run(cmd, ignore_status=True)
        expected = self.params.get('runnable-run-uri-only-exit-code',
                                   default=2)
        self.assertEqual(result.exit_status, expected)
