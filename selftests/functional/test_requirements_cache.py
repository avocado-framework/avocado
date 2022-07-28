import os
import unittest.mock

from avocado.core.dependencies.requirements import cache
from selftests.utils import TestCaseTmpDir

ENTRIES = [
    (
        "podman",
        "cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e",
        "package",
        "bash",
    ),
    (
        "podman",
        "cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e",
        "package",
        "hello",
    ),
    (
        "podman",
        "ad34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e",
        "package",
        "hello",
    ),
    (
        "podman",
        "cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e",
        "core",
        "avocado",
    ),
    ("local", "localhost.localdomain", "core", "avocado"),
    (
        "podman",
        "pd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e",
        "package",
        "foo",
        0,
    ),
]


class Cache(TestCaseTmpDir):
    def test_entries(self):
        with unittest.mock.patch(
            "avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH",
            os.path.join(self.tmpdir.name, "requirements.sqlite"),
        ):
            for entry in ENTRIES[:-1]:
                cache.set_requirement(*entry)
                self.assertTrue(cache.is_requirement_in_cache(*entry))
            entry = ENTRIES[-1]
            cache.set_requirement(*entry)
            self.assertIsNone(
                cache.is_requirement_in_cache(entry[0], entry[1], entry[2], entry[3])
            )
            self.assertFalse(
                cache.is_requirement_in_cache(
                    "local", "localhost.localdomain", "package", "foo"
                )
            )

    def test_empty(self):
        with unittest.mock.patch(
            "avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH",
            os.path.join(self.tmpdir.name, "requirements.sqlite"),
        ):
            self.assertFalse(cache.is_requirement_in_cache(*ENTRIES[0]))

    def test_is_environment_prepared(self):
        with unittest.mock.patch(
            "avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH",
            os.path.join(self.tmpdir.name, "requirements.sqlite"),
        ):
            for entry in ENTRIES:
                cache.set_requirement(*entry)
            self.assertFalse(
                cache.is_environment_prepared(
                    "pd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e"
                )
            )
            self.assertTrue(
                cache.is_environment_prepared(
                    "cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e"
                )
            )

    def test_get_all_environments_with_requirement(self):
        with unittest.mock.patch(
            "avocado.core.dependencies.requirements.cache.backends.sqlite.CACHE_DATABASE_PATH",
            os.path.join(self.tmpdir.name, "requirements.sqlite"),
        ):
            for entry in ENTRIES:
                cache.set_requirement(*entry)
            all_requirements = cache.get_all_environments_with_requirement(
                "podman", "package", "hello"
            )
            expected_data = {
                "ad34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e": [
                    ("package", "hello")
                ],
                "cd34d13b2980d0a9d438f754b2e94f85443076d0ebe1b0db09a0439f35feca5e": [
                    ("core", "avocado"),
                    ("package", "bash"),
                    ("package", "hello"),
                ],
            }
            self.assertEqual(all_requirements, expected_data)
