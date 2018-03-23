import os
import sys

from avocado import Test, skip


class SkipSetup(Test):

    @skip("from setUp()")
    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class SkipTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    @skip("from test()")
    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class SkipTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    @skip("from tearDown()")
    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class CancelSetup(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.cancel()
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class CancelTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.cancel()
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class CancelTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.cancel()
        self.log.info('teardown post')


class FailSetup(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.fail()
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class FailTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.fail()
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class FailTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.fail()
        self.log.info('teardown post')


class WarnSetup(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.warn('')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class WarnTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.warn('')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class WarnTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.warn('')
        self.log.info('teardown post')


class ExitSetup(Test):

    def setUp(self):
        self.log.info('setup pre')
        sys.exit(-1)
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class ExitTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        sys.exit(-1)
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class ExitTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        sys.exit(-1)
        self.log.info('teardown post')


class ExceptionSetup(Test):

    def setUp(self):
        self.log.info('setup pre')
        raise ValueError
        # pylint: disable=W0101
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class ExceptionTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        raise ValueError
        # pylint: disable=W0101
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')


class ExceptionTeardown(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        raise ValueError
        # pylint: disable=W0101
        self.log.info('teardown post')


class KillTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        os.kill(os.getpid(), 9)
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        self.log.info('teardown post')
