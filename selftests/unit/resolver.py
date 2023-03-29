import os
import stat
import unittest.mock

from avocado.core import resolver
from avocado.utils import script

#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
)


class SnippetTestCase(unittest.TestCase):
    def setUp(self):
        self.input_test_file = script.TemporaryScript(
            "test.py", self.SNIPPET, mode=DEFAULT_NON_EXEC_MODE
        )
        self.input_test_file.save()

    def tearDown(self):
        self.input_test_file.remove()


class MultipleMethods(SnippetTestCase):

    SNIPPET = """from avocado import Test

class MultipleMethods(Test):
    def test_one(self):
        pass
    def testTwo(self):
        pass
    def foo(self):
        pass
    """

    def test_bare(self):
        """Tests a bare resolution (with no filter qualifier)"""
        reference = self.input_test_file.path
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 2)

    def test_some(self):
        """Tries to resolve only some of the tests"""
        reference = f"{self.input_test_file.path}:MultipleMethods.testTwo"
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 1)

    def test_regex(self):
        """Tests resolution with a regex filter"""
        reference = f"{self.input_test_file.path}:.*_one"
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 1)
        self.assertEqual(
            result[0].resolutions[0].uri,
            f"{self.input_test_file.path}:MultipleMethods.test_one",
        )

    def test_regex_all(self):
        """Tests resolution with a regex that matches all tests"""
        reference = f"{self.input_test_file.path}:test.*"
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 2)
        self.assertEqual(
            result[0].resolutions[0].uri,
            f"{self.input_test_file.path}:MultipleMethods.test_one",
        )
        self.assertEqual(
            result[0].resolutions[1].uri,
            f"{self.input_test_file.path}:MultipleMethods.testTwo",
        )

    def test_regex_none(self):
        """Tests resolution with a regex that matches all tests"""
        reference = f"{self.input_test_file.path}:no_match.*"
        result = resolver.resolve([reference])
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(len(result[0].resolutions), 0)
        self.assertEqual(result[-1].result, resolver.ReferenceResolutionResult.NOTFOUND)


class MultipleMethodsSameName(SnippetTestCase):

    SNIPPET = """from avocado import Test

class MultipleMethods(Test):
    def test(self):
        raise
    def test(self):
        raise
    def test(self):
        pass
    """

    def test(self):
        """Tests that multiple test methods are seen as just one"""
        reference = f"{self.input_test_file.path}:MultipleMethods.test"
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 1)
        self.assertEqual(result[0].resolutions[0].uri, reference)


class ForeignTaggedEnable(SnippetTestCase):

    SNIPPET = """from foreignlib import Base

class First(Base):
    '''
    First actual test based on library base class

    This Base class happens to, fictionally, inherit from avocado.Test. Because
    Avocado can't tell that, a tag is necessary to signal that.

    :avocado: enable
    '''
    def test(self):
        pass
    """

    def test(self):
        """Checks that an enabled foreign base class's tests are seen"""
        reference = self.input_test_file.path
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 1)
        self.assertEqual(result[0].resolutions[0].uri, f"{reference}:First.test")


class Disable(SnippetTestCase):

    SNIPPET = """from avocado import Test

class PassTest(Test):
    '''
    Instrumented test, but disabled using an Avocado docstring tag
    :avocado: disable
    '''
    def test(self):
        pass
    """

    def test(self):
        """Checks that disabled tests are never resolved"""
        reference = self.input_test_file.path
        result = resolver.resolve([reference])
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(result[-1].result, resolver.ReferenceResolutionResult.NOTFOUND)


class Nested(SnippetTestCase):

    SNIPPET = """from avocado import Test
import avocado
import fmaslkfdsaf

class First(Test):
    '''
    :avocado: disable
    '''
    def test(self):
        class Third(Test):
            '''
            :avocado: enable
            '''
            def test_2(self):
                pass
        class Fourth(Second):
            '''
            :avocado: enable
            '''
            def test_3(self):
                pass
        pass
    """

    def test(self):
        """Checks that nested tests are never resolved"""
        reference = self.input_test_file.path
        result = resolver.resolve([reference])
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(result[-1].result, resolver.ReferenceResolutionResult.NOTFOUND)


class MultipleImports(SnippetTestCase):

    SNIPPET = """from avocado import Test
import avocado

class Second(avocado.Test):
    def test_1(self):
        pass
    """

    def test(self):
        """Checks multiple imports of base class don't break the resolver"""
        reference = self.input_test_file.path
        result = resolver.resolve([reference])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].reference, reference)
        self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(result[0].resolutions), 1)
        self.assertEqual(result[0].resolutions[0].uri, f"{reference}:Second.test_1")


class RaisingException(SnippetTestCase):

    SNIPPET = """from avocado import Test

class PassTest(Test):
    def test(self):
        pass
    """

    def test(self):
        with unittest.mock.patch(
            "avocado.core.safeloader.core.find_python_tests"
        ) as _mock:
            _mock.side_effect = Exception()
            reference = self.input_test_file.path
            result = resolver.resolve([reference])
            self.assertGreater(len(result), 0)
            self.assertEqual(result[0].reference, reference)
            self.assertEqual(result[0].result, resolver.ReferenceResolutionResult.ERROR)
            self.assertEqual(len(result[0].resolutions), 0)


class Resolver(unittest.TestCase):
    def _check(self, exps, runnables):
        len_msg = (
            f"Total count of tests not as expected ({len(exps)} != "
            "{len(runnables)}) \nexps: {exps}\nrunnables: {runnables}"
        )
        self.assertEqual(len(exps), len(runnables), len_msg)
        for exp, runnable in zip(exps, runnables):
            self.assertEqual(runnable.kind, "avocado-instrumented")
            self.assertEqual(runnable.uri, exp)

    def test_mod_import_and_classes(self):
        reference = os.path.join(
            "selftests", ".data", "safeloader", "data", "dont_crash.py"
        )
        result = resolver.resolve([reference])
        exps = [
            "selftests/.data/safeloader/data/dont_crash.py:DiscoverMe.test",
            "selftests/.data/safeloader/data/dont_crash.py:DiscoverMe2.test",
            "selftests/.data/safeloader/data/dont_crash.py:DiscoverMe3.test",
            "selftests/.data/safeloader/data/dont_crash.py:DiscoverMe4.test",
        ]
        self._check(exps, result[0].resolutions)

    def test_imports(self):
        reference = os.path.join(
            "selftests", ".data", "safeloader", "data", "imports.py"
        )
        result = resolver.resolve([reference])
        exps = [
            "selftests/.data/safeloader/data/imports.py:Test1.test",
            "selftests/.data/safeloader/data/imports.py:Test3.test",
            "selftests/.data/safeloader/data/imports.py:Test4.test",
            "selftests/.data/safeloader/data/imports.py:Test5.test",
            "selftests/.data/safeloader/data/imports.py:Test6.test",
            "selftests/.data/safeloader/data/imports.py:Test8.test",
            "selftests/.data/safeloader/data/imports.py:Test10.test",
        ]
        self._check(exps, result[0].resolutions)

    def test_infinite_recurse(self):
        """Checks we don't crash on infinite recursion"""
        reference = os.path.join(
            "selftests", ".data", "safeloader", "data", "infinite_recurse.py"
        )
        result = resolver.resolve([reference])
        self._check([], result[0].resolutions)
        self._check([], result[-1].resolutions)

    def test_double_import(self):
        reference = os.path.join(
            "selftests", ".data", "safeloader", "data", "double_import.py"
        )
        result = resolver.resolve([reference])
        exps = [
            "selftests/.data/safeloader/data/double_import.py:Test1.test1",
            "selftests/.data/safeloader/data/double_import.py:Test2.test2",
            "selftests/.data/safeloader/data/double_import.py:Test3.test3",
            "selftests/.data/safeloader/data/double_import.py:Test4.test4",
        ]
        self._check(exps, result[0].resolutions)
