import os
import unittest.mock

from avocado.core.dependencies.requirements import cache
from selftests.utils import TestCaseTmpDir

ENTRIES = [
    ('podman',
     'cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e',
     'package',
     'bash'),
    ('podman',
     'cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e',
     'core',
     'avocado'),
    ('local',
     'localhost.localdomain',
     'core',
     'avocado')
    ]


class Cache(TestCaseTmpDir):

    def test_entries(self):
        with unittest.mock.patch(
                'avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH',
                os.path.join(self.tmpdir.name,
                             'requirements.sqlite')):
            for entry in ENTRIES:
                cache.set_requirement(*entry)
                self.assertTrue(cache.get_requirement(*entry))

    def test_empty(self):
        with unittest.mock.patch(
                'avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH',
                os.path.join(self.tmpdir.name,
                             'requirements.sqlite')):
            self.assertFalse(cache.get_requirement(*ENTRIES[0]))
