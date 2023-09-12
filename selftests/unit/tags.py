import os
import stat
import unittest

from avocado.core import resolver, tags
from avocado.utils import script
from selftests.utils import BASEDIR

#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
)


AVOCADO_TEST_OK = """from avocado import Test

class PassTest(Test):
    def test(self):
        pass
"""

AVOCADO_TEST_TAGS_INHERITANCE = """import avocado


class Base(avocado.Test):
    '''
    :avocado: tags=foo
    '''
    def test_one(self):
        pass

    def test_two(self):
        '''
        :avocado: tags=boo
        '''
        pass


class Derived(Base):
    '''
    :avocado: tags=moo
    '''

    def test_two(self):
        pass

    def test_three(self):
        pass

class DerivedTwo(Derived):
    '''
    :avocado: tags=zoo
    '''
"""


class TagFilter(unittest.TestCase):
    def setUp(self):
        tags_example = os.path.join(BASEDIR, "examples", "tests", "tags.py")
        self.result = resolver.resolve([tags_example])
        self.input_file_path = tags_example

    def test_no_tag_filter(self):
        self.assertEqual(len(self.result), 1)
        self.assertEqual(
            self.result[0].result, resolver.ReferenceResolutionResult.SUCCESS
        )
        self.assertEqual(len(self.result[0].resolutions), 8)
        self.assertEqual(
            self.result[0].resolutions[0].uri,
            f"{self.input_file_path}:FastTest.test_fast",
        )
        self.assertEqual(
            self.result[0].resolutions[1].uri,
            f"{self.input_file_path}:FastTest.test_fast_other",
        )
        self.assertEqual(
            self.result[0].resolutions[2].uri,
            f"{self.input_file_path}:SlowTest.test_slow",
        )
        self.assertEqual(
            self.result[0].resolutions[3].uri,
            f"{self.input_file_path}:SlowUnsafeTest.test_slow_unsafe",
        )
        self.assertEqual(
            self.result[0].resolutions[4].uri,
            f"{self.input_file_path}:SafeTest.test_safe",
        )
        self.assertEqual(
            self.result[0].resolutions[5].uri,
            f"{self.input_file_path}:SafeX86Test.test_safe_x86",
        )
        self.assertEqual(
            self.result[0].resolutions[6].uri,
            f"{self.input_file_path}:NoTagsTest.test_no_tags",
        )
        self.assertEqual(
            self.result[0].resolutions[7].uri,
            f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64",
        )

    def test_filter_fast_net(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["fast,net"], False, False
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )

    def test_filter_fast_net_include_empty(self):
        filtered = tags.filter_tags_on_runnables(self.result, ["fast,net"], True, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )
        self.assertEqual(
            filtered[2].uri, f"{self.input_file_path}:NoTagsTest.test_no_tags"
        )

    def test_filter_arch(self):
        filtered = tags.filter_tags_on_runnables(self.result, ["arch"], False, False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(
            filtered[0].uri, f"{self.input_file_path}:SafeX86Test.test_safe_x86"
        )
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64"
        )

    def test_filter_arch_include_empty(self):
        filtered = tags.filter_tags_on_runnables(self.result, ["arch"], True, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(
            filtered[0].uri, f"{self.input_file_path}:SafeX86Test.test_safe_x86"
        )
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:NoTagsTest.test_no_tags"
        )
        self.assertEqual(
            filtered[2].uri, f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64"
        )

    def test_filter_arch_x86_64(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["arch:x86_64"], False, False
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(
            filtered[0].uri, f"{self.input_file_path}:SafeX86Test.test_safe_x86"
        )

    def test_filter_arch_other(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["arch:ppc64"], False, False
        )
        self.assertEqual(len(filtered), 0)

    def test_filter_arch_other_include_empty_key(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["arch:ppc64"], False, True
        )
        self.assertEqual(len(filtered), 5)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )
        self.assertEqual(filtered[2].uri, f"{self.input_file_path}:SlowTest.test_slow")
        self.assertEqual(
            filtered[3].uri, f"{self.input_file_path}:SlowUnsafeTest.test_slow_unsafe"
        )
        self.assertEqual(filtered[4].uri, f"{self.input_file_path}:SafeTest.test_safe")

    def test_filter_arch_other_include_empty_flat_and_key(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["arch:ppc64"], True, True
        )
        self.assertEqual(len(filtered), 6)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )
        self.assertEqual(filtered[2].uri, f"{self.input_file_path}:SlowTest.test_slow")
        self.assertEqual(
            filtered[3].uri, f"{self.input_file_path}:SlowUnsafeTest.test_slow_unsafe"
        )
        self.assertEqual(filtered[4].uri, f"{self.input_file_path}:SafeTest.test_safe")
        self.assertEqual(
            filtered[5].uri, f"{self.input_file_path}:NoTagsTest.test_no_tags"
        )

    def test_filter_fast_net__slow_disk_unsafe(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["fast,net", "slow,disk,unsafe"], False, False
        )
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )
        self.assertEqual(
            filtered[2].uri, f"{self.input_file_path}:SlowUnsafeTest.test_slow_unsafe"
        )

    def test_filter_fast_net__slow_disk(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["fast,net", "slow,disk"], False, False
        )
        self.assertEqual(len(filtered), 4)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:FastTest.test_fast")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:FastTest.test_fast_other"
        )
        self.assertEqual(filtered[2].uri, f"{self.input_file_path}:SlowTest.test_slow")
        self.assertEqual(
            filtered[3].uri, f"{self.input_file_path}:SlowUnsafeTest.test_slow_unsafe"
        )

    def test_filter_not_fast_not_slow(self):
        filtered = tags.filter_tags_on_runnables(self.result, ["-fast,-slow"], False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:SafeTest.test_safe")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:SafeX86Test.test_safe_x86"
        )
        self.assertEqual(
            filtered[2].uri, f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64"
        )

    def test_filter_not_fast_not_slow_include_empty(self):
        filtered = tags.filter_tags_on_runnables(self.result, ["-fast,-slow"], True)
        self.assertEqual(len(filtered), 4)
        self.assertEqual(filtered[0].uri, f"{self.input_file_path}:SafeTest.test_safe")
        self.assertEqual(
            filtered[1].uri, f"{self.input_file_path}:SafeX86Test.test_safe_x86"
        )
        self.assertEqual(
            filtered[2].uri, f"{self.input_file_path}:NoTagsTest.test_no_tags"
        )
        self.assertEqual(
            filtered[3].uri, f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64"
        )

    def test_filter_safe_arch_not_x86_64(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["safe,arch:-x86_64"], False
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(
            filtered[0].uri, f"{self.input_file_path}:SafeAarch64Test.test_safe_aarch64"
        )

    def test_filter_not_fast_not_slow_not_safe(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["-fast,-slow,-safe"], False
        )
        self.assertEqual(len(filtered), 0)

    def test_filter_not_fast_not_slow_not_safe_others_dont_exist(self):
        filtered = tags.filter_tags_on_runnables(
            self.result, ["-fast,-slow,-safe", "does,not,exist"], False
        )
        self.assertEqual(len(filtered), 0)

    def test_load_tags(self):
        tags_map = {
            "FastTest.test_fast": {"fast": None, "net": None},
            "FastTest.test_fast_other": {"fast": None, "net": None},
            "SlowTest.test_slow": {"slow": None, "disk": None},
            "SlowUnsafeTest.test_slow_unsafe": {
                "slow": None,
                "disk": None,
                "unsafe": None,
            },
            "SafeTest.test_safe": {"safe": None},
            "SafeX86Test.test_safe_x86": {"safe": None, "arch": set(["x86_64"])},
            "NoTagsTest.test_no_tags": {},
            "SafeAarch64Test.test_safe_aarch64": {
                "safe": None,
                "arch": set(["aarch64"]),
            },
        }

        for runnable in self.result[0].resolutions:
            name = runnable.uri.split(":", 1)[1]
            self.assertEqual(runnable.tags, tags_map[name])
            del tags_map[name]
        self.assertEqual(len(tags_map), 0)


class TagFilter2(unittest.TestCase):
    def setUp(self):
        with script.TemporaryScript(
            "passtest.py",
            AVOCADO_TEST_OK,
            "avocado_resolver_tag_unittest",
            DEFAULT_NON_EXEC_MODE,
        ) as test_script:
            self.result = resolver.resolve([test_script.path])
            self.input_file_path = test_script.path

    def test_filter_tags_include_empty(self):
        self.assertEqual(
            tags.filter_tags_on_runnables(self.result, [], False, False), []
        )
        self.assertEqual(
            tags.filter_tags_on_runnables(self.result, [], True, False),
            self.result[0].resolutions,
        )


class TagInheritance(unittest.TestCase):
    def setUp(self):
        with script.TemporaryScript(
            "passtest.py",
            AVOCADO_TEST_TAGS_INHERITANCE,
            "avocado_resolver_tag_unittest",
            DEFAULT_NON_EXEC_MODE,
        ) as test_script:
            self.result = resolver.resolve([test_script.path])
            self.input_file_path = test_script.path

    def test_filter_tags_inheritance(self):
        """
        Checks if tags from parent class are respected.
        """
        foo_tag = tags.filter_tags_on_runnables(self.result, ["foo"], False, False)
        self.assertEqual(len(foo_tag), 8)
        self.assertEqual(foo_tag[0].uri, f"{self.input_file_path}:Base.test_one")
        self.assertEqual(foo_tag[1].uri, f"{self.input_file_path}:Base.test_two")
        self.assertEqual(foo_tag[2].uri, f"{self.input_file_path}:Derived.test_two")
        self.assertEqual(foo_tag[3].uri, f"{self.input_file_path}:Derived.test_three")
        self.assertEqual(foo_tag[4].uri, f"{self.input_file_path}:Derived.test_one")
        self.assertEqual(foo_tag[5].uri, f"{self.input_file_path}:DerivedTwo.test_two")
        self.assertEqual(
            foo_tag[6].uri, f"{self.input_file_path}:DerivedTwo.test_three"
        )
        self.assertEqual(foo_tag[7].uri, f"{self.input_file_path}:DerivedTwo.test_one")

        moo_tag = tags.filter_tags_on_runnables(self.result, ["moo"], False, False)
        self.assertEqual(len(moo_tag), 6)
        self.assertEqual(moo_tag[0].uri, f"{self.input_file_path}:Derived.test_two")
        self.assertEqual(moo_tag[1].uri, f"{self.input_file_path}:Derived.test_three")
        self.assertEqual(moo_tag[2].uri, f"{self.input_file_path}:Derived.test_one")
        self.assertEqual(moo_tag[3].uri, f"{self.input_file_path}:DerivedTwo.test_two")
        self.assertEqual(
            moo_tag[4].uri, f"{self.input_file_path}:DerivedTwo.test_three"
        )
        self.assertEqual(moo_tag[5].uri, f"{self.input_file_path}:DerivedTwo.test_one")

        boo_tag = tags.filter_tags_on_runnables(self.result, ["boo"], False, False)
        self.assertEqual(len(boo_tag), 3)
        self.assertEqual(boo_tag[0].uri, f"{self.input_file_path}:Base.test_two")
        self.assertEqual(boo_tag[1].uri, f"{self.input_file_path}:Derived.test_two")
        self.assertEqual(boo_tag[2].uri, f"{self.input_file_path}:DerivedTwo.test_two")


class ParseFilterByTags(unittest.TestCase):
    def test_must(self):
        self.assertEqual(
            tags._parse_filter_by_tags(["foo,bar,baz"]),
            [(set(["foo", "bar", "baz"]), set([]))],
        )

    def test_must_must_not(self):
        self.assertEqual(
            tags._parse_filter_by_tags(["foo,-bar,baz"]),
            [(set(["foo", "baz"]), set(["bar"]))],
        )

    def test_musts_must_nots(self):
        self.assertEqual(
            tags._parse_filter_by_tags(["foo,bar,baz", "-FOO,-BAR,-BAZ"]),
            [
                (set(["foo", "bar", "baz"]), set([])),
                (set([]), set(["FOO", "BAR", "BAZ"])),
            ],
        )
