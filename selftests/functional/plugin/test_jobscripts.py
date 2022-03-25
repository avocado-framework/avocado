import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

SCRIPT_PRE_TOUCH = """#!/bin/sh -e
touch %s"""

TEST_CHECK_TOUCH = """#!/bin/sh -e
test -f %s"""

SCRIPT_POST_RM = """#!/bin/sh -e
rm %s"""

SCRIPT_PRE_POST_CFG = """[plugins.jobscripts]
pre = %s
post = %s
warn_non_existing_dir = True
warn_non_zero_status = True"""

SCRIPT_NON_EXISTING_DIR_CFG = """[plugins.jobscripts]
pre = %s
warn_non_existing_dir = True
warn_non_zero_status = False"""

SCRIPT_NON_ZERO_STATUS = """#!/bin/sh
exit 1"""

SCRIPT_NON_ZERO_CFG = """[plugins.jobscripts]
pre = %s
warn_non_existing_dir = False
warn_non_zero_status = True"""


class JobScriptsTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.pre_dir = os.path.join(self.tmpdir.name, 'pre.d')
        os.mkdir(self.pre_dir)
        self.post_dir = os.path.join(self.tmpdir.name, 'post.d')
        os.mkdir(self.post_dir)

    def test_pre_post(self):
        """
        Runs both pre and post scripts and makes sure both execute properly
        """
        touch_script = script.Script(os.path.join(self.pre_dir,
                                                  'touch.sh'),
                                     SCRIPT_PRE_TOUCH)
        touch_script.save()
        test_check_touch = script.Script(os.path.join(self.tmpdir.name,
                                                      'check_touch.sh'),
                                         TEST_CHECK_TOUCH)
        test_check_touch.save()
        rm_script = script.Script(os.path.join(self.post_dir,
                                               'rm.sh'),
                                  SCRIPT_POST_RM)
        rm_script.save()
        config = script.TemporaryScript("pre_post.conf",
                                        SCRIPT_PRE_POST_CFG % (self.pre_dir,
                                                               self.post_dir))
        with config:
            cmd = (f'{AVOCADO} --config {config} run '
                   f'--job-results-dir {self.tmpdir.name} '
                   f'--disable-sysinfo {test_check_touch}')
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn(f'Pre job script "{touch_script}" exited with status "1"',
                         result.stderr_text)
        self.assertNotIn(f'Post job script "{rm_script}" exited with status "1"',
                         result.stderr_text)

    def test_status_non_zero(self):
        """
        Checks warning when script returns non-zero status
        """
        non_zero_script = script.Script(os.path.join(self.pre_dir,
                                                     'non_zero.sh'),
                                        SCRIPT_NON_ZERO_STATUS)
        non_zero_script.save()
        config = script.TemporaryScript("non_zero.conf",
                                        SCRIPT_NON_ZERO_CFG % self.pre_dir)
        with config:
            cmd = (f'{AVOCADO} --config {config} run '
                   f'--job-results-dir {self.tmpdir.name} '
                   f'--disable-sysinfo examples/tests/passtest.py')
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(f'Pre job script "{non_zero_script}" exited with status "1\"\n',
                      result.stderr_text)

    def test_non_existing_dir(self):
        """
        Checks warning with non existing pre dir
        """
        non_zero_script = script.Script(os.path.join(self.pre_dir,
                                                     'non_zero.sh'),
                                        SCRIPT_NON_ZERO_STATUS)
        non_zero_script.save()

        self.pre_dir = '/non/existing/dir'
        config = script.TemporaryScript("non_existing_dir.conf",
                                        SCRIPT_NON_EXISTING_DIR_CFG % self.pre_dir)
        with config:
            cmd = (f'{AVOCADO} --config {config} run '
                   f'--job-results-dir {self.tmpdir.name} '
                   f'--disable-sysinfo examples/tests/passtest.py')
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'-job scripts has not been found', result.stderr)
        self.assertNotIn(f'Pre job script "{non_zero_script}" exited with status "1"',
                         result.stderr_text)


if __name__ == '__main__':
    unittest.main()
