# Having 2 imports forces both paths
import avocado


# Should not be discovered as "Test" import did not happened yet
class DontCrash0(Test):
    def test(self):
        pass


from avocado import Test


# on "import avocado" this requires some skipping
class DontCrash1:
    pass


# This one should be discovered no matter how other
# classes break
class DiscoverMe(avocado.Test):
    def test(self):
        pass


# The same as "DontCrash1" only this one should be discovered
class DiscoverMe2(avocado.Test, main):  # pylint: disable=E0240,E0602
    def test(self):
        pass


# The same as "DontCrash1" only this one should be discovered
class DiscoverMe3(Test, main):  # pylint: disable=E0240,E0602
    def test(self):
        pass


class DontCrash2p:
    class Bar(avocado.Test):
        def test(self):
            pass


# Only top-level-namespace classes are allowed for
# in-module-class definitions
class DontCrash2(DontCrash2p.Bar):
    """:avocado: recursive"""


# Class DiscoverMe4p is defined after this one
class DiscoverMe4(DiscoverMe4p):    # pylint: disable=E0601
    """:avocado: recursive"""


class DiscoverMe4p:
    def test(self):
        pass


dont_crash3_on_broken_syntax    # pylint: disable=E0602,W0104
