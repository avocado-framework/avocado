from avocado.core.test import Test  # pylint: disable=W0404


# On load this will be avocado.Test, but in static analysis it's
# avocado.core.test.Test and should not match.
class StaticallyNotAvocadoTest(Test):
    def test(self):
        pass


# This import should not make the previous import to be
# internally evaluated as "avocado.Test", because it happens
# after the previous class definition
from avocado import Test    # pylint: disable=W0404


# On recursive discovery this should be imported from
# avocado.core.test and not avocado.Test, therefor it should
# not be detected (ditto for the Python unittest discover behavior)
class NotTest(StaticallyNotAvocadoTest):
    def test2(self):
        pass
