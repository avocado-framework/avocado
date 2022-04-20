import os
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.core.settings import settings
from avocado.plugins.runners.sysinfo import SysinfoRunner


class BasicTests(unittest.TestCase):
    """Basic unit tests for the RequirementPackageRunner class"""

    def in_message_path(self, messages, path, sysinfo_type='pre'):
        path = os.path.join('sysinfo', sysinfo_type, path)
        for message in messages:
            if message.get('path', '') == path:
                return True
        return False

    def test_pre(self):
        kwargs = {'sysinfo': {'commands': ['uptime', 'dmidecode'],
                              'files': ['/proc/version', '/proc/meminfo']}}
        runnable = Runnable('sysinfo', 'pre', **kwargs,
                            config=settings.as_dict())
        runner = SysinfoRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertTrue(self.in_message_path(messages, 'uptime'))
        self.assertTrue(self.in_message_path(messages, 'dmidecode'))
        self.assertTrue(self.in_message_path(messages, 'meminfo'))
        self.assertTrue(self.in_message_path(messages, 'version'))

    def test_post_fail(self):
        kwargs = {'sysinfo': {'fail_commands': ['uptime', 'dmidecode'],
                              'fail_files': ['/proc/version', '/proc/meminfo']},
                  'test_fail': True}
        runnable = Runnable('sysinfo', 'post', **kwargs,
                            config=settings.as_dict())
        runner = SysinfoRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertTrue(self.in_message_path(messages, 'uptime', 'post'))
        self.assertTrue(self.in_message_path(messages, 'dmidecode', 'post'))
        self.assertTrue(self.in_message_path(messages, 'meminfo', 'post'))
        self.assertTrue(self.in_message_path(messages, 'version', 'post'))
