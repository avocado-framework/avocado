import time

from avocado import Test


class DisabledTest(Test):
    """
    :avocado: disable
    :avocado: tags=fast,net
    """

    def test_disabled(self):
        pass


class FastTest(Test):
    """
    :avocado: tags=fast
    """

    def test_fast(self):
        """
        :avocado: tags=net
        """

    def test_fast_other(self):
        """
        :avocado: tags=net
        """


class SlowTest(Test):
    """
    :avocado: tags=slow,disk
    """

    def test_slow(self):
        time.sleep(1)


class SlowUnsafeTest(Test):
    """
    :avocado: tags=slow,disk,unsafe
    """

    def test_slow_unsafe(self):
        time.sleep(1)


class SafeTest(Test):
    """
    :avocado: tags=safe
    """

    def test_safe(self):
        pass


class SafeX86Test(Test):
    """
    :avocado: tags=safe,arch:x86_64
    """

    def test_safe_x86(self):
        pass


class NoTagsTest(Test):
    def test_no_tags(self):
        pass


class SafeAarch64Test(Test):
    """
    :avocado: tags=safe,arch:aarch64
    """

    def test_safe_aarch64(self):
        pass
