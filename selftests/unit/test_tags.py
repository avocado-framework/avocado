import stat
import unittest

from avocado.core import loader, tags
from avocado.core.nrunner.runnable import Runnable
from avocado.utils import script

#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)


AVOCADO_TEST_TAGS = """#!/usr/bin/env python
from avocado import Test
from avocado import main

import time

class DisabledTest(Test):
    '''
    :avocado: disable
    :avocado: tags=fast,net
    '''
    def test_disabled(self):
        pass

class FastTest(Test):
    '''
    :avocado: tags=fast
    '''
    def test_fast(self):
        '''
        :avocado: tags=net
        '''
        pass

    def test_fast_other(self):
        '''
        :avocado: tags=net
        '''
        pass

class SlowTest(Test):
    '''
    :avocado: tags=slow,disk
    '''
    def test_slow(self):
        time.sleep(1)

class SlowUnsafeTest(Test):
    '''
    :avocado: tags=slow,disk,unsafe
    '''
    def test_slow_unsafe(self):
        time.sleep(1)

class SafeTest(Test):
    '''
    :avocado: tags=safe
    '''
    def test_safe(self):
        pass

class SafeX86Test(Test):
    '''
    :avocado: tags=safe,arch:x86_64
    '''
    def test_safe_x86(self):
        pass

class NoTagsTest(Test):
    def test_no_tags(self):
        pass

class SafeAarch64Test(Test):
    '''
    :avocado: tags=safe,arch:aarch64
    '''
    def test_safe_aarch64(self):
        pass

if __name__ == "__main__":
    main()
"""


AVOCADO_TEST_OK = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""


class TagFilter(unittest.TestCase):

    def setUp(self):
        with script.TemporaryScript('tags.py',
                                    AVOCADO_TEST_TAGS,
                                    'avocado_loader_unittest',
                                    DEFAULT_NON_EXEC_MODE) as test_script:
            this_loader = loader.FileLoader(None, {})
            self.test_suite = this_loader.discover(test_script.path,
                                                   loader.DiscoverMode.ALL)

    def test_no_tag_filter(self):
        self.assertEqual(len(self.test_suite), 8)
        self.assertEqual(self.test_suite[0][0], 'FastTest')
        self.assertEqual(self.test_suite[0][1]['methodName'], 'test_fast')
        self.assertEqual(self.test_suite[1][0], 'FastTest')
        self.assertEqual(self.test_suite[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(self.test_suite[2][0], 'SlowTest')
        self.assertEqual(self.test_suite[2][1]['methodName'], 'test_slow')
        self.assertEqual(self.test_suite[3][0], 'SlowUnsafeTest')
        self.assertEqual(self.test_suite[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(self.test_suite[4][0], 'SafeTest')
        self.assertEqual(self.test_suite[4][1]['methodName'], 'test_safe')
        self.assertEqual(self.test_suite[5][0], 'SafeX86Test')
        self.assertEqual(self.test_suite[5][1]['methodName'], 'test_safe_x86')
        self.assertEqual(self.test_suite[6][0], 'NoTagsTest')
        self.assertEqual(self.test_suite[6][1]['methodName'], 'test_no_tags')
        self.assertEqual(self.test_suite[7][0], 'SafeAarch64Test')
        self.assertEqual(self.test_suite[7][1]['methodName'], 'test_safe_aarch64')

    def test_filter_fast_net(self):
        filtered = tags.filter_test_tags(self.test_suite, ['fast,net'], False, False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')

    def test_filter_fast_net_include_empty(self):
        filtered = tags.filter_test_tags(self.test_suite, ['fast,net'], True, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'NoTagsTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_no_tags')

    def test_filter_arch(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch'], False, False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[1][0], 'SafeAarch64Test')
        self.assertEqual(filtered[1][1]['methodName'], 'test_safe_aarch64')

    def test_filter_arch_include_empty(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch'], True, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[1][0], 'NoTagsTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_no_tags')
        self.assertEqual(filtered[2][0], 'SafeAarch64Test')
        self.assertEqual(filtered[2][1]['methodName'], 'test_safe_aarch64')

    def test_filter_arch_x86_64(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch:x86_64'], False, False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')

    def test_filter_arch_other(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch:ppc64'], False, False)
        self.assertEqual(len(filtered), 0)

    def test_filter_arch_other_include_empty_key(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch:ppc64'], False, True)
        self.assertEqual(len(filtered), 5)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(filtered[4][0], 'SafeTest')
        self.assertEqual(filtered[4][1]['methodName'], 'test_safe')

    def test_filter_arch_other_include_empty_flat_and_key(self):
        filtered = tags.filter_test_tags(self.test_suite, ['arch:ppc64'], True, True)
        self.assertEqual(len(filtered), 6)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(filtered[4][0], 'SafeTest')
        self.assertEqual(filtered[4][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[5][0], 'NoTagsTest')
        self.assertEqual(filtered[5][1]['methodName'], 'test_no_tags')

    def test_filter_fast_net__slow_disk_unsafe(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['fast,net',
                                          'slow,disk,unsafe'],
                                         False, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow_unsafe')

    def test_filter_fast_net__slow_disk(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['fast,net',
                                          'slow,disk'],
                                         False, False)
        self.assertEqual(len(filtered), 4)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')

    def test_filter_not_fast_not_slow(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['-fast,-slow'],
                                         False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'SafeTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[1][0], 'SafeX86Test')
        self.assertEqual(filtered[1][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[2][0], 'SafeAarch64Test')
        self.assertEqual(filtered[2][1]['methodName'], 'test_safe_aarch64')

    def test_filter_not_fast_not_slow_include_empty(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['-fast,-slow'],
                                         True)
        self.assertEqual(len(filtered), 4)
        self.assertEqual(filtered[0][0], 'SafeTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[1][0], 'SafeX86Test')
        self.assertEqual(filtered[1][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[2][0], 'NoTagsTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_no_tags')
        self.assertEqual(filtered[3][0], 'SafeAarch64Test')
        self.assertEqual(filtered[3][1]['methodName'], 'test_safe_aarch64')

    def test_filter_safe_arch_not_x86_64(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['safe,arch:-x86_64'],
                                         False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 'SafeAarch64Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_aarch64')

    def test_filter_not_fast_not_slow_not_safe(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['-fast,-slow,-safe'],
                                         False)
        self.assertEqual(len(filtered), 0)

    def test_filter_not_fast_not_slow_not_safe_others_dont_exist(self):
        filtered = tags.filter_test_tags(self.test_suite,
                                         ['-fast,-slow,-safe',
                                          'does,not,exist'],
                                         False)
        self.assertEqual(len(filtered), 0)

    def test_load_tags(self):
        tags_map = {
            'FastTest.test_fast': {'fast': None, 'net': None},
            'FastTest.test_fast_other': {'fast': None, 'net': None},
            'SlowTest.test_slow': {'slow': None, 'disk': None},
            'SlowUnsafeTest.test_slow_unsafe': {'slow': None,
                                                'disk': None,
                                                'unsafe': None},
            'SafeTest.test_safe': {'safe': None},
            'SafeX86Test.test_safe_x86': {'safe': None,
                                          'arch': set(['x86_64'])},
            'NoTagsTest.test_no_tags': {},
            'SafeAarch64Test.test_safe_aarch64': {'safe': None,
                                                  'arch': set(['aarch64'])}
        }

        for _, info in self.test_suite:
            name = info['name'].split(':', 1)[1]
            self.assertEqual(info['tags'], tags_map[name])
            del(tags_map[name])
        self.assertEqual(len(tags_map), 0)


class TagFilter2(unittest.TestCase):

    def test_filter_tags_include_empty(self):
        with script.TemporaryScript('passtest.py',
                                    AVOCADO_TEST_OK,
                                    'avocado_loader_unittest',
                                    DEFAULT_NON_EXEC_MODE) as test_script:
            this_loader = loader.FileLoader(None, {})
            test_suite = this_loader.discover(test_script.path,
                                              loader.DiscoverMode.ALL)
        self.assertEqual([], tags.filter_test_tags(test_suite, [], False, False))
        self.assertEqual(test_suite,
                         tags.filter_test_tags(test_suite, [], True, False))


class ParseFilterByTags(unittest.TestCase):

    def test_must(self):
        self.assertEqual(tags._parse_filter_by_tags(['foo,bar,baz']),
                         [(set(['foo', 'bar', 'baz']), set([]))])

    def test_must_must_not(self):
        self.assertEqual(tags._parse_filter_by_tags(['foo,-bar,baz']),
                         [(set(['foo', 'baz']), set(['bar']))])

    def test_musts_must_nots(self):
        self.assertEqual(tags._parse_filter_by_tags(['foo,bar,baz',
                                                     '-FOO,-BAR,-BAZ']),
                         [(set(['foo', 'bar', 'baz']), set([])),
                          (set([]), set(['FOO', 'BAR', 'BAZ']))])


class FilterRunnable(unittest.TestCase):

    def test_no_tags(self):
        runnable = Runnable('noop', None)
        self.assertFalse(tags.filter_test_tags_runnable(runnable, []))
