from avocado import Test


class Property(Test):

    @property
    def testing_the_existence_of_properties(self):
        """
        This is a bad name for property when writing an Avocado test.

        Its name starts with "test", which would usually make it an
        Avocado test, but, because it's a property, it's not
        considered a valid test.
        """
        return True

    def test(self):
        self.log.info("Property exists: %s",
                      self.testing_the_existence_of_properties)
