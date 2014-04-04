.. _writing-tests:

Writing Avocado Tests
=====================

Avocado tests closely resemble autotest tests: All you need to do is to create a
test module, which is a python file with a class that inherits from `avocado.test.Test`.
This class only really needs to implement a method called `action`, which represents
the actual test payload. Let's re-create an old time functional test for autotest,
a simple `time.sleep([number-seconds])`:

::

    #!/usr/bin/python

    import time

    from avocado import job
    from avocado import test


    class sleeptest(test.Test):

        """
        Example test for avocado.
        """

        def action(self, length=1):
            """
            Sleep for length seconds.
            """
            self.log.debug("Sleeping for %d seconds", length)
            time.sleep(length)


    if __name__ == "__main__":
        job.main()


This is about the simplest test you can write for avocado (at least, one using
the avocado APIs). Note that the test object provides you with a number of
convenience attributes, such as `self.log`, that lets you log debug, info, error
and warning messages.
