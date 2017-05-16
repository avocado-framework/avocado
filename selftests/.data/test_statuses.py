from avocado import Test


class StatusTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        if self.params.get('location') == 'setUp':
            exec(self.params.get('command'))
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        if self.params.get('location') == 'test':
            exec(self.params.get('command'))
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        if self.params.get('location') == 'tearDown':
            exec(self.params.get('command'))
        self.log.info('teardown post')
