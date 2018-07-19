import infinite_recurse


# This should fail
class DependsOnSelf(infinite_recurse.DependsOnSelf):
    def test(self):
        pass
