from avocado import Test


class MultiplexTest(Test):

    """
    Execute a test that uses provided parameters (for multiplexing testing).

    :param *: All params are only logged, they have no special meaning
    """

    def setUp(self):
        self.compile_code()
        self.set_hugepages()
        self.set_numa_balance()
        self.assembly_vm()

        os_type = self.params.get('os_type', default='linux')
        if os_type == 'windows':
            self.log.info('Preparing VM with Windows (%s)',
                          self.params.get('win'))
        if os_type == 'linux':
            self.log.info('Preparing VM with Linux (%s)',
                          self.params.get('distro'))

    def compile_code(self):
        self.log.info('Compile code')
        self.log.info('gcc %s %s', self.params.get('gcc_flags', default='-O2'),
                      'code.c')

    def set_hugepages(self):
        if self.params.get('huge_pages', default='yes') == 'yes':
            self.log.info('Setting hugepages')

    def set_numa_balance(self):
        numa_balancing = self.params.get('numa_balancing', default='yes')
        numa_migrate = self.params.get('numa_balancing_migrate_deferred',
                                       default='no')
        if numa_balancing:
            self.log.info('Numa balancing: %s', numa_balancing)
        if numa_migrate:
            self.log.info('Numa balancing migrate deferred: %s', numa_migrate)

    def assembly_vm(self):
        self.log.info('Assembling VM')
        drive_format = self.params.get('drive_format', default='virtio_blk')
        nic_model = self.params.get('nic_model', default='virtio_net')
        enable_msx_vectors = self.params.get('enable_msx_vectors',
                                             default='yes')
        if drive_format:
            self.log.info('Drive format: %s', drive_format)
        if nic_model:
            self.log.info('NIC model: %s', nic_model)
        if enable_msx_vectors == 'yes':
            self.log.info('Enabling msx vectors')

    def test(self):
        self.log.info('Executing synctest...')
        self.log.info('synctest --timeout %s --tries %s',
                      self.params.get('sync_timeout', default=12),
                      self.params.get('sync_tries', default=3))

        self.log.info('Executing ping test...')
        cmdline = f"ping --timeout {self.params.get('ping_timeout', default=10)} --tries {self.params.get('ping_tries', default=5)}"

        ping_flags = self.params.get('ping_flags')
        if ping_flags:
            cmdline += f' {ping_flags}'

        self.log.info(cmdline)
