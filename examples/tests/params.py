from avocado import Test


class Params(Test):

    def test(self):
        """Test that simply lists all parameters."""
        self.log.info("Test params:")
        for path, key, value in self.params.iteritems():
            self.log.info("%s:%s ==> %s", path, key, value)
