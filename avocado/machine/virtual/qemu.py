"""
Contains the QEMU virtual machine class.

QEMU is a widely used open source machine emulator and virtualizer. The
QemuVirtualMachine class provides an abstraction model for interacting with
qemu processses as virtual machine objects, which you can control (start, stop,
migrate, so on and so forth). We also provide convenience methods to run your
own qemu commands made from scratch and then providing the same conveniences.
"""

from avocado.machine.virtual.base import VirtualMachine


class QemuVirtualMachine(VirtualMachine):

    migration_protos = ['rdma', 'x-rdma', 'tcp', 'unix', 'exec', 'fd']
    close_session_timeout = 30
    create_timeout = 20

    def __init__(self, name, params, state=None):
        if state:
            self.__dict__ = state
        else:
            self.process = None
            self.serial_ports = []
            self.serial_console = None
            self.redirs = {}
            self.spice_options = {}
            self.vnc_port = 5900
            self.monitors = []
            self.virtio_ports = []
            self.uuid = None
            self.vcpu_threads = []
            self.vhost_threads = []
            self.devices = None
            self.logs = {}
            self.remote_sessions = []
            self.logsessions = {}

        self.name = name
        self.params = params
        self.ip_version = self.params.get("ip_version", "ipv4")
        self.index_in_use = {}
        self.usb_dev_dict = {}
        self.driver_type = 'qemu'
        self.params['driver_type_' + self.name] = self.driver_type
        super(QemuVirtualMachine, self).__init__(name, params)
        if state:
            self.instance = state['instance']
        self.qemu_command = ''
        self.start_time = 0.0
        self.start_monotonic_time = 0.0
        self.last_boot_index = 0
        self.last_driver_index = 0

    def create(self, params=None):
        pass


def create_from_cmdline(cmdline):
    pass
