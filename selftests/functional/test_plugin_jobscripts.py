import os
import shutil
import sys
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script


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


class JobScriptsTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.pre_dir = os.path.join(self.tmpdir, 'pre.d')
        os.mkdir(self.pre_dir)
        self.post_dir = os.path.join(self.tmpdir, 'post.d')
        os.mkdir(self.post_dir)

    def test_pre_post(self):
        """
        Runs both pre and post scripts and makes sure both execute properly
        """
        touch_script = script.Script(os.path.join(self.pre_dir,
                                                  'touch.sh'),
                                     SCRIPT_PRE_TOUCH)
        touch_script.save()
        test_check_touch = script.Script(os.path.join(self.tmpdir,
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
            cmd = './scripts/avocado --config %s run %s' % (config,
                                                            test_check_touch)
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn('Pre job script "%s" exited with status "1"' % touch_script,
                         result.stderr)
        self.assertNotIn('Post job script "%s" exited with status "1"' % rm_script,
                         result.stderr)

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
            cmd = './scripts/avocado --config %s run passtest.py' % config
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual('Pre job script "%s" exited with status "1"\n' % non_zero_script,
                         result.stderr)

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
            cmd = './scripts/avocado --config %s run passtest.py' % config
            result = process.run(cmd)

        # Pre/Post scripts failures do not (currently?) alter the exit status
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn('-job scripts has not been found', result.stderr)
        self.assertNotIn('Pre job script "%s" exited with status "1"' % non_zero_script,
                         result.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
