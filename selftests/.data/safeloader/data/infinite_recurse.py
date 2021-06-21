import infinite_recurse  # pylint: disable=W0406


# This should fail
class DependsOnSelf(infinite_recurse.DependsOnSelf):
    def test(self):
        pass
