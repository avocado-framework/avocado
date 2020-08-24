import os
import unittest.mock

from avocado.core import requirements

from .. import TestCaseTmpDir

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


class Requirement(TestCaseTmpDir):

    def test_entries(self):
        with unittest.mock.patch('avocado.core.requirements.CACHE_DATABASE_PATH',
                                 os.path.join(self.tmpdir.name,
                                              'requirements.sqlite')):
            for entry in ENTRIES:
                requirements.set_requirement_on_cache(*entry)
                self.assertTrue(requirements.get_requirement_on_cache(*entry))

    def test_empty(self):
        with unittest.mock.patch('avocado.core.requirements.CACHE_DATABASE_PATH',
                                 os.path.join(self.tmpdir.name,
                                              'requirements.sqlite')):
            self.assertFalse(requirements.get_requirement_on_cache(*ENTRIES[0]))
