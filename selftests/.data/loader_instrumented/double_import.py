import avocado as foo  # pylint: disable=W0404
import avocado as bar  # pylint: disable=W0404
from avocado import Test as Bar  # pylint: disable=W0404
from avocado import Test as Foo


class Test1(foo.Test):
    def test1(self):
        pass


class Test2(bar.Test):
    def test2(self):
        pass


class Test3(Foo):
    def test3(self):
        pass


class Test4(Bar):
    def test4(self):
        pass
