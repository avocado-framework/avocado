from avocado.utils import network
from avocado.virt.qemu import path


class QemuDevices(object):

    def __init__(self, params=None):
        self.qemu_bin = path.get_qemu_binary(params)
        self.redir_port = None
        self._args = [self.qemu_bin]

    def add_args(self, *args):
        self._args.extend(args)

    def get_cmdline(self):
        return ' '.join(self._args)

    def add_fd(self, fd, fdset, opaque, opts=''):
        options = ['fd=%d' % fd,
                   'set=%d' % fdset,
                   'opaque=%s' % opaque]
        if opts:
            options.append(opts)

        self.add_args('-add-fd', ','.join(options))

    def add_qmp_monitor(self, monitor_socket):
        self.add_args('-chardev',
                      'socket,id=mon,path=%s' % monitor_socket,
                      '-mon', 'chardev=mon,mode=control')

    def add_display(self, value='none'):
        self.add_args('-display', value)

    def add_vga(self, value='none'):
        self.add_args('-vga', value)

    def add_drive(self, drive_file, device_type='virtio-blk-pci',
                  device_id='avocado_image', drive_id='device_avocado_image'):
        self.add_args('-drive',
                      'id=%s,if=none,file=%s' %
                      (drive_id, drive_file),
                      '-device %s,id=%s,drive=%s' %
                      (device_type, device_id, drive_id))

    def add_net(self, netdev_type='user', device_type='virtio-net-pci',
                device_id='avocado_nic', nic_id='device_avocado_nic'):
        self.redir_port = network.find_free_port(5000, 6000)
        self.add_args('-device %s,id=%s,netdev=%s' %
                      (device_type, device_id, nic_id),
                      '-netdev %s,id=%s,hostfwd=tcp::%s-:22' %
                      (netdev_type, nic_id, self.redir_port))

    def add_serial(self, serial_socket, device_id='avocado_serial'):
        self.add_args('-chardev socket,id=%s,path=%s,server,nowait' % (device_id, serial_socket))
        self.add_args('-device isa-serial,chardev=%s' % (device_id))
