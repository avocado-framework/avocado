import os
import unittest

from avocado import Test, skipUnless
from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO

SINGLE_SUCCESS_CHECK = '''#!/usr/bin/env python3

from avocado import Test


class SuccessTest(Test):

    def test_check(self):
        """
        :avocado: dependency={"type": "package", "name": "bash", "action": "check"}
        """
'''

SINGLE_FAIL_CHECK = '''#!/usr/bin/env python3

from avocado import Test


class FailTest(Test):

    def test_check(self):
        """
        :avocado: dependency={"type": "package", "name": "-foo-bar-", "action": "check"}
        """
'''

MULTIPLE_SUCCESS = '''#!/usr/bin/env python3

from avocado import Test
from avocado.utils import process


class SuccessTest(Test):

    def check_hello(self):
        result = process.run("hello", ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertIn('Hello, world!', result.stdout_text,)

    def test_a(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
        self.check_hello()

    def test_b(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
        self.check_hello()

    def test_c(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
        self.check_hello()
'''

MULTIPLE_FAIL = '''#!/usr/bin/env python3

from avocado import Test
from avocado.utils import process


class FailTest(Test):

    def test_a(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        :avocado: dependency={"type": "package", "name": "-foo-bar-"}
        """
    def test_b(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
        result = process.run("hello", ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertIn('Hello, world!', result.stdout_text,)

    def test_c(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        :avocado: dependency={"type": "package", "name": "-foo-bar-"}
        """
'''


class BasicTest(Test):

    """
    :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
    """

    skip_install_message = (
        "This test runs on CI environments only as it"
        " installs packages to test the feature, which"
        " may not be desired locally, in the user's"
        " system."
    )
    skip_package_manager_message = (
        "This test runs on CI environments only"
        " as it depends on the system package"
        " manager, and some environments don't"
        " have it available."
    )

    def get_command(self, path):
        spawner = self.params.get("spawner", default="process")
        spawner_command = ""
        if spawner == "podman":
            spawner_command = "--spawner=podman --spawner-podman-image=fedora:36"
        return (
            f"{AVOCADO} run {spawner_command} --job-results-dir {self.workdir} {path}"
        )

    @skipUnless(os.getenv("CI"), skip_package_manager_message)
    def test_single_success(self):
        with script.Script(
            os.path.join(self.workdir, "test_single_success.py"), SINGLE_SUCCESS_CHECK
        ) as test:
            command = self.get_command(test.path)
            result = process.run(command, ignore_status=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(
                "PASS 1",
                result.stdout_text,
            )
            self.assertNotIn(
                "bash",
                result.stdout_text,
            )

    @skipUnless(os.getenv("CI"), skip_package_manager_message)
    def test_single_fail(self):
        with script.Script(
            os.path.join(self.workdir, "test_single_fail.py"), SINGLE_FAIL_CHECK
        ) as test:
            command = self.get_command(test.path)
            result = process.run(command, ignore_status=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(
                "PASS 0",
                result.stdout_text,
            )
            self.assertIn(
                "SKIP 1",
                result.stdout_text,
            )
            self.assertNotIn(
                "-foo-bar-",
                result.stdout_text,
            )

    @skipUnless(os.getenv("CI"), skip_install_message)
    def test_multiple_success(self):
        with script.Script(
            os.path.join(self.workdir, "test_multiple_success.py"), MULTIPLE_SUCCESS
        ) as test:
            command = self.get_command(test.path)
            result = process.run(command, ignore_status=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(
                "PASS 3",
                result.stdout_text,
            )
            self.assertNotIn(
                "vim-common",
                result.stdout_text,
            )

    @skipUnless(os.getenv("CI"), skip_install_message)
    def test_multiple_fails(self):
        with script.Script(
            os.path.join(self.workdir, "test_multiple_fail.py"), MULTIPLE_FAIL
        ) as test:
            command = self.get_command(test.path)
            result = process.run(command, ignore_status=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(
                "PASS 1",
                result.stdout_text,
            )
            self.assertIn(
                "SKIP 2",
                result.stdout_text,
            )
            self.assertNotIn(
                "-foo-bar-",
                result.stdout_text,
            )


if __name__ == "__main__":
    unittest.main()
