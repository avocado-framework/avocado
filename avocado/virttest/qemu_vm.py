"""
Utility classes and functions to handle Virtual Machine creation using qemu.

:copyright: 2008-2009 Red Hat Inc.
"""

import time
import os
import logging
import fcntl
import re
import commands
from autotest.client.shared import error
from autotest.client import utils
from virttest.qemu_devices import qdevices, qcontainer
import utils_misc
import virt_vm
import test_setup
import storage
import qemu_monitor
import aexpect
import qemu_virtio_port
import remote
import data_dir
import utils_net


class QemuSegFaultError(virt_vm.VMError):

    def __init__(self, crash_message):
        virt_vm.VMError.__init__(self, crash_message)
        self.crash_message = crash_message

    def __str__(self):
        return ("Qemu crashed: %s" % self.crash_message)


class VMMigrateProtoUnsupportedError(virt_vm.VMMigrateProtoUnknownError):

    """
    When QEMU tells us it doesn't know about a given migration protocol.

    This usually happens when we're testing older QEMU. It makes sense to
    skip the test in this situation.
    """

    def __init__(self, protocol, output):
        self.protocol = protocol
        self.output = output

    def __str__(self):
        return ("QEMU reports it doesn't know migration protocol '%s'. "
                "QEMU output: %s" % (self.protocol, self.output))


class KVMInternalError(virt_vm.VMError):
    pass


class ImageUnbootableError(virt_vm.VMError):

    def __init__(self, name):
        virt_vm.VMError.__init__(self, name)
        self.name = name

    def __str__(self):
        return ("VM '%s' can't bootup from image,"
                " check your boot disk image file." % self.name)


def clean_tmp_files():
    if os.path.isfile(CREATE_LOCK_FILENAME):
        os.unlink(CREATE_LOCK_FILENAME)

CREATE_LOCK_FILENAME = os.path.join('/tmp', 'virt-test-vm-create.lock')


class VM(virt_vm.BaseVM):

    """
    This class handles all basic VM operations.
    """

    MIGRATION_PROTOS = ['rdma', 'x-rdma', 'tcp', 'unix', 'exec', 'fd']

    # By default we inherit all timeouts from the base VM class except...
    CLOSE_SESSION_TIMEOUT = 30

    # Because we've seen qemu taking longer than 5 seconds to initialize
    # itself completely, including creating the monitor sockets files
    # which are used on create(), this timeout is considerably larger
    # than the one on the base vm class
    CREATE_TIMEOUT = 20

    def __init__(self, name, params, root_dir, address_cache, state=None):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param params: A dict containing VM params
                (see method make_qemu_command for a full description)
        :param root_dir: Base directory for relative filenames
        :param address_cache: A dict that maps MAC addresses to IP addresses
        :param state: If provided, use this as self.__dict__
        """

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
            self.virtio_ports = []      # virtio_console / virtio_serialport
            self.pci_assignable = None
            self.uuid = None
            self.vcpu_threads = []
            self.vhost_threads = []
            self.devices = None
            self.logs = {}
            self.remote_sessions = []
            self.logsessions = {}

        self.name = name
        self.params = params
        self.root_dir = root_dir
        self.ip_version = self.params.get("ip_version", "ipv4")
        self.address_cache = address_cache
        self.index_in_use = {}
        # This usb_dev_dict member stores usb controller and device info,
        # It's dict, each key is an id of usb controller,
        # and key's value is a list, contains usb devices' ids which
        # attach to this controller.
        # A filled usb_dev_dict may look like:
        # { "usb1" : ["stg1", "stg2", "stg3", "stg4", "stg5", "stg6"],
        #   "usb2" : ["stg7", "stg8"],
        #   ...
        # }
        # This structure can used in usb hotplug/unplug test.
        self.usb_dev_dict = {}
        self.driver_type = 'qemu'
        self.params['driver_type_' + self.name] = self.driver_type
        # virtnet init depends on vm_type/driver_type being set w/in params
        super(VM, self).__init__(name, params)
        # un-overwrite instance attribute, virtnet db lookups depend on this
        if state:
            self.instance = state['instance']
        self.qemu_command = ''
        self.start_time = 0.0
        self.start_monotonic_time = 0.0
        self.last_boot_index = 0
        self.last_driver_index = 0

    def verify_alive(self):
        """
        Make sure the VM is alive and that the main monitor is responsive.

        :raise VMDeadError: If the VM is dead
        :raise: Various monitor exceptions if the monitor is unresponsive
        """
        self.verify_disk_image_bootable()
        self.verify_userspace_crash()
        self.verify_kernel_crash()
        self.verify_illegal_instruction()
        self.verify_kvm_internal_error()
        try:
            virt_vm.BaseVM.verify_alive(self)
            if self.monitor:
                self.monitor.verify_responsive()
        except virt_vm.VMDeadError:
            raise virt_vm.VMDeadError(self.process.get_status(),
                                      self.process.get_output())

    def is_alive(self):
        """
        Return True if the VM is alive and its monitor is responsive.
        """
        return not self.is_dead() and (not self.monitor or
                                       self.monitor.is_responsive())

    def is_dead(self):
        """
        Return True if the qemu process is dead.
        """
        return not self.process or not self.process.is_alive()

    def is_paused(self):
        """
        Return True if the qemu process is paused ('stop'ed)
        """
        if self.is_dead():
            return False
        try:
            self.verify_status("paused")
            return True
        except virt_vm.VMStatusError:
            return False

    def verify_status(self, status):
        """
        Check VM status

        :param status: Optional VM status, 'running' or 'paused'
        :raise VMStatusError: If the VM status is not same as parameter
        """
        if not self.monitor.verify_status(status):
            raise virt_vm.VMStatusError('Unexpected VM status: "%s"' %
                                        self.monitor.get_status())

    def verify_userspace_crash(self):
        """
        Verify if the userspace component (qemu) crashed.
        """
        if "(core dumped)" in self.process.get_output():
            for line in self.process.get_output().splitlines():
                if "(core dumped)" in line:
                    raise QemuSegFaultError(line)

    def verify_kvm_internal_error(self):
        """
        Verify KVM internal error.
        """
        if "KVM internal error." in self.process.get_output():
            out = self.process.get_output()
            out = out[out.find("KVM internal error."):]
            raise KVMInternalError(out)

    def verify_disk_image_bootable(self):
        if self.params.get("image_verify_bootable") == "yes":
            pattern = self.params.get("image_unbootable_pattern")
            if not pattern:
                raise virt_vm.VMConfigMissingError(self.name,
                                                   "image_unbootable_pattern")
            try:
                seabios_log = self.logsessions['seabios'].get_output()
                if re.search(pattern, seabios_log, re.S):
                    logging.error("Can't boot guest from image.")
                    # Set 'shutdown_command' to None to force autotest
                    # shuts down guest with monitor.
                    self.params["shutdown_command"] = None
                    raise ImageUnbootableError(self.name)
            except KeyError:
                pass

    def clone(self, name=None, params=None, root_dir=None, address_cache=None,
              copy_state=False):
        """
        Return a clone of the VM object with optionally modified parameters.
        The clone is initially not alive and needs to be started using create().
        Any parameters not passed to this function are copied from the source
        VM.

        :param name: Optional new VM name
        :param params: Optional new VM creation parameters
        :param root_dir: Optional new base directory for relative filenames
        :param address_cache: A dict that maps MAC addresses to IP addresses
        :param copy_state: If True, copy the original VM's state to the clone.
                Mainly useful for make_qemu_command().
        """
        if name is None:
            name = self.name
        if params is None:
            params = self.params.copy()
        if root_dir is None:
            root_dir = self.root_dir
        if address_cache is None:
            address_cache = self.address_cache
        if copy_state:
            state = self.__dict__.copy()
        else:
            state = None
        return VM(name, params, root_dir, address_cache, state)

    def get_serial_console_filename(self, name=None):
        """
        Return the serial console filename.

        :param name: The serial port name.
        """
        if name:
            return "/tmp/serial-%s-%s" % (name, self.instance)
        return "/tmp/serial-%s" % self.instance

    def get_serial_console_filenames(self):
        """
        Return a list of all serial console filenames
        (as specified in the VM's params).
        """
        return [self.get_serial_console_filename(_) for _ in
                self.params.objects("isa_serials")]

    def cleanup_serial_console(self):
        """
        Close serial console and associated log file
        """
        if self.serial_console is not None:
            self.serial_console.close()
            self.serial_console = None
        if hasattr(self, "migration_file"):
            try:
                os.unlink(self.migration_file)
            except OSError:
                pass

    def make_create_command(self, name=None, params=None, root_dir=None):
        """
        Generate a qemu command line. All parameters are optional. If a
        parameter is not supplied, the corresponding value stored in the
        class attributes is used.

        :param name: The name of the object
        :param params: A dict containing VM params
        :param root_dir: Base directory for relative filenames

        :note: The params dict should contain:
               mem -- memory size in MBs
               cdrom -- ISO filename to use with the qemu -cdrom parameter
               extra_params -- a string to append to the qemu command
               shell_port -- port of the remote shell daemon on the guest
               (SSH, Telnet or the home-made Remote Shell Server)
               shell_client -- client program to use for connecting to the
               remote shell daemon on the guest (ssh, telnet or nc)
               x11_display -- if specified, the DISPLAY environment variable
               will be be set to this value for the qemu process (useful for
               SDL rendering)
               images -- a list of image object names, separated by spaces
               nics -- a list of NIC object names, separated by spaces

               For each image in images:
               drive_format -- string to pass as 'if' parameter for this
               image (e.g. ide, scsi)
               image_snapshot -- if yes, pass 'snapshot=on' to qemu for
               this image
               image_boot -- if yes, pass 'boot=on' to qemu for this image
               In addition, all parameters required by get_image_filename.

               For each NIC in nics:
               nic_model -- string to pass as 'model' parameter for this
               NIC (e.g. e1000)
        """
        # Helper function for command line option wrappers
        def _add_option(option, value, option_type=None, first=False):
            """
            Add option to qemu parameters.
            """
            if first:
                fmt = " %s=%s"
            else:
                fmt = ",%s=%s"
            if option_type is bool:
                # Decode value for bool parameter (supports True, False, None)
                if value in ['yes', 'on', True]:
                    return fmt % (option, "on")
                elif value in ['no', 'off', False]:
                    return fmt % (option, "off")
            elif value and isinstance(value, bool):
                return fmt % (option, "on")
            elif value and isinstance(value, str):
                # "EMPTY_STRING" and "NULL_STRING" is used for testing illegal
                # foramt of option.
                # "EMPTY_STRING": set option as a empty string "".
                # "NO_EQUAL_STRING": set option as a option string only,
                #                    even without "=".
                #      (In most case, qemu-kvm should recognize it as "<null>")
                if value == "NO_EQUAL_STRING":
                    return ",%s" % option
                if value == "EMPTY_STRING":
                    value = '""'
                return fmt % (option, str(value))
            return ""

        # Wrappers for all supported qemu command line parameters.
        # This is meant to allow support for multiple qemu versions.
        # Each of these functions receives the output of 'qemu -help'
        # as a parameter, and should add the requested command line
        # option accordingly.
        def add_name(devices, name):
            return " -name '%s'" % name

        def process_sandbox(devices, action):
            if action == "add":
                if devices.has_option("sandbox"):
                    return " -sandbox on "
            elif action == "rem":
                if devices.has_option("sandbox"):
                    return " -sandbox off "

        def add_human_monitor(devices, monitor_name, filename):
            if not devices.has_option("chardev"):
                return " -monitor unix:'%s',server,nowait" % filename

            monitor_id = "hmp_id_%s" % monitor_name
            cmd = " -chardev socket"
            cmd += _add_option("id", monitor_id)
            cmd += _add_option("path", filename)
            cmd += _add_option("server", "NO_EQUAL_STRING")
            cmd += _add_option("nowait", "NO_EQUAL_STRING")
            cmd += " -mon chardev=%s" % monitor_id
            cmd += _add_option("mode", "readline")
            return cmd

        def add_qmp_monitor(devices, monitor_name, filename):
            if not devices.has_option("qmp"):
                logging.warn("Fallback to human monitor since qmp is"
                             " unsupported")
                return add_human_monitor(devices, monitor_name, filename)

            if not devices.has_option("chardev"):
                return " -qmp unix:'%s',server,nowait" % filename

            monitor_id = "qmp_id_%s" % monitor_name
            cmd = " -chardev socket"
            cmd += _add_option("id", monitor_id)
            cmd += _add_option("path", filename)
            cmd += _add_option("server", "NO_EQUAL_STRING")
            cmd += _add_option("nowait", "NO_EQUAL_STRING")
            cmd += " -mon chardev=%s" % monitor_id
            cmd += _add_option("mode", "control")
            return cmd

        def add_serial(devices, name, filename):
            if not devices.has_option("chardev"):
                return " -serial unix:'%s',server,nowait" % filename

            serial_id = "serial_id_%s" % name
            cmd = " -chardev socket"
            cmd += _add_option("id", serial_id)
            cmd += _add_option("path", filename)
            cmd += _add_option("server", "NO_EQUAL_STRING")
            cmd += _add_option("nowait", "NO_EQUAL_STRING")
            cmd += " -device isa-serial"
            cmd += _add_option("chardev", serial_id)
            return cmd

        def add_virtio_port(devices, name, bus, filename, porttype, chardev,
                            name_prefix=None, index=None, extra_params=""):
            """
            Appends virtio_serialport or virtio_console device to cmdline.
            :param help: qemu -h output
            :param name: Name of the port
            :param bus: Which virtio-serial-pci device use
            :param filename: Path to chardev filename
            :param porttype: Type of the port (*serialport, console)
            :param chardev: Which chardev to use (*socket, spicevmc)
            :param name_prefix: Custom name prefix (port index is appended)
            :param index: Index of the current virtio_port
            :param extra_params: Space sepparated chardev params
            """
            cmd = ''
            # host chardev
            if chardev == "spicevmc":   # SPICE
                cmd += " -chardev spicevmc,id=dev%s,name=%s" % (name, name)
            else:   # SOCKET
                cmd = (" -chardev socket,id=dev%s,path=%s,server,nowait"
                       % (name, filename))
            # virtport device
            if porttype in ("console", "virtio_console"):
                cmd += " -device virtconsole"
            else:
                cmd += " -device virtserialport"
            if name_prefix:     # used by spiceagent (com.redhat.spice.*)
                port_name = "%s%d" % (name_prefix, index)
            else:
                port_name = name
            cmd += ",chardev=dev%s,name=%s,id=%s" % (name, port_name, name)
            cmd += _add_option("bus", bus)
            # Space sepparated chardev params
            _params = ""
            for parm in extra_params.split():
                _params += ',' + parm
            cmd += _params
            return cmd

        def add_log_seabios(devices):
            if not devices.has_device("isa-debugcon"):
                return ""

            default_id = "seabioslog_id_%s" % self.instance
            filename = "/tmp/seabios-%s" % self.instance
            self.logs["seabios"] = filename
            cmd = " -chardev socket"
            cmd += _add_option("id", default_id)
            cmd += _add_option("path", filename)
            cmd += _add_option("server", "NO_EQUAL_STRING")
            cmd += _add_option("nowait", "NO_EQUAL_STRING")
            cmd += " -device isa-debugcon"
            cmd += _add_option("chardev", default_id)
            cmd += _add_option("iobase", "0x402")
            return cmd

        def add_log_anaconda(devices, pci_bus='pci.0'):
            chardev_id = "anacondalog_chardev_%s" % self.instance
            vioser_id = "anacondalog_vioser_%s" % self.instance
            filename = "/tmp/anaconda-%s" % self.instance
            self.logs["anaconda"] = filename
            dev = qdevices.QCustomDevice('chardev', backend='backend')
            dev.set_param('backend', 'socket')
            dev.set_param('id', chardev_id)
            dev.set_param("path", filename)
            dev.set_param("server", 'NO_EQUAL_STRING')
            dev.set_param("nowait", 'NO_EQUAL_STRING')
            devices.insert(dev)
            dev = QDevice('virtio-serial-pci', parent_bus=pci_bus)
            dev.set_param("id", vioser_id)
            devices.insert(dev)
            dev = QDevice('virtserialport')
            dev.set_param("bus", "%s.0" % vioser_id)
            dev.set_param("chardev", chardev_id)
            dev.set_param("name", "org.fedoraproject.anaconda.log.0")
            devices.insert(dev)

        def add_mem(devices, mem):
            return " -m %s" % mem

        def add_smp(devices):
            smp_str = " -smp %d" % self.cpuinfo.smp
            smp_pattern = "smp .*n\[,maxcpus=cpus\].*"
            if devices.has_option(smp_pattern):
                smp_str += ",maxcpus=%d" % self.cpuinfo.maxcpus
            smp_str += ",cores=%d" % self.cpuinfo.cores
            smp_str += ",threads=%d" % self.cpuinfo.threads
            smp_str += ",sockets=%d" % self.cpuinfo.sockets
            return smp_str

        def add_nic(devices, vlan, model=None, mac=None, device_id=None,
                    netdev_id=None, nic_extra_params=None, pci_addr=None,
                    bootindex=None, queues=1, vectors=None, pci_bus='pci.0'):
            if model == 'none':
                return
            if devices.has_option("device"):
                if not model:
                    model = "rtl8139"
                elif model == "virtio":
                    model = "virtio-net-pci"
                dev = QDevice(model)
                dev.set_param('mac', mac, dynamic=True)
                # only pci domain=0,bus=0,function=0 is supported for now.
                #
                # libvirt gains the pci_slot, free_pci_addr here,
                # value by parsing the xml file, i.e. counting all the
                # pci devices and store the number.
                if model != 'spapr-vlan':
                    dev.parent_bus = pci_bus
                    dev.set_param('addr', pci_addr)
                if nic_extra_params:
                    nic_extra_params = (_.split('=', 1) for _ in
                                        nic_extra_params.split(',') if _)
                    for key, val in nic_extra_params:
                        dev.set_param(key, val)
                dev.set_param("bootindex", bootindex)
            else:
                dev = qdevices.QCustomDevice('net', backend='type')
                dev.set_param('type', 'nic')
                dev.set_param('model', model)
                dev.set_param('macaddr', mac, 'NEED_QUOTE', True)
            dev.set_param('id', device_id, 'NEED_QUOTE')
            if "virtio" in model:
                if int(queues) > 1:
                    dev.set_param('mq', 'on')
                if vectors:
                    dev.set_param('vectors', vectors)
            if devices.has_option("netdev"):
                dev.set_param('netdev', netdev_id)
            else:
                dev.set_param('vlan', vlan)
            devices.insert(dev)

        def add_net(devices, vlan, nettype, ifname=None, tftp=None,
                    bootfile=None, hostfwd=[], netdev_id=None,
                    netdev_extra_params=None, tapfds=None, script=None,
                    downscript=None, vhost=None, queues=None, vhostfds=None,
                    add_queues=None, helper=None, add_tapfd=None,
                    add_vhostfd=None):
            mode = None
            if nettype in ['bridge', 'network', 'macvtap']:
                mode = 'tap'
            elif nettype == 'user':
                mode = 'user'
            else:
                logging.warning("Unknown/unsupported nettype %s" % nettype)
                return ''

            if devices.has_option("netdev"):
                cmd = " -netdev %s,id=%s" % (mode, netdev_id)
                cmd_nd = cmd
                if vhost:
                    if vhost in ["on", "off"]:
                        cmd += ",vhost=%s" % vhost
                    elif vhost == "vhost=on":  # Keeps compatibility with old.
                        cmd += ",%s" % vhost
                    cmd_nd = cmd
                    if vhostfds:
                        if (int(queues) > 1 and
                                'vhostfds=' in devices.get_help_text()):
                            cmd += ",vhostfds=%(vhostfds)s"
                            cmd_nd += ",vhostfds=DYN"
                        else:
                            txt = ""
                            if int(queues) > 1:
                                txt = "qemu do not support vhost multiqueue,"
                                txt += " Fall back to single queue."
                            if 'vhostfd=' in devices.get_help_text():
                                cmd += ",vhostfd=%(vhostfd)s"
                                cmd_nd += ",vhostfd=DYN"
                            else:
                                txt += " qemu do not support vhostfd."
                            if txt:
                                logging.warn(txt)
                        # For negative test
                        if add_vhostfd:
                            cmd += ",vhostfd=%(vhostfd)s"
                            cmd_nd += ",vhostfd=%(vhostfd)s"
                if netdev_extra_params:
                    cmd += "%s" % netdev_extra_params
                    cmd_nd += "%s" % netdev_extra_params
            else:
                cmd = " -net %s,vlan=%d" % (mode, vlan)
                cmd_nd = cmd
            if mode == "tap":
                if script:
                    cmd += ",script='%s'" % script
                    cmd += ",downscript='%s'" % (downscript or "no")
                    cmd_nd = cmd
                    if ifname:
                        cmd += ",ifname='%s'" % ifname
                        cmd_nd = cmd
                elif tapfds:
                    if (int(queues) > 1 and
                            ',fds=' in devices.get_help_text()):
                        cmd += ",fds=%(tapfds)s"
                        cmd_nd += ",fds=DYN"
                    else:
                        cmd += ",fd=%(tapfd)s"
                        cmd_nd += ",fd=DYN"
                    # For negative test
                    if add_tapfd:
                        cmd += ",fd=%(tapfd)s"
                        cmd_nd += ",fd=%(tapfd)s"
            elif mode == "user":
                if tftp and "[,tftp=" in devices.get_help_text():
                    cmd += ",tftp='%s'" % tftp
                    cmd_nd = cmd
                if bootfile and "[,bootfile=" in devices.get_help_text():
                    cmd += ",bootfile='%s'" % bootfile
                    cmd_nd = cmd
                if "[,hostfwd=" in devices.get_help_text():
                    for i in xrange(len(hostfwd)):
                        cmd += (",hostfwd=tcp::%%(host_port%d)s"
                                "-:%%(guest_port%d)s" % (i, i))
                        cmd_nd += ",hostfwd=tcp::DYN-:%%(guest_port)ds"

            if add_queues and queues:
                cmd += ",queues=%s" % queues
                cmd_nd += ",queues=%s" % queues

            if helper:
                cmd += ",helper=%s" % helper
                cmd_nd += ",helper=%s" % helper

            return cmd, cmd_nd

        def add_floppy(devices, filename, index):
            cmd_list = [" -fda '%s'", " -fdb '%s'"]
            return cmd_list[index] % filename

        def add_tftp(devices, filename):
            # If the new syntax is supported, don't add -tftp
            if "[,tftp=" in devices.get_help_text():
                return ""
            else:
                return " -tftp '%s'" % filename

        def add_bootp(devices, filename):
            # If the new syntax is supported, don't add -bootp
            if "[,bootfile=" in devices.get_help_text():
                return ""
            else:
                return " -bootp '%s'" % filename

        def add_tcp_redir(devices, host_port, guest_port):
            # If the new syntax is supported, don't add -redir
            if "[,hostfwd=" in devices.get_help_text():
                return ""
            else:
                return " -redir tcp:%s::%s" % (host_port, guest_port)

        def add_vnc(devices, vnc_port, vnc_password='no', extra_params=None):
            vnc_cmd = " -vnc :%d" % (vnc_port - 5900)
            if vnc_password == "yes":
                vnc_cmd += ",password"
            if extra_params:
                vnc_cmd += ",%s" % extra_params
            return vnc_cmd

        def add_sdl(devices):
            if devices.has_option("sdl"):
                return " -sdl"
            else:
                return ""

        def add_nographic(devices):
            return " -nographic"

        def add_uuid(devices, uuid):
            return " -uuid '%s'" % uuid

        def add_pcidevice(devices, host, params, device_driver="pci-assign",
                          pci_bus='pci.0'):
            if devices.has_device(device_driver):
                dev = QDevice(device_driver, parent_bus=pci_bus)
            else:
                dev = qdevices.QCustomDevice('pcidevice', parent_bus=pci_bus)
            help_cmd = "%s -device %s,\\? 2>&1" % (qemu_binary, device_driver)
            pcidevice_help = utils.system_output(help_cmd)
            dev.set_param('host', host)
            dev.set_param('id', 'id_%s' % host.replace(":", "."))
            fail_param = []
            for param in params.get("pci-assign_params", "").split():
                value = params.get(param)
                if value:
                    if param in pcidevice_help:
                        dev.set_param(param, value)
                    else:
                        fail_param.append(param)
            if fail_param:
                msg = ("parameter %s is not support in device pci-assign."
                       " It only support following parameter:\n %s" %
                       (", ".join(fail_param), pcidevice_help))
                logging.warn(msg)
            devices.insert(dev)

        def add_spice_rhel5(devices, spice_params, port_range=(3100, 3199)):
            """
            processes spice parameters on rhel5 host.

            :param spice_options - dict with spice keys/values
            :param port_range - tuple with port range, default: (3000, 3199)
            """

            if devices.has_option("spice"):
                cmd = " -spice"
            else:
                return ""
            spice_help = ""
            if devices.has_option("spice-help"):
                spice_help = commands.getoutput("%s -device \\?" % qemu_binary)
            s_port = str(utils_misc.find_free_port(*port_range))
            self.spice_options['spice_port'] = s_port
            cmd += " port=%s" % s_port
            for param in spice_params.split():
                value = params.get(param)
                if value:
                    if bool(re.search(param, spice_help, re.M)):
                        cmd += ",%s=%s" % (param, value)
                    else:
                        msg = ("parameter %s is not supported in spice. It "
                               "only supports the following parameters:\n %s"
                               % (param, spice_help))
                        logging.warn(msg)
                else:
                    cmd += ",%s" % param
            if devices.has_option("qxl"):
                qxl_dev_nr = params.get("qxl_dev_nr", 1)
                cmd += " -qxl %s" % qxl_dev_nr
            return cmd

        def add_spice(port_range=(3000, 3199),
                      tls_port_range=(3200, 3399)):
            """
            processes spice parameters
            :param port_range - tuple with port range, default: (3000, 3199)
            :param tls_port_range - tuple with tls port range,
                                    default: (3200, 3399)
            """
            spice_opts = []  # will be used for ",".join()
            tmp = None

            def optget(opt):
                """a helper function"""
                return self.spice_options.get(opt)

            def set_yes_no_value(key, yes_value=None, no_value=None):
                """just a helper function"""
                tmp = optget(key)
                if tmp == "no" and no_value:
                    spice_opts.append(no_value)

                elif tmp == "yes" and yes_value:
                    spice_opts.append(yes_value)

            def set_value(opt_string, key, fallback=None):
                """just a helper function"""
                tmp = optget(key)
                if tmp:
                    spice_opts.append(opt_string % tmp)
                elif fallback:
                    spice_opts.append(fallback)
            s_port = str(utils_misc.find_free_port(*port_range))
            if optget("spice_port") == "generate":
                if not self.is_alive():
                    self.spice_options['spice_port'] = s_port
                    spice_opts.append("port=%s" % s_port)
                    self.spice_port = s_port
                else:
                    self.spice_options['spice_port'] = self.spice_port
                    spice_opts.append("port=%s" % self.spice_port)
            else:
                set_value("port=%s", "spice_port")

            set_value("password=%s", "spice_password", "disable-ticketing")
            if optget("listening_addr") == "ipv4":
                host_ip = utils_net.get_host_ip_address(self.params)
                self.spice_options['listening_addr'] = "ipv4"
                spice_opts.append("addr=%s" % host_ip)
                # set_value("addr=%s", "listening_addr", )
            elif optget("listening_addr") == "ipv6":
                host_ip = utils_net.get_host_ip_address(self.params)
                host_ip_ipv6 = utils_misc.convert_ipv4_to_ipv6(host_ip)
                self.spice_options['listening_addr'] = "ipv6"
                spice_opts.append("addr=%s" % host_ip_ipv6)

            set_yes_no_value(
                "disable_copy_paste", yes_value="disable-copy-paste")
            set_value("addr=%s", "spice_addr")

            if optget("spice_ssl") == "yes":
                # SSL only part
                t_port = str(utils_misc.find_free_port(*tls_port_range))
                if optget("spice_tls_port") == "generate":
                    if not self.is_alive():
                        self.spice_options['spice_tls_port'] = t_port
                        spice_opts.append("tls-port=%s" % t_port)
                        self.spice_tls_port = t_port
                    else:
                        self.spice_options[
                            'spice_tls_port'] = self.spice_tls_port
                        spice_opts.append("tls-port=%s" % self.spice_tls_port)
                else:
                    set_value("tls-port=%s", "spice_tls_port")

                prefix = optget("spice_x509_prefix")
                if ((prefix is None or not os.path.exists(prefix)) and
                        (optget("spice_gen_x509") == "yes")):
                    # Generate spice_x509_* is not always necessary,
                    # Regenerate them will make your existing VM
                    # not longer accessiable via encrypted spice.
                    c_subj = optget("spice_x509_cacert_subj")
                    s_subj = optget("spice_x509_server_subj")
                    # If CN is not specified, add IP of host
                    if s_subj[-3:] == "CN=":
                        s_subj += utils_net.get_host_ip_address(self.params)
                    passwd = optget("spice_x509_key_password")
                    secure = optget("spice_x509_secure")

                    utils_misc.create_x509_dir(prefix, c_subj, s_subj, passwd,
                                               secure)

                tmp = optget("spice_x509_dir")
                if tmp == "yes":
                    spice_opts.append("x509-dir=%s" % (prefix))

                elif tmp == "no":
                    cacert = optget("spice_x509_cacert_file")
                    server_key = optget("spice_x509_key_file")
                    server_cert = optget("spice_x509_cert_file")
                    keyfile_str = ("x509-key-file=%s,x509-cacert-file=%s,"
                                   "x509-cert-file=%s" %
                                   (os.path.join(prefix, server_key),
                                    os.path.join(prefix, cacert),
                                    os.path.join(prefix, server_cert)))
                    spice_opts.append(keyfile_str)

                set_yes_no_value("spice_x509_secure",
                                 yes_value="x509-key-password=%s" %
                                 (optget("spice_x509_key_password")))

                tmp = optget("spice_secure_channels")
                if tmp:
                    for item in tmp.split(","):
                        spice_opts.append("tls-channel=%s" % (item.strip()))

            # Less common options
            set_value("seamless-migration=%s", "spice_seamless_migration")
            set_value("image-compression=%s", "spice_image_compression")
            set_value("jpeg-wan-compression=%s", "spice_jpeg_wan_compression")
            set_value("zlib-glz-wan-compression=%s",
                      "spice_zlib_glz_wan_compression")
            set_value("streaming-video=%s", "spice_streaming_video")
            set_value("agent-mouse=%s", "spice_agent_mouse")
            set_value("playback-compression=%s", "spice_playback_compression")

            set_yes_no_value("spice_ipv4", yes_value="ipv4")
            set_yes_no_value("spice_ipv6", yes_value="ipv6")

            return " -spice %s" % (",".join(spice_opts))

        def add_qxl(qxl_nr, qxl_memory=None):
            """
            adds extra qxl devices + sets memory to -vga qxl and extra qxls
            :param qxl_nr total number of qxl devices
            :param qxl_memory sets memory to individual devices
            """
            qxl_str = ""
            vram_help = ""

            if qxl_memory:
                vram_help = "vram_size=%d" % qxl_memory
                qxl_str += " -global qxl-vga.%s" % (vram_help)

            for index in range(1, qxl_nr):
                qxl_str += " -device qxl,id=video%d,%s"\
                    % (index, vram_help)
            return qxl_str

        def add_vga(vga):
            return " -vga %s" % vga

        def add_kernel(devices, filename):
            return " -kernel '%s'" % filename

        def add_initrd(devices, filename):
            return " -initrd '%s'" % filename

        def add_rtc(devices):
            # Pay attention that rtc-td-hack is for early version
            # if "rtc " in help:
            if devices.has_option("rtc"):
                cmd = " -rtc base=%s" % params.get("rtc_base", "utc")
                cmd += _add_option("clock", params.get("rtc_clock", "host"))
                cmd += _add_option("driftfix", params.get("rtc_drift", "none"))
                return cmd
            elif devices.has_option("rtc-td-hack"):
                return " -rtc-td-hack"
            else:
                return ""

        def add_kernel_cmdline(devices, cmdline):
            return " -append '%s'" % cmdline

        def add_testdev(devices, filename=None):
            if devices.has_device("testdev"):
                return (" -chardev file,id=testlog,path=%s"
                        " -device testdev,chardev=testlog" % filename)
            elif devices.has_device("pc-testdev"):
                return " -device pc-testdev"
            else:
                return ""

        def add_isa_debug_exit(devices, iobase=0xf4, iosize=0x04):
            if devices.has_device("isa-debug-exit"):
                return (" -device isa-debug-exit,iobase=%s,iosize=%s" %
                        (iobase, iosize))
            else:
                return ""

        def add_no_hpet(devices):
            if devices.has_option("no-hpet"):
                return " -no-hpet"
            else:
                return ""

        def add_cpu_flags(devices, cpu_model, flags=None, vendor_id=None,
                          family=None):
            if devices.has_option('cpu'):
                cmd = " -cpu '%s'" % cpu_model

                if vendor_id:
                    cmd += ",vendor=\"%s\"" % vendor_id
                if flags:
                    if not flags.startswith(","):
                        cmd += ","
                    cmd += "%s" % flags
                if family is not None:
                    cmd += ",family=%s" % family
                return cmd
            else:
                return ""

        def add_boot(devices, boot_order, boot_once, boot_menu):
            cmd = " -boot"
            pattern = "boot \[order=drives\]\[,once=drives\]\[,menu=on\|off\]"
            if devices.has_option("boot \[a\|c\|d\|n\]"):
                cmd += " %s" % boot_once
            elif devices.has_option(pattern):
                cmd += (" order=%s,once=%s,menu=%s" %
                        (boot_order, boot_once, boot_menu))
            else:
                cmd = ""
            return cmd

        def get_index(index):
            while self.index_in_use.get(str(index)):
                index += 1
            return index

        def add_sga(devices):
            if not devices.has_option("device"):
                return ""

            return " -device sga"

        def add_watchdog(devices, device_type=None, action="reset"):
            watchdog_cmd = ""
            if devices.has_option("watchdog"):
                if device_type:
                    watchdog_cmd += " -watchdog %s" % device_type
                watchdog_cmd += " -watchdog-action %s" % action

            return watchdog_cmd

        def add_option_rom(devices, opt_rom):
            if not devices.has_option("option-rom"):
                return ""

            return " -option-rom %s" % opt_rom

        def add_smartcard(devices, sc_chardev, sc_id):
            sc_cmd = " -device usb-ccid,id=ccid0"
            sc_cmd += " -chardev " + sc_chardev
            sc_cmd += ",id=" + sc_id + ",name=smartcard"
            sc_cmd += " -device ccid-card-passthru,chardev=" + sc_id

            return sc_cmd

        def add_numa_node(devices, mem=None, cpus=None, nodeid=None):
            """
            This function used to add numa node to guest command line
            """
            if not devices.has_option("numa"):
                return ""
            numa_cmd = " -numa node"
            if mem is not None:
                numa_cmd += ",mem=%s" % mem
            if cpus is not None:
                numa_cmd += ",cpus=%s" % cpus
            if nodeid is not None:
                numa_cmd += ",nodeid=%s" % nodeid
            return numa_cmd

        # End of command line option wrappers

        # If nothing changed and devices exists, return imediatelly
        if (name is None and params is None and root_dir is None
                and self.devices is not None):
            return self.devices

        if name is None:
            name = self.name
        if params is None:
            params = self.params
        if root_dir is None:
            root_dir = self.root_dir

        have_ahci = False
        have_virtio_scsi = False
        virtio_scsi_pcis = []
        pci_bus = {'aobject': params.get('pci_bus', 'pci.0')}

        # init value by default.
        # PCI addr 0,1,2 are taken by PCI/ISA/IDE bridge and the GPU.
        self.pci_addr_list = [0, 1, 2]

        # Clone this VM using the new params
        vm = self.clone(name, params, root_dir, copy_state=True)

        # global counters
        ide_bus = 0
        ide_unit = 0
        vdisk = 0
        scsi_disk = 0
        self.last_boot_index = 0
        if params.get("kernel"):
            self.last_boot_index = 1

        qemu_binary = utils_misc.get_qemu_binary(params)

        self.qemu_binary = qemu_binary
        support_cpu_model = commands.getoutput("%s -cpu \\?" % qemu_binary)

        self.last_driver_index = 0
        # init the dict index_in_use
        for key in params.keys():
            if 'drive_index' in key:
                self.index_in_use[params.get(key)] = True

        cmd = ""
        # Enable the use of glibc's malloc_perturb feature
        if params.get("malloc_perturb", "no") == "yes":
            cmd += "MALLOC_PERTURB_=1 "
        # Set the X11 display parameter if requested
        if params.get("x11_display"):
            cmd += "DISPLAY=%s " % params.get("x11_display")
        if params.get("qemu_audio_drv"):
            cmd += "QEMU_AUDIO_DRV=%s " % params.get("qemu_audio_drv")
        # Add command prefix for qemu-kvm. like taskset, valgrind and so on
        if params.get("qemu_command_prefix"):
            qemu_command_prefix = params.get("qemu_command_prefix")
            cmd += "%s " % qemu_command_prefix
        # Add numa memory cmd to pin guest memory to numa node
        if params.get("numa_node"):
            numa_node = int(params.get("numa_node"))
            if len(utils_misc.get_node_cpus()) < int(params.get("smp", 1)):
                logging.info("Skip pinning, no enough nodes")
            elif numa_node < 0:
                n = utils_misc.NumaNode(numa_node)
                cmd += "numactl -m %s " % n.node_id
            else:
                n = numa_node - 1
                cmd += "numactl -m %s " % n

        # Start constructing devices representation
        devices = qcontainer.DevContainer(qemu_binary, self.name,
                                          params.get('strict_mode'),
                                          params.get('workaround_qemu_qmp_crash'),
                                          params.get('allow_hotplugged_vm'))
        StrDev = qdevices.QStringDevice
        QDevice = qdevices.QDevice

        devices.insert(StrDev('PREFIX', cmdline=cmd))
        # Add the qemu binary
        devices.insert(StrDev('qemu', cmdline=qemu_binary))
        devices.insert(StrDev('-S', cmdline="-S"))
        # Add the VM's name
        devices.insert(StrDev('vmname', cmdline=add_name(devices, name)))

        if params.get("qemu_sandbox", "on") == "on":
            devices.insert(StrDev('sandbox', cmdline=process_sandbox(devices, "add")))
        elif params.get("sandbox", "off") == "off":
            devices.insert(StrDev('qemu_sandbox', cmdline=process_sandbox(devices, "rem")))

        devs = devices.machine_by_params(params)
        for dev in devs:
            devices.insert(dev)

        # no automagic devices please
        defaults = params.get("defaults", "no")
        if devices.has_option("nodefaults") and defaults != "yes":
            devices.insert(StrDev('nodefaults', cmdline=" -nodefaults"))

        vga = params.get("vga")
        if vga:
            if vga != 'none':
                devices.insert(StrDev('VGA-%s' % vga,
                                      cmdline=add_vga(vga),
                                      parent_bus={'aobject': 'pci.0'}))
            else:
                devices.insert(StrDev('VGA-none', cmdline=add_vga(vga)))

            if vga == "qxl":
                qxl_dev_memory = int(params.get("qxl_dev_memory", 0))
                qxl_dev_nr = int(params.get("qxl_dev_nr", 1))
                devices.insert(StrDev('qxl',
                                      cmdline=add_qxl(qxl_dev_nr, qxl_dev_memory)))
        elif params.get('defaults', 'no') != 'no':  # by default add cirrus
            devices.insert(StrDev('VGA-cirrus',
                                  cmdline=add_vga(vga),
                                  parent_bus={'aobject': 'pci.0'}))

        # When old scsi fmt is used, new device with lowest pci_addr is created
        devices.hook_fill_scsi_hbas(params)

        # Additional PCI RC/switch/bridges
        for pcic in params.objects("pci_controllers"):
            devs = devices.pcic_by_params(pcic, params.object_params(pcic))
            devices.insert(devs)

        # -soundhw addresses are always the lowest after scsi
        soundhw = params.get("soundcards")
        if soundhw:
            if not devices.has_option('device') or soundhw == "all":
                for sndcard in ('AC97', 'ES1370', 'intel-hda'):
                    # Add all dummy PCI devices and the actuall command below
                    devices.insert(StrDev("SND-%s" % sndcard,
                                          parent_bus=pci_bus))
                devices.insert(StrDev('SoundHW',
                                      cmdline="-soundhw %s" % soundhw))
            else:
                # TODO: Use QDevices for this and set the addresses properly
                for sound_device in soundhw.split(","):
                    if "hda" in sound_device:
                        devices.insert(QDevice('intel-hda',
                                               parent_bus=pci_bus))
                        devices.insert(QDevice('hda-duplex'))
                    elif sound_device in ["es1370", "ac97"]:
                        devices.insert(QDevice(sound_device.upper(),
                                               parent_bus=pci_bus))
                    else:
                        devices.insert(QDevice(sound_device,
                                               parent_bus=pci_bus))

        # Add monitors
        for monitor_name in params.objects("monitors"):
            monitor_params = params.object_params(monitor_name)
            monitor_filename = qemu_monitor.get_monitor_filename(vm,
                                                                 monitor_name)
            if monitor_params.get("monitor_type") == "qmp":
                cmd = add_qmp_monitor(devices, monitor_name,
                                      monitor_filename)
                devices.insert(StrDev('QMP-%s' % monitor_name, cmdline=cmd))
            else:
                cmd = add_human_monitor(devices, monitor_name,
                                        monitor_filename)
                devices.insert(StrDev('HMP-%s' % monitor_name, cmdline=cmd))

        # Add serial console redirection
        for serial in params.objects("isa_serials"):
            serial_filename = vm.get_serial_console_filename(serial)
            cmd = add_serial(devices, serial, serial_filename)
            devices.insert(StrDev('SER-%s' % serial, cmdline=cmd))

        # Add virtio_serial ports
        no_virtio_serial_pcis = 0
        no_virtio_ports = 0
        virtio_port_spread = int(params.get('virtio_port_spread', 2))
        for port_name in params.objects("virtio_ports"):
            port_params = params.object_params(port_name)
            bus = params.get('virtio_port_bus', False)
            if bus is not False:     # Manually set bus
                bus = int(bus)
            elif not virtio_port_spread:
                # bus not specified, let qemu decide
                pass
            elif not no_virtio_ports % virtio_port_spread:
                # Add new vio-pci every n-th port. (Spread ports)
                bus = no_virtio_serial_pcis
            else:  # Port not overriden, use last vio-pci
                bus = no_virtio_serial_pcis - 1
                if bus < 0:     # First bus
                    bus = 0
            # Add virtio_serial_pcis
            # Multiple virtio console devices can't share a
            # single virtio-serial-pci bus. So add a virtio-serial-pci bus
            # when the port is a virtio console.
            if (port_params.get('virtio_port_type') == 'console'
                    and params.get('virtio_port_bus') is None):
                dev = QDevice('virtio-serial-pci', parent_bus=pci_bus)
                dev.set_param('id',
                              'virtio_serial_pci%d' % no_virtio_serial_pcis)
                devices.insert(dev)
                no_virtio_serial_pcis += 1
            for i in range(no_virtio_serial_pcis, bus + 1):
                dev = QDevice('virtio-serial-pci', parent_bus=pci_bus)
                dev.set_param('id', 'virtio_serial_pci%d' % i)
                devices.insert(dev)
                no_virtio_serial_pcis += 1
            if bus is not False:
                bus = "virtio_serial_pci%d.0" % bus
            # Add actual ports
            cmd = add_virtio_port(devices, port_name, bus,
                                  self.get_virtio_port_filename(port_name),
                                  port_params.get('virtio_port_type'),
                                  port_params.get('virtio_port_chardev'),
                                  port_params.get('virtio_port_name_prefix'),
                                  no_virtio_ports,
                                  port_params.get('virtio_port_params', ''))
            devices.insert(StrDev('VIO-%s' % port_name, cmdline=cmd))
            no_virtio_ports += 1

        # Add logging
        devices.insert(StrDev('isa-log', cmdline=add_log_seabios(devices)))
        if params.get("anaconda_log", "no") == "yes":
            add_log_anaconda(devices, pci_bus)

        # Add USB controllers
        usbs = params.objects("usbs")
        if not devices.has_option("device"):
            usbs = ("oldusb",)  # Old qemu, add only one controller '-usb'
        for usb_name in usbs:
            usb_params = params.object_params(usb_name)
            for dev in devices.usbc_by_params(usb_name, usb_params):
                devices.insert(dev)

        # Add images (harddrives)
        for image_name in params.objects("images"):
            # FIXME: Use qemu_devices for handling indexes
            image_params = params.object_params(image_name)
            if image_params.get("boot_drive") == "no":
                continue
            if params.get("index_enable") == "yes":
                drive_index = image_params.get("drive_index")
                if drive_index:
                    index = drive_index
                else:
                    self.last_driver_index = get_index(self.last_driver_index)
                    index = str(self.last_driver_index)
                    self.last_driver_index += 1
            else:
                index = None
            image_bootindex = None
            image_boot = image_params.get("image_boot")
            if not re.search("boot=on\|off", devices.get_help_text(),
                             re.MULTILINE):
                if image_boot in ['yes', 'on', True]:
                    image_bootindex = str(self.last_boot_index)
                    self.last_boot_index += 1
                image_boot = "unused"
                image_bootindex = image_params.get('bootindex',
                                                   image_bootindex)
            else:
                if image_boot in ['yes', 'on', True]:
                    if self.last_boot_index > 0:
                        image_boot = False
                    self.last_boot_index += 1
            image_params = params.object_params(image_name)
            if image_params.get("boot_drive") == "no":
                continue
            devs = devices.images_define_by_params(image_name, image_params,
                                                   'disk', index, image_boot,
                                                   image_bootindex)
            for _ in devs:
                devices.insert(_)

        # Networking
        redirs = []
        for redir_name in params.objects("redirs"):
            redir_params = params.object_params(redir_name)
            guest_port = int(redir_params.get("guest_port"))
            host_port = vm.redirs.get(guest_port)
            redirs += [(host_port, guest_port)]

        iov = 0
        for nic in vm.virtnet:
            nic_params = params.object_params(nic.nic_name)
            if nic_params.get('pci_assignable') == "no":
                script = nic_params.get("nic_script")
                downscript = nic_params.get("nic_downscript")
                vhost = nic_params.get("vhost")
                script_dir = data_dir.get_data_dir()
                if script:
                    script = utils_misc.get_path(script_dir, script)
                if downscript:
                    downscript = utils_misc.get_path(script_dir, downscript)
                # setup nic parameters as needed
                # add_netdev if netdev_id not set
                nic = vm.add_nic(**dict(nic))
                # gather set values or None if unset
                vlan = int(nic.get('vlan'))
                netdev_id = nic.get('netdev_id')
                device_id = nic.get('device_id')
                mac = nic.get('mac')
                nic_model = nic.get("nic_model")
                nic_extra = nic.get("nic_extra_params")
                bootindex = nic_params.get("bootindex")
                netdev_extra = nic.get("netdev_extra_params")
                bootp = nic.get("bootp")
                add_queues = nic_params.get("add_queues", "no") == "yes"
                add_tapfd = nic_params.get("add_tapfd", "no") == "yes"
                add_vhostfd = nic_params.get("add_vhostfd", "no") == "yes"
                helper = nic_params.get("helper")
                tapfds_len = int(nic_params.get("tapfds_len", -1))
                vhostfds_len = int(nic_params.get("vhostfds_len", -1))
                if nic.get("tftp"):
                    tftp = utils_misc.get_path(root_dir, nic.get("tftp"))
                else:
                    tftp = None
                nettype = nic.get("nettype", "bridge")
                # don't force conversion add_nic()/add_net() optional parameter
                if 'tapfds' in nic:
                    tapfds = nic.tapfds
                else:
                    tapfds = None
                if 'vhostfds' in nic:
                    vhostfds = nic.vhostfds
                else:
                    vhostfds = None
                ifname = nic.get('ifname')
                queues = nic.get("queues", 1)
                # specify the number of MSI-X vectors that the card should have;
                # this option currently only affects virtio cards
                if nic_params.get("enable_msix_vectors") == "yes":
                    if "vectors" in nic:
                        vectors = nic.vectors
                    else:
                        vectors = 2 * int(queues) + 2
                else:
                    vectors = None

                # Setup some exclusive parameters if we are not running a
                # negative test.
                if nic_params.get("run_invalid_cmd_nic") != "yes":
                    if vhostfds or tapfds or add_queues:
                        helper = None
                    if vhostfds or tapfds:
                        add_queues = None
                    add_vhostfd = None
                    add_tapfd = None
                else:
                    if vhostfds and vhostfds_len > -1:
                        vhostfd_list = re.split(":", vhostfds)
                        if vhostfds_len < len(vhostfd_list):
                            vhostfds = ":".join(vhostfd_list[:vhostfds_len])
                    if tapfds and tapfds_len > -1:
                        tapfd_list = re.split(":", tapfds)
                        if tapfds_len < len(tapfd_list):
                            tapfds = ":".join(tapfd_list[:tapfds_len])

                # Handle the '-net nic' part
                add_nic(devices, vlan, nic_model, mac,
                        device_id, netdev_id, nic_extra,
                        nic_params.get("nic_pci_addr"),
                        bootindex, queues, vectors, pci_bus)

                # Handle the '-net tap' or '-net user' or '-netdev' part
                cmd, cmd_nd = add_net(devices, vlan, nettype, ifname, tftp,
                                      bootp, redirs, netdev_id, netdev_extra,
                                      tapfds, script, downscript, vhost,
                                      queues, vhostfds, add_queues, helper,
                                      add_tapfd, add_vhostfd)

                if vhostfds is None:
                    vhostfds = ""

                if tapfds is None:
                    tapfds = ""

                net_params = {'netdev_id': netdev_id,
                              'vhostfd': vhostfds.split(":")[0],
                              'vhostfds': vhostfds,
                              'tapfd': tapfds.split(":")[0],
                              'tapfds': tapfds,
                              'ifname': ifname,
                              }

                for i, (host_port, guest_port) in enumerate(redirs):
                    net_params["host_port%d" % i] = host_port
                    net_params["guest_port%d" % i] = guest_port

                # TODO: Is every NIC a PCI device?
                devices.insert(StrDev("NET-%s" % nettype, cmdline=cmd,
                                      params=net_params, cmdline_nd=cmd_nd))
            else:
                device_driver = nic_params.get("device_driver", "pci-assign")
                pci_id = vm.pa_pci_ids[iov]
                pci_id = ":".join(pci_id.split(":")[1:])
                add_pcidevice(devices, pci_id, params=nic_params,
                              device_driver=device_driver,
                              pci_bus=pci_bus)
                iov += 1

        mem = params.get("mem")
        if mem:
            devices.insert(StrDev('mem', cmdline=add_mem(devices, mem)))

        smp = int(params.get("smp", 0))
        vcpu_maxcpus = int(params.get("vcpu_maxcpus", 0))
        vcpu_sockets = int(params.get("vcpu_sockets", 0))
        vcpu_cores = int(params.get("vcpu_cores", 0))
        vcpu_threads = int(params.get("vcpu_threads", 0))

        # Force CPU threads to 2 when smp > 8.
        if smp > 8 and vcpu_threads <= 1:
            vcpu_threads = 2

        # Some versions of windows don't support more than 2 sockets of cpu,
        # here is a workaround to make all windows use only 2 sockets.
        if (vcpu_sockets and vcpu_sockets > 2
                and params.get("os_type") == 'windows'):
            vcpu_sockets = 2

        if smp == 0 or vcpu_sockets == 0:
            vcpu_cores = vcpu_cores or 1
            vcpu_threads = vcpu_threads or 1
            if smp and vcpu_sockets == 0:
                vcpu_sockets = int(smp / (vcpu_cores * vcpu_threads)) or 1
            else:
                vcpu_sockets = vcpu_sockets or 1
            if smp == 0:
                smp = vcpu_cores * vcpu_threads * vcpu_sockets
        else:
            if vcpu_cores == 0:
                vcpu_threads = vcpu_threads or 1
                vcpu_cores = int(smp / (vcpu_sockets * vcpu_threads)) or 1
            else:
                vcpu_threads = int(smp / (vcpu_cores * vcpu_sockets)) or 1

        self.cpuinfo.smp = smp
        self.cpuinfo.maxcpus = vcpu_maxcpus or smp
        self.cpuinfo.cores = vcpu_cores
        self.cpuinfo.threads = vcpu_threads
        self.cpuinfo.sockets = vcpu_sockets
        devices.insert(StrDev('smp', cmdline=add_smp(devices)))

        numa_total_cpus = 0
        numa_total_mem = 0
        for numa_node in params.objects("guest_numa_nodes"):
            numa_params = params.object_params(numa_node)
            numa_mem = numa_params.get("numa_mem")
            numa_cpus = numa_params.get("numa_cpus")
            numa_nodeid = numa_params.get("numa_nodeid")
            if numa_mem is not None:
                numa_total_mem += int(numa_mem)
            if numa_cpus is not None:
                numa_total_cpus += len(utils_misc.cpu_str_to_list(numa_cpus))
            devices.insert(StrDev('numa', cmdline=add_numa_node(devices)))

        if params.get("numa_consistency_check_cpu_mem", "no") == "yes":
            if (numa_total_cpus > int(smp) or numa_total_mem > int(mem)
                    or len(params.objects("guest_numa_nodes")) > int(smp)):
                logging.debug("-numa need %s vcpu and %s memory. It is not "
                              "matched the -smp and -mem. The vcpu number "
                              "from -smp is %s, and memory size from -mem is"
                              " %s" % (numa_total_cpus, numa_total_mem, smp,
                                       mem))
                raise virt_vm.VMDeviceError("The numa node cfg can not fit"
                                            " smp and memory cfg.")

        cpu_model = params.get("cpu_model")
        use_default_cpu_model = True
        if cpu_model:
            use_default_cpu_model = False
            for model in re.split(",", cpu_model):
                model = model.strip()
                if model not in support_cpu_model:
                    continue
                cpu_model = model
                break
            else:
                cpu_model = model
                logging.error("Non existing CPU model %s will be passed "
                              "to qemu (wrong config or negative test)", model)

        if use_default_cpu_model:
            cpu_model = params.get("default_cpu_model")

        if cpu_model:
            vendor = params.get("cpu_model_vendor")
            flags = params.get("cpu_model_flags")
            family = params.get("cpu_family")
            self.cpuinfo.model = cpu_model
            self.cpuinfo.vendor = vendor
            self.cpuinfo.flags = flags
            self.cpuinfo.family = family
            cmd = add_cpu_flags(devices, cpu_model, flags, vendor, family)
            devices.insert(StrDev('cpu', cmdline=cmd))

        # Add cdroms
        for cdrom in params.objects("cdroms"):
            image_params = params.object_params(cdrom)
            # FIXME: Use qemu_devices for handling indexes
            if image_params.get("boot_drive") == "no":
                continue
            if params.get("index_enable") == "yes":
                drive_index = image_params.get("drive_index")
                if drive_index:
                    index = drive_index
                else:
                    self.last_driver_index = get_index(self.last_driver_index)
                    index = str(self.last_driver_index)
                    self.last_driver_index += 1
            else:
                index = None
            image_bootindex = None
            image_boot = image_params.get("image_boot")
            if not re.search("boot=on\|off", devices.get_help_text(),
                             re.MULTILINE):
                if image_boot in ['yes', 'on', True]:
                    image_bootindex = str(self.last_boot_index)
                    self.last_boot_index += 1
                image_boot = "unused"
                image_bootindex = image_params.get(
                    'bootindex', image_bootindex)
            else:
                if image_boot in ['yes', 'on', True]:
                    if self.last_boot_index > 0:
                        image_boot = False
                    self.last_boot_index += 1
            iso = image_params.get("cdrom")
            if iso or image_params.get("cdrom_without_file") == "yes":
                devs = devices.cdroms_define_by_params(cdrom, image_params,
                                                       'cdrom', index,
                                                       image_boot,
                                                       image_bootindex)
                for _ in devs:
                    devices.insert(_)

        # We may want to add {floppy_otps} parameter for -fda, -fdb
        # {fat:floppy:}/path/. However vvfat is not usually recommended.
        for floppy_name in params.objects('floppies'):
            image_params = params.object_params(floppy_name)
            # TODO: Unify image, cdrom, floppy params
            image_params['drive_format'] = 'floppy'
            image_params[
                'image_readonly'] = image_params.get("floppy_readonly",
                                                     "no")
            # Use the absolute patch with floppies (pure *.vfd)
            image_params['image_raw_device'] = 'yes'
            image_params['image_name'] = utils_misc.get_path(
                data_dir.get_data_dir(),
                image_params["floppy_name"])
            image_params['image_format'] = None
            devs = devices.images_define_by_params(floppy_name, image_params,
                                                   media='')
            for _ in devs:
                devices.insert(_)

        # Add usb devices
        for usb_dev in params.objects("usb_devices"):
            usb_dev_params = params.object_params(usb_dev)
            devices.insert(devices.usb_by_params(usb_dev, usb_dev_params))

        tftp = params.get("tftp")
        if tftp:
            tftp = utils_misc.get_path(data_dir.get_data_dir(), tftp)
            devices.insert(StrDev('tftp', cmdline=add_tftp(devices, tftp)))

        bootp = params.get("bootp")
        if bootp:
            devices.insert(StrDev('bootp',
                                  cmdline=add_bootp(devices, bootp)))

        kernel = params.get("kernel")
        if kernel:
            kernel = utils_misc.get_path(data_dir.get_data_dir(), kernel)
            devices.insert(StrDev('kernel',
                                  cmdline=add_kernel(devices, kernel)))

        kernel_params = params.get("kernel_params")
        if kernel_params:
            cmd = add_kernel_cmdline(devices, kernel_params)
            devices.insert(StrDev('kernel-params', cmdline=cmd))

        initrd = params.get("initrd")
        if initrd:
            initrd = utils_misc.get_path(data_dir.get_data_dir(), initrd)
            devices.insert(StrDev('initrd',
                                  cmdline=add_initrd(devices, initrd)))

        for host_port, guest_port in redirs:
            cmd = add_tcp_redir(devices, host_port, guest_port)
            devices.insert(StrDev('tcp-redir', cmdline=cmd))

        cmd = ""
        if params.get("display") == "vnc":
            vnc_extra_params = params.get("vnc_extra_params")
            vnc_password = params.get("vnc_password", "no")
            cmd += add_vnc(devices, self.vnc_port, vnc_password,
                           vnc_extra_params)
        elif params.get("display") == "sdl":
            cmd += add_sdl(devices)
        elif params.get("display") == "nographic":
            cmd += add_nographic(devices)
        elif params.get("display") == "spice":
            if params.get("rhel5_spice"):
                spice_params = params.get("spice_params")
                cmd += add_spice_rhel5(devices, spice_params)
            else:
                spice_keys = (
                    "spice_port", "spice_password", "spice_addr", "spice_ssl",
                    "spice_tls_port", "spice_tls_ciphers", "spice_gen_x509",
                    "spice_x509_dir", "spice_x509_prefix",
                    "spice_x509_key_file", "spice_x509_cacert_file",
                    "spice_x509_key_password", "spice_x509_secure",
                    "spice_x509_cacert_subj", "spice_x509_server_subj",
                    "spice_secure_channels", "spice_image_compression",
                    "spice_jpeg_wan_compression",
                    "spice_zlib_glz_wan_compression", "spice_streaming_video",
                    "spice_agent_mouse", "spice_playback_compression",
                    "spice_ipv4", "spice_ipv6", "spice_x509_cert_file",
                    "disable_copy_paste", "spice_seamless_migration",
                    "listening_addr"
                )

                for skey in spice_keys:
                    value = params.get(skey, None)
                    if value:
                        self.spice_options[skey] = value

                cmd += add_spice()
        if cmd:
            devices.insert(StrDev('display', cmdline=cmd))

        if params.get("uuid") == "random":
            cmd = add_uuid(devices, vm.uuid)
            devices.insert(StrDev('uuid', cmdline=cmd))
        elif params.get("uuid"):
            cmd = add_uuid(devices, params.get("uuid"))
            devices.insert(StrDev('uuid', cmdline=cmd))

        if params.get("testdev") == "yes":
            cmd = add_testdev(devices, vm.get_testlog_filename())
            devices.insert(StrDev('testdev', cmdline=cmd))

        if params.get("isa_debugexit") == "yes":
            iobase = params.get("isa_debugexit_iobase")
            iosize = params.get("isa_debugexit_iosize")
            cmd = add_isa_debug_exit(devices, iobase, iosize)
            devices.insert(StrDev('isa_debugexit', cmdline=cmd))

        if params.get("disable_hpet") == "yes":
            devices.insert(StrDev('nohpet', cmdline=add_no_hpet(devices)))

        devices.insert(StrDev('rtc', cmdline=add_rtc(devices)))

        if devices.has_option("boot"):
            boot_order = params.get("boot_order", "cdn")
            boot_once = params.get("boot_once", "c")
            boot_menu = params.get("boot_menu", "off")
            cmd = add_boot(devices, boot_order, boot_once, boot_menu)
            devices.insert(StrDev('bootmenu', cmdline=cmd))

        p9_export_dir = params.get("9p_export_dir")
        if p9_export_dir:
            cmd = " -fsdev"
            p9_fs_driver = params.get("9p_fs_driver")
            if p9_fs_driver == "handle":
                cmd += " handle,id=local1,path=" + p9_export_dir
            elif p9_fs_driver == "proxy":
                cmd += " proxy,id=local1,socket="
            else:
                p9_fs_driver = "local"
                cmd += " local,id=local1,path=" + p9_export_dir

            # security model is needed only for local fs driver
            if p9_fs_driver == "local":
                p9_security_model = params.get("9p_security_model")
                if not p9_security_model:
                    p9_security_model = "none"
                cmd += ",security_model=" + p9_security_model
            elif p9_fs_driver == "proxy":
                p9_socket_name = params.get("9p_socket_name")
                if not p9_socket_name:
                    raise virt_vm.VMImageMissingError("Socket name not "
                                                      "defined")
                cmd += p9_socket_name

            p9_immediate_writeout = params.get("9p_immediate_writeout")
            if p9_immediate_writeout == "yes":
                cmd += ",writeout=immediate"

            p9_readonly = params.get("9p_readonly")
            if p9_readonly == "yes":
                cmd += ",readonly"

            devices.insert(StrDev('fsdev', cmdline=cmd))

            dev = QDevice('virtio-9p-pci', parent_bus=pci_bus)
            dev.set_param('fsdev', 'local1')
            dev.set_param('mount_tag', 'autotest_tag')
            devices.insert(dev)

        extra_params = params.get("extra_params")
        if extra_params:
            devices.insert(StrDev('extra', cmdline=extra_params))

        bios_path = params.get("bios_path")
        if bios_path:
            devices.insert(StrDev('bios', cmdline="-bios %s" % bios_path))

        disable_kvm_option = ""
        if (devices.has_option("no-kvm")):
            disable_kvm_option = "-no-kvm"

        enable_kvm_option = ""
        if (devices.has_option("enable-kvm")):
            enable_kvm_option = "-enable-kvm"

        if (params.get("disable_kvm", "no") == "yes"):
            params["enable_kvm"] = "no"

        if (params.get("enable_kvm", "yes") == "no"):
            devices.insert(StrDev('nokvm', cmdline=disable_kvm_option))
            logging.debug("qemu will run in TCG mode")
        else:
            devices.insert(StrDev('kvm', cmdline=enable_kvm_option))
            logging.debug("qemu will run in KVM mode")

        self.no_shutdown = (devices.has_option("no-shutdown") and
                            params.get("disable_shutdown", "no") == "yes")
        if self.no_shutdown:
            devices.insert(StrDev('noshutdown', cmdline="-no-shutdown"))

        user_runas = params.get("user_runas")
        if devices.has_option("runas") and user_runas:
            devices.insert(StrDev('runas', cmdline="-runas %s" % user_runas))

        if params.get("enable_sga") == "yes":
            devices.insert(StrDev('sga', cmdline=add_sga(devices)))

        if params.get("smartcard", "no") == "yes":
            sc_chardev = params.get("smartcard_chardev")
            sc_id = params.get("smartcard_id")
            devices.insert(StrDev('smartcard',
                                  cmdline=add_smartcard(devices, sc_chardev, sc_id)))

        if params.get("enable_watchdog", "no") == "yes":
            cmd = add_watchdog(devices,
                               params.get("watchdog_device_type", None),
                               params.get("watchdog_action", "reset"))
            devices.insert(StrDev('watchdog', cmdline=cmd))

        option_roms = params.get("option_roms")
        if option_roms:
            cmd = ""
            for opt_rom in option_roms.split():
                cmd += add_option_rom(devices, opt_rom)
            if cmd:
                devices.insert(StrDev('ROM', cmdline=cmd))

        return devices

    def _nic_tap_add_helper(self, nic):
        if nic.nettype == 'macvtap':
            macvtap_mode = self.params.get("macvtap_mode", "vepa")
            nic.tapfds = utils_net.create_and_open_macvtap(nic.ifname,
                                                           macvtap_mode, nic.queues, nic.netdst, nic.mac)
        else:
            nic.tapfds = utils_net.open_tap("/dev/net/tun", nic.ifname,
                                            queues=nic.queues, vnet_hdr=True)
            logging.debug("Adding VM %s NIC ifname %s to bridge %s",
                          self.name, nic.ifname, nic.netdst)
            if nic.nettype == 'bridge':
                utils_net.add_to_bridge(nic.ifname, nic.netdst)
        utils_net.bring_up_ifname(nic.ifname)

    def _nic_tap_remove_helper(self, nic):
        try:
            if nic.nettype == 'macvtap':
                logging.info("Remove macvtap ifname %s", nic.ifname)
                tap = utils_net.Macvtap(nic.ifname)
                tap.delete()
            else:
                logging.debug("Removing VM %s NIC ifname %s from bridge %s",
                              self.name, nic.ifname, nic.netdst)
                if nic.tapfds:
                    for i in nic.tapfds.split(':'):
                        os.close(int(i))
                if nic.vhostfds:
                    for i in nic.vhostfds.split(':'):
                        os.close(int(i))
                if nic.ifname and nic.ifname not in utils_net.get_net_if():
                    _, br_name = utils_net.find_current_bridge(nic.ifname)
                    if br_name == nic.netdst:
                        utils_net.del_from_bridge(nic.ifname, nic.netdst)
        except TypeError:
            pass

    def create_serial_console(self):
        """
        Establish a session with the serial console.

        Let's consider the first serial port as serial console.
        Note: requires a version of netcat that supports -U
        """
        try:
            tmp_serial = self.serial_ports[0]
        except IndexError:
            raise virt_vm.VMConfigMissingError(self.name, "isa_serial")

        self.serial_console = aexpect.ShellSession(
            "nc -U %s" % self.get_serial_console_filename(tmp_serial),
            auto_close=False,
            output_func=utils_misc.log_line,
            output_params=("serial-%s-%s.log" % (tmp_serial, self.name),),
            prompt=self.params.get("shell_prompt", "[\#\$]"))
        del tmp_serial

    def update_system_dependent_devs(self):
        # Networking
        devices = self.devices
        params = self.params
        redirs = []
        for redir_name in params.objects("redirs"):
            redir_params = params.object_params(redir_name)
            guest_port = int(redir_params.get("guest_port"))
            host_port = self.redirs.get(guest_port)
            redirs += [(host_port, guest_port)]

        for nic in self.virtnet:
            nic_params = params.object_params(nic.nic_name)
            if nic_params.get('pci_assignable') == "no":
                script = nic_params.get("nic_script")
                downscript = nic_params.get("nic_downscript")
                script_dir = data_dir.get_data_dir()
                if script:
                    script = utils_misc.get_path(script_dir, script)
                if downscript:
                    downscript = utils_misc.get_path(script_dir,
                                                     downscript)
                # setup nic parameters as needed
                # add_netdev if netdev_id not set
                nic = self.add_nic(**dict(nic))
                # gather set values or None if unset
                netdev_id = nic.get('netdev_id')
                # don't force conversion add_nic()/add_net() optional
                # parameter
                if 'tapfds' in nic:
                    tapfds = nic.tapfds
                else:
                    tapfds = ""
                if 'vhostfds' in nic:
                    vhostfds = nic.vhostfds
                else:
                    vhostfds = ""
                ifname = nic.get('ifname')
                # specify the number of MSI-X vectors that the card should
                # have this option currently only affects virtio cards

                net_params = {'netdev_id': netdev_id,
                              'vhostfd': vhostfds.split(":")[0],
                              'vhostfds': vhostfds,
                              'tapfd': tapfds.split(":")[0],
                              'tapfds': tapfds,
                              'ifname': ifname,
                              }

                for i, (host_port, guest_port) in enumerate(redirs):
                    net_params["host_port%d" % i] = host_port
                    net_params["guest_port%d" % i] = guest_port

                # TODO: Is every NIC a PCI device?
                devs = devices.get_by_params({'netdev_id': netdev_id})
                # TODO: Is every NIC a PCI device?
                if len(devs) > 1:
                    logging.error("There are %d devices with netdev_id %s."
                                  " This shouldn't happens." % (len(devs),
                                                                netdev_id))
                devs[0].params.update(net_params)

    @error.context_aware
    def create(self, name=None, params=None, root_dir=None,
               timeout=CREATE_TIMEOUT, migration_mode=None,
               migration_exec_cmd=None, migration_fd=None,
               mac_source=None):
        """
        Start the VM by running a qemu command.
        All parameters are optional. If name, params or root_dir are not
        supplied, the respective values stored as class attributes are used.

        :param name: The name of the object
        :param params: A dict containing VM params
        :param root_dir: Base directory for relative filenames
        :param migration_mode: If supplied, start VM for incoming migration
                using this protocol (either 'rdma', 'x-rdma', 'rdma', 'tcp', 'unix' or 'exec')
        :param migration_exec_cmd: Command to embed in '-incoming "exec: ..."'
                (e.g. 'gzip -c -d filename') if migration_mode is 'exec'
                default to listening on a random TCP port
        :param migration_fd: Open descriptor from machine should migrate.
        :param mac_source: A VM object from which to copy MAC addresses. If not
                specified, new addresses will be generated.

        :raise VMCreateError: If qemu terminates unexpectedly
        :raise VMKVMInitError: If KVM initialization fails
        :raise VMHugePageError: If hugepage initialization fails
        :raise VMImageMissingError: If a CD image is missing
        :raise VMHashMismatchError: If a CD image hash has doesn't match the
                expected hash
        :raise VMBadPATypeError: If an unsupported PCI assignment type is
                requested
        :raise VMPAError: If no PCI assignable devices could be assigned
        :raise TAPCreationError: If fail to create tap fd
        :raise BRAddIfError: If fail to add a tap to a bridge
        :raise TAPBringUpError: If fail to bring up a tap
        :raise PrivateBridgeError: If fail to bring the private bridge
        """
        error.context("creating '%s'" % self.name)
        self.destroy(free_mac_addresses=False)

        if name is not None:
            self.name = name
            self.devices = None     # Representation changed
        if params is not None:
            self.params = params
            self.devices = None     # Representation changed
        if root_dir is not None:
            self.root_dir = root_dir
            self.devices = None     # Representation changed
        name = self.name
        params = self.params
        root_dir = self.root_dir

        # Verify the md5sum of the ISO images
        for cdrom in params.objects("cdroms"):
            cdrom_params = params.object_params(cdrom)
            iso = cdrom_params.get("cdrom")
            if iso:
                iso = utils_misc.get_path(data_dir.get_data_dir(), iso)
                if not os.path.exists(iso):
                    raise virt_vm.VMImageMissingError(iso)
                compare = False
                if cdrom_params.get("skip_hash"):
                    logging.debug("Skipping hash comparison")
                elif cdrom_params.get("md5sum_1m"):
                    logging.debug("Comparing expected MD5 sum with MD5 sum of "
                                  "first MB of ISO file...")
                    actual_hash = utils.hash_file(iso, 1048576, method="md5")
                    expected_hash = cdrom_params.get("md5sum_1m")
                    compare = True
                elif cdrom_params.get("md5sum"):
                    logging.debug("Comparing expected MD5 sum with MD5 sum of "
                                  "ISO file...")
                    actual_hash = utils.hash_file(iso, method="md5")
                    expected_hash = cdrom_params.get("md5sum")
                    compare = True
                elif cdrom_params.get("sha1sum"):
                    logging.debug("Comparing expected SHA1 sum with SHA1 sum "
                                  "of ISO file...")
                    actual_hash = utils.hash_file(iso, method="sha1")
                    expected_hash = cdrom_params.get("sha1sum")
                    compare = True
                if compare:
                    if actual_hash == expected_hash:
                        logging.debug("Hashes match")
                    else:
                        raise virt_vm.VMHashMismatchError(actual_hash,
                                                          expected_hash)

        # Make sure the following code is not executed by more than one thread
        # at the same time
        lockfile = open(CREATE_LOCK_FILENAME, "w+")
        fcntl.lockf(lockfile, fcntl.LOCK_EX)

        try:
            # Handle port redirections
            redir_names = params.objects("redirs")
            host_ports = utils_misc.find_free_ports(
                5000, 6000, len(redir_names))

            old_redirs = None
            if self.redirs:
                old_redirs = self.redirs

            self.redirs = {}
            for i in range(len(redir_names)):
                redir_params = params.object_params(redir_names[i])
                guest_port = int(redir_params.get("guest_port"))
                self.redirs[guest_port] = host_ports[i]

            if self.redirs != old_redirs:
                self.devices = None

            # Update the network related parameters as well to conform to
            # expected behavior on VM creation
            getattr(self, 'virtnet').__init__(self.params,
                                              self.name,
                                              self.instance)

            # Generate basic parameter values for all NICs and create TAP fd
            for nic in self.virtnet:
                nic_params = params.object_params(nic.nic_name)
                pa_type = nic_params.get("pci_assignable")
                if pa_type and pa_type != "no":
                    device_driver = nic_params.get("device_driver",
                                                   "pci-assign")
                    if "mac" not in nic:
                        self.virtnet.generate_mac_address(nic["nic_name"])
                    mac = nic["mac"]
                    if self.pci_assignable is None:
                        self.pci_assignable = test_setup.PciAssignable(
                            driver=params.get("driver"),
                            driver_option=params.get("driver_option"),
                            host_set_flag=params.get("host_setup_flag"),
                            kvm_params=params.get("kvm_default"),
                            vf_filter_re=params.get("vf_filter_re"),
                            pf_filter_re=params.get("pf_filter_re"),
                            device_driver=device_driver)
                    # Virtual Functions (VF) assignable devices
                    if pa_type == "vf":
                        self.pci_assignable.add_device(device_type=pa_type,
                                                       mac=mac,
                                                       name=nic_params.get("device_name"))
                    # Physical NIC (PF) assignable devices
                    elif pa_type == "pf":
                        self.pci_assignable.add_device(device_type=pa_type,
                                                       name=nic_params.get("device_name"))
                    else:
                        raise virt_vm.VMBadPATypeError(pa_type)
                else:
                    # fill in key values, validate nettype
                    # note: make_create_command() calls vm.add_nic (i.e. on a
                    # copy)
                    if nic_params.get('netdst') == 'private':
                        nic.netdst = (test_setup.
                                      PrivateBridgeConfig(nic_params).brname)

                    nic = self.add_nic(**dict(nic))  # implied add_netdev

                    if mac_source:
                        # Will raise exception if source doesn't
                        # have cooresponding nic
                        logging.debug("Copying mac for nic %s from VM %s"
                                      % (nic.nic_name, mac_source.name))
                        nic.mac = mac_source.get_mac_address(nic.nic_name)

                    if nic.ifname in utils_net.get_net_if():
                        self.virtnet.generate_ifname(nic.nic_name)
                    elif (utils_net.find_current_bridge(nic.ifname)[1] ==
                          nic.netdst):
                        utils_net.del_from_bridge(nic.ifname, nic.netdst)

                    if nic.nettype in ['bridge', 'network', 'macvtap']:
                        self._nic_tap_add_helper(nic)

                    if ((nic_params.get("vhost") in ['on',
                                                     'force',
                                                     'vhost=on']) and
                            (nic_params.get("enable_vhostfd", "yes") == "yes")):
                        vhostfds = []
                        for i in xrange(int(nic.queues)):
                            vhostfds.append(str(os.open("/dev/vhost-net",
                                                        os.O_RDWR)))
                        nic.vhostfds = ':'.join(vhostfds)
                    elif nic.nettype == 'user':
                        logging.info("Assuming dependencies met for "
                                     "user mode nic %s, and ready to go"
                                     % nic.nic_name)

                    self.virtnet.update_db()

            # Find available VNC port, if needed
            if params.get("display") == "vnc":
                self.vnc_port = utils_misc.find_free_port(5900, 6100)

            # Find random UUID if specified 'uuid = random' in config file
            if params.get("uuid") == "random":
                f = open("/proc/sys/kernel/random/uuid")
                self.uuid = f.read().strip()
                f.close()

            if self.pci_assignable is not None:
                self.pa_pci_ids = self.pci_assignable.request_devs()

                if self.pa_pci_ids:
                    logging.debug("Successfully assigned devices: %s",
                                  self.pa_pci_ids)
                else:
                    raise virt_vm.VMPAError(pa_type)

            if (name is None and params is None and root_dir is None
                    and self.devices is not None):
                self.update_system_dependent_devs()
            # Make qemu command
            try:
                self.devices = self.make_create_command()
                logging.debug(self.devices.str_short())
                logging.debug(self.devices.str_bus_short())
                qemu_command = self.devices.cmdline()
            except error.TestNAError:
                # TestNAErrors should be kept as-is so we generate SKIP
                # results instead of bogus FAIL results
                raise
            except Exception:
                for nic in self.virtnet:
                    self._nic_tap_remove_helper(nic)
                # TODO: log_last_traceback is being moved into autotest.
                # use autotest.client.shared.base_utils when it's completed.
                if 'log_last_traceback' in utils.__dict__:
                    utils.log_last_traceback('Fail to create qemu command:')
                else:
                    utils_misc.log_last_traceback('Fail to create qemu'
                                                  'command:')
                raise virt_vm.VMStartError(self.name, 'Error occurred while '
                                           'executing make_create_command(). '
                                           'Check the log for traceback.')

            # Add migration parameters if required
            if migration_mode in ["tcp", "rdma", "x-rdma"]:
                self.migration_port = utils_misc.find_free_port(5200, 6000)
                qemu_command += (" -incoming " + migration_mode +
                                 ":0:%d" % self.migration_port)
            elif migration_mode == "unix":
                self.migration_file = "/tmp/migration-unix-%s" % self.instance
                qemu_command += " -incoming unix:%s" % self.migration_file
            elif migration_mode == "exec":
                if migration_exec_cmd is None:
                    self.migration_port = utils_misc.find_free_port(5200, 6000)
                    qemu_command += (' -incoming "exec:nc -l %s"' %
                                     self.migration_port)
                else:
                    qemu_command += (' -incoming "exec:%s"' %
                                     migration_exec_cmd)
            elif migration_mode == "fd":
                qemu_command += ' -incoming "fd:%d"' % (migration_fd)

            p9_fs_driver = params.get("9p_fs_driver")
            if p9_fs_driver == "proxy":
                proxy_helper_name = params.get("9p_proxy_binary",
                                               "virtfs-proxy-helper")
                proxy_helper_cmd = utils_misc.get_path(root_dir,
                                                       proxy_helper_name)
                if not proxy_helper_cmd:
                    raise virt_vm.VMConfigMissingError(self.name,
                                                       "9p_proxy_binary")

                p9_export_dir = params.get("9p_export_dir")
                if not p9_export_dir:
                    raise virt_vm.VMConfigMissingError(self.name,
                                                       "9p_export_dir")

                proxy_helper_cmd += " -p " + p9_export_dir
                proxy_helper_cmd += " -u 0 -g 0"
                p9_socket_name = params.get("9p_socket_name")
                proxy_helper_cmd += " -s " + p9_socket_name
                proxy_helper_cmd += " -n"

                logging.info("Running Proxy Helper:\n%s", proxy_helper_cmd)
                self.process = aexpect.run_tail(proxy_helper_cmd,
                                                None,
                                                logging.info,
                                                "[9p proxy helper]",
                                                auto_close=False)
            else:
                logging.info("Running qemu command (reformatted):\n%s",
                             qemu_command.replace(" -", " \\\n    -"))
                self.qemu_command = qemu_command
                self.process = aexpect.run_tail(qemu_command,
                                                None,
                                                logging.info,
                                                "[qemu output] ",
                                                auto_close=False)

            logging.info("Created qemu process with parent PID %d",
                         self.process.get_pid())
            self.start_time = time.time()
            self.start_monotonic_time = utils_misc.monotonic_time()

            # test doesn't need to hold tapfd's open
            for nic in self.virtnet:
                if 'tapfds' in nic:  # implies bridge/tap
                    try:
                        for i in nic.tapfds.split(':'):
                            os.close(int(i))
                        # qemu process retains access via open file
                        # remove this attribute from virtnet because
                        # fd numbers are not always predictable and
                        # vm instance must support cloning.
                        del nic['tapfds']
                    # File descriptor is already closed
                    except OSError:
                        pass
                if 'vhostfds' in nic:
                    try:
                        for i in nic.vhostfds.split(':'):
                            os.close(int(i))
                        del nic['vhostfds']
                    except OSError:
                        pass

            # Make sure qemu is not defunct
            if self.process.is_defunct():
                logging.error("Bad things happened, qemu process is defunct")
                err = ("Qemu is defunct.\nQemu output:\n%s"
                       % self.process.get_output())
                self.destroy()
                raise virt_vm.VMStartError(self.name, err)

            # Make sure the process was started successfully
            if not self.process.is_alive():
                status = self.process.get_status()
                output = self.process.get_output().strip()
                migration_in_course = migration_mode is not None
                unknown_protocol = "unknown migration protocol" in output
                if migration_in_course and unknown_protocol:
                    e = VMMigrateProtoUnsupportedError(migration_mode, output)
                else:
                    e = virt_vm.VMCreateError(qemu_command, status, output)
                self.destroy()
                raise e

            # Establish monitor connections
            self.monitors = []
            for monitor_name in params.objects("monitors"):
                monitor_params = params.object_params(monitor_name)
                try:
                    monitor = qemu_monitor.wait_for_create_monitor(self,
                                                                   monitor_name, monitor_params, timeout)
                except qemu_monitor.MonitorConnectError, detail:
                    logging.error(detail)
                    self.destroy()
                    raise

                # Add this monitor to the list
                self.monitors += [monitor]

            # Create isa serial ports.
            for serial in params.objects("isa_serials"):
                self.serial_ports.append(serial)

            # Create virtio_ports (virtio_serialports and virtio_consoles)
            i = 0
            self.virtio_ports = []
            for port in params.objects("virtio_ports"):
                port_params = params.object_params(port)
                if port_params.get('virtio_port_chardev') == "spicevmc":
                    filename = 'dev%s' % port
                else:
                    filename = self.get_virtio_port_filename(port)
                port_name = port_params.get('virtio_port_name_prefix', None)
                if port_name:   # If port_name_prefix was used
                    port_name = port_name + str(i)
                else:           # Implicit name - port
                    port_name = port
                if port_params.get('virtio_port_type') in ("console",
                                                           "virtio_console"):
                    self.virtio_ports.append(
                        qemu_virtio_port.VirtioConsole(port, port_name,
                                                       filename))
                else:
                    self.virtio_ports.append(
                        qemu_virtio_port.VirtioSerial(port, port_name,
                                                      filename))
                i += 1

            # Get the output so far, to see if we have any problems with
            # KVM modules or with hugepage setup.
            output = self.process.get_output()

            if re.search("Could not initialize KVM", output, re.IGNORECASE):
                e = virt_vm.VMKVMInitError(
                    qemu_command, self.process.get_output())
                self.destroy()
                raise e

            if "alloc_mem_area" in output:
                e = virt_vm.VMHugePageError(
                    qemu_command, self.process.get_output())
                self.destroy()
                raise e

            logging.debug("VM appears to be alive with PID %s", self.get_pid())
            vcpu_thread_pattern = self.params.get("vcpu_thread_pattern",
                                                  r"thread_id.?[:|=]\s*(\d+)")
            self.vcpu_threads = self.get_vcpu_pids(vcpu_thread_pattern)

            vhost_thread_pattern = params.get("vhost_thread_pattern",
                                              r"\w+\s+(\d+)\s.*\[vhost-%s\]")
            self.vhost_threads = self.get_vhost_threads(vhost_thread_pattern)

            self.create_serial_console()

            for key, value in self.logs.items():
                outfile = "%s-%s.log" % (key, name)
                self.logsessions[key] = aexpect.Tail(
                    "nc -U %s" % value,
                    auto_close=False,
                    output_func=utils_misc.log_line,
                    output_params=(outfile,))
                self.logsessions[key].set_log_file(outfile)

            if params.get("paused_after_start_vm") != "yes":
                # start guest
                if self.monitor.verify_status("paused"):
                    try:
                        self.monitor.cmd("cont")
                    except qemu_monitor.QMPCmdError, e:
                        if ((e.data['class'] == "MigrationExpected") and
                                (migration_mode is not None)):
                            logging.debug("Migration did not start yet...")
                        else:
                            raise e

            # Update mac and IP info for assigned device
            # NeedFix: Can we find another way to get guest ip?
            if params.get("mac_changeable") == "yes":
                utils_net.update_mac_ip_address(self, params)

        finally:
            fcntl.lockf(lockfile, fcntl.LOCK_UN)
            lockfile.close()

    def wait_for_status(self, status, timeout, first=0.0, step=1.0, text=None):
        """
        Wait until the VM status changes to specified status

        :param timeout: Timeout in seconds
        :param first: Time to sleep before first attempt
        :param steps: Time to sleep between attempts in seconds
        :param text: Text to print while waiting, for debug purposes

        :return: True in case the status has changed before timeout, otherwise
                 return None.
        """
        return utils_misc.wait_for(lambda: self.monitor.verify_status(status),
                                   timeout, first, step, text)

    def wait_until_paused(self, timeout):
        """
        Wait until the VM is paused.

        :param timeout: Timeout in seconds.

        :return: True in case the VM is paused before timeout, otherwise
                 return None.
        """
        return self.wait_for_status("paused", timeout)

    def wait_until_dead(self, timeout, first=0.0, step=1.0):
        """
        Wait until VM is dead.

        :return: True if VM is dead before timeout, otherwise returns None.

        :param timeout: Timeout in seconds
        :param first: Time to sleep before first attempt
        :param steps: Time to sleep between attempts in seconds
        """
        return utils_misc.wait_for(self.is_dead, timeout, first, step)

    def wait_for_shutdown(self, timeout=60):
        """
        Wait until guest shuts down.

        Helps until the VM is shut down by the guest.

        :return: True in case the VM was shut down, None otherwise.

        Note that the VM is not necessarily dead when this function returns
        True. If QEMU is running in -no-shutdown mode, the QEMU process
        may be still alive.
        """
        if self.no_shutdown:
            return self.wait_until_paused(timeout)
        else:
            return self.wait_until_dead(timeout, 1, 1)

    def graceful_shutdown(self, timeout=60):
        """
        Try to gracefully shut down the VM.

        :return: True if VM was successfully shut down, None otherwise.

        Note that the VM is not necessarily dead when this function returns
        True. If QEMU is running in -no-shutdown mode, the QEMU process
        may be still alive.
        """
        if self.params.get("shutdown_command"):
            # Try to destroy with shell command
            logging.debug("Shutting down VM %s (shell)", self.name)
            try:
                if len(self.virtnet) > 0:
                    session = self.login()
                else:
                    session = self.serial_login()
            except (IndexError), e:
                try:
                    session = self.serial_login()
                except (remote.LoginError, virt_vm.VMError), e:
                    logging.debug(e)
            except (remote.LoginError, virt_vm.VMError), e:
                logging.debug(e)
            else:
                try:
                    # Send the shutdown command
                    session.sendline(self.params.get("shutdown_command"))
                    if self.wait_for_shutdown(timeout):
                        return True
                finally:
                    session.close()

    def _cleanup(self, free_mac_addresses):
        """
        Do cleanup works
            .removes VM monitor files.
            .process close
            .serial_console close
            .logsessions close
            .delete tmp files
            .free_mac_addresses, if needed
            .delete macvtap, if needed

        :param free_mac_addresses: Whether to release the VM's NICs back
                to the address pool.
        """
        self.monitors = []
        if self.pci_assignable:
            self.pci_assignable.release_devs()
            self.pci_assignable = None
        if self.process:
            self.process.close()
        if self.serial_console:
            self.serial_console.close()
        if self.logsessions:
            for key in self.logsessions:
                self.logsessions[key].close()

        # Generate the tmp file which should be deleted.
        file_list = [self.get_testlog_filename()]
        file_list += qemu_monitor.get_monitor_filenames(self)
        file_list += self.get_virtio_port_filenames()
        file_list += self.get_serial_console_filenames()
        file_list += self.logs.values()

        for f in file_list:
            try:
                os.unlink(f)
            except OSError:
                pass

        if hasattr(self, "migration_file"):
            try:
                os.unlink(self.migration_file)
            except OSError:
                pass

        if free_mac_addresses:
            for nic_index in xrange(0, len(self.virtnet)):
                self.free_mac_address(nic_index)

        for nic in self.virtnet:
            if nic.nettype == 'macvtap':
                tap = utils_net.Macvtap(nic.ifname)
                tap.delete()
            elif nic.ifname and nic.ifname not in utils_net.get_net_if():
                _, br_name = utils_net.find_current_bridge(nic.ifname)
                if br_name == nic.netdst:
                    utils_net.del_from_bridge(nic.ifname, nic.netdst)

    def destroy(self, gracefully=True, free_mac_addresses=True):
        """
        Destroy the VM.

        If gracefully is True, first attempt to shutdown the VM with a shell
        command.  Then, attempt to destroy the VM via the monitor with a 'quit'
        command.  If that fails, send SIGKILL to the qemu process.

        :param gracefully: If True, an attempt will be made to end the VM
                using a shell command before trying to end the qemu process
                with a 'quit' or a kill signal.
        :param free_mac_addresses: If True, the MAC addresses used by the VM
                will be freed.
        """
        try:
            # Is it already dead?
            if self.is_dead():
                return

            logging.debug("Destroying VM %s (PID %s)", self.name,
                          self.get_pid())

            kill_timeout = int(self.params.get("kill_timeout", "60"))

            if gracefully:
                self.graceful_shutdown(kill_timeout)
                if self.is_dead():
                    logging.debug("VM %s down (shell)", self.name)
                    return
                else:
                    logging.debug("VM %s failed to go down (shell)", self.name)

            if self.monitor:
                # Try to finish process with a monitor command
                logging.debug("Ending VM %s process (monitor)", self.name)
                try:
                    self.monitor.quit()
                except Exception, e:
                    logging.warn(e)
                    if self.is_dead():
                        logging.warn("VM %s down during try to kill it "
                                     "by monitor", self.name)
                        return
                else:
                    # Wait for the VM to be really dead
                    if self.wait_until_dead(5, 0.5, 0.5):
                        logging.debug("VM %s down (monitor)", self.name)
                        return
                    else:
                        logging.debug("VM %s failed to go down (monitor)",
                                      self.name)

            # If the VM isn't dead yet...
            pid = self.process.get_pid()
            logging.debug("Ending VM %s process (killing PID %s)",
                          self.name, pid)
            utils_misc.kill_process_tree(pid, 9)

            # Wait for the VM to be really dead
            if utils_misc.wait_for(self.is_dead, 5, 0.5, 0.5):
                logging.debug("VM %s down (process killed)", self.name)
                return

            # If all else fails, we've got a zombie...
            logging.error("VM %s (PID %s) is a zombie!", self.name,
                          self.process.get_pid())

        finally:
            self._cleanup(free_mac_addresses)

    @property
    def monitor(self):
        """
        Return the main monitor object, selected by the parameter main_monitor.
        If main_monitor isn't defined, return the first monitor.
        If no monitors exist, or if main_monitor refers to a nonexistent
        monitor, return None.
        """
        for m in self.monitors:
            if m.name == self.params.get("main_monitor"):
                return m
        if self.monitors and not self.params.get("main_monitor"):
            return self.monitors[0]
        return None

    def get_monitors_by_type(self, mon_type):
        """
        Return list of monitors of mon_type type.
        :param mon_type: desired monitor type (qmp, human)
        """
        return [_ for _ in self.monitors if _.protocol == mon_type]

    def get_peer(self, netid):
        """
        Return the peer of netdev or network deivce.

        :param netid: id of netdev or device
        :return: id of the peer device otherwise None
        """
        o = self.monitor.info("network")
        network_info = o
        if isinstance(o, dict):
            network_info = o.get["return"]

        netdev_peer_re = self.params.get("netdev_peer_re")
        if not netdev_peer_re:
            default_netdev_peer_re = "\s{2,}(.*?): .*?\\\s(.*?):"
            logging.warning("Missing config netdev_peer_re for VM %s, "
                            "using default %s", self.name,
                            default_netdev_peer_re)
            netdev_peer_re = default_netdev_peer_re

        pairs = re.findall(netdev_peer_re, network_info, re.S)
        for nic, tap in pairs:
            if nic == netid:
                return tap
            if tap == netid:
                return nic

        return None

    def get_ifname(self, nic_index=0):
        """
        Return the ifname of a bridge/tap device associated with a NIC.

        :param nic_index: Index of the NIC
        """
        return self.virtnet[nic_index].ifname

    def get_pid(self):
        """
        Return the VM's PID.  If the VM is dead return None.

        :note: This works under the assumption that self.process.get_pid()
        :return: the PID of the parent shell process.
        """
        try:
            children = commands.getoutput("ps --ppid=%d -o pid=" %
                                          self.process.get_pid()).split()
            return int(children[0])
        except (TypeError, IndexError, ValueError):
            return None

    def get_shell_pid(self):
        """
        Return the PID of the parent shell process.

        :note: This works under the assumption that self.process.get_pid()
        :return: the PID of the parent shell process.
        """
        return self.process.get_pid()

    def get_vnc_port(self):
        """
        Return self.vnc_port.
        """

        return self.vnc_port

    def get_vcpu_pids(self, vcpu_thread_pattern):
        """
        Return the list of vcpu PIDs

        :return: the list of vcpu PIDs
        """
        return [int(_) for _ in re.findall(vcpu_thread_pattern,
                                           str(self.monitor.info("cpus")))]

    def get_vhost_threads(self, vhost_thread_pattern):
        """
        Return the list of vhost threads PIDs

        :param vhost_thread_pattern: a regex to match the vhost threads
        :type vhost_thread_pattern: string
        :return: a list of vhost threads PIDs
        :rtype: list of integer
        """
        return [int(_) for _ in re.findall(vhost_thread_pattern %
                                           self.get_pid(),
                                           utils.system_output("ps aux"))]

    def get_shared_meminfo(self):
        """
        Returns the VM's shared memory information.

        :return: Shared memory used by VM (MB)
        """
        if self.is_dead():
            logging.error("Could not get shared memory info from dead VM.")
            return None

        filename = "/proc/%d/statm" % self.get_pid()
        shm = int(open(filename).read().split()[2])
        # statm stores informations in pages, translate it to MB
        return shm * 4.0 / 1024

    def get_spice_var(self, spice_var):
        """
        Returns string value of spice variable of choice or None
        :param spice_var - spice related variable 'spice_port', ...
        """
        return self.spice_options.get(spice_var, None)

    @error.context_aware
    def hotplug_vcpu(self, cpu_id=None, plug_command=""):
        """
        Hotplug a vcpu, if not assign the cpu_id, will use the minimum unused.
        the function will use the plug_command if you assigned it, else the
        function will use the command automatically generated based on the
        type of monitor

        :param cpu_id  the cpu_id you want hotplug.
        """
        vcpu_threads_count = len(self.vcpu_threads)
        plug_cpu_id = cpu_id
        if plug_cpu_id is None:
            plug_cpu_id = vcpu_threads_count
        if plug_command:
            vcpu_add_cmd = plug_command % plug_cpu_id
        else:
            if self.monitor.protocol == 'human':
                vcpu_add_cmd = "cpu_set %s online" % plug_cpu_id
            elif self.monitor.protocol == 'qmp':
                vcpu_add_cmd = "cpu-add id=%s" % plug_cpu_id

        try:
            self.monitor.verify_supported_cmd(vcpu_add_cmd.split()[0])
        except qemu_monitor.MonitorNotSupportedCmdError:
            raise error.TestNAError("%s monitor not support cmd '%s'" %
                                    (self.monitor.protocol, vcpu_add_cmd))
        try:
            cmd_output = self.monitor.send_args_cmd(vcpu_add_cmd)
        except qemu_monitor.QMPCmdError, e:
            return (False, str(e))

        vcpu_thread_pattern = self.params.get("vcpu_thread_pattern",
                                              r"thread_id.?[:|=]\s*(\d+)")
        self.vcpu_threads = self.get_vcpu_pids(vcpu_thread_pattern)
        if len(self.vcpu_threads) == vcpu_threads_count + 1:
            return(True, plug_cpu_id)
        else:
            return(False, cmd_output)

    @error.context_aware
    def hotplug_nic(self, **params):
        """
        Convenience method wrapper for add_nic() and add_netdev().

        :return: dict-like object containing nic's details
        """
        nic_name = self.add_nic(**params)["nic_name"]
        self.activate_netdev(nic_name)
        self.activate_nic(nic_name)
        return self.virtnet[nic_name]

    @error.context_aware
    def hotunplug_nic(self, nic_index_or_name):
        """
        Convenience method wrapper for del/deactivate nic and netdev.
        """
        # make sure we got a name
        nic_name = self.virtnet[nic_index_or_name].nic_name
        self.deactivate_nic(nic_name)
        self.deactivate_netdev(nic_name)
        self.del_nic(nic_name)

    @error.context_aware
    def add_netdev(self, **params):
        """
        Hotplug a netdev device.

        :param params: NIC info. dict.
        :return: netdev_id
        """
        nic_name = params['nic_name']
        nic = self.virtnet[nic_name]
        nic_index = self.virtnet.nic_name_index(nic_name)
        nic.set_if_none('netdev_id', utils_misc.generate_random_id())
        nic.set_if_none('ifname', self.virtnet.generate_ifname(nic_index))
        nic.set_if_none('netdev_extra_params',
                        params.get('netdev_extra_params'))
        nic.set_if_none('nettype', 'bridge')
        if nic.nettype in ['bridge', 'macvtap']:  # implies tap
            # destination is required, hard-code reasonable default if unset
            # nic.set_if_none('netdst', 'virbr0')
            # tapfd allocated/set in activate because requires system resources
            nic.set_if_none('queues', '1')
            ids = []
            for i in range(int(nic.queues)):
                ids.append(utils_misc.generate_random_id())
            nic.set_if_none('tapfd_ids', ids)

        elif nic.nettype == 'user':
            pass  # nothing to do
        else:  # unsupported nettype
            raise virt_vm.VMUnknownNetTypeError(self.name, nic_name,
                                                nic.nettype)
        return nic.netdev_id

    @error.context_aware
    def del_netdev(self, nic_index_or_name):
        """
        Remove netdev info. from nic on VM, does not deactivate.

        :param: nic_index_or_name: name or index number for existing NIC
        """
        nic = self.virtnet[nic_index_or_name]
        error.context("removing netdev info from nic %s from vm %s" % (
                      nic, self.name))
        for propertea in ['netdev_id', 'ifname', 'queues',
                          'tapfds', 'tapfd_ids', 'vectors']:
            if nic.has_key(propertea):
                del nic[propertea]

    def add_nic(self, **params):
        """
        Add new or setup existing NIC, optionally creating netdev if None

        :param params: Parameters to set
        :param nic_name: Name for existing or new device
        :param nic_model: Model name to emulate
        :param netdev_id: Existing qemu net device ID name, None to create new
        :param mac: Optional MAC address, None to randomly generate.
        """
        # returns existing or new nic object
        nic = super(VM, self).add_nic(**params)
        nic_index = self.virtnet.nic_name_index(nic.nic_name)
        nic.set_if_none('vlan', str(nic_index))
        nic.set_if_none('device_id', utils_misc.generate_random_id())
        nic.set_if_none('queues', '1')
        if not nic.has_key('netdev_id'):
            # virtnet items are lists that act like dicts
            nic.netdev_id = self.add_netdev(**dict(nic))
        nic.set_if_none('nic_model', params['nic_model'])
        nic.set_if_none('queues', params.get('queues', '1'))
        if params.get("enable_msix_vectors") == "yes":
            nic.set_if_none('vectors', 2 * int(nic.queues) + 2)
        return nic

    @error.context_aware
    def activate_netdev(self, nic_index_or_name):
        """
        Activate an inactive host-side networking device

        :raise: IndexError if nic doesn't exist
        :raise: VMUnknownNetTypeError: if nettype is unset/unsupported
        :raise: IOError if TAP device node cannot be opened
        :raise: VMAddNetDevError: if operation failed
        """
        nic = self.virtnet[nic_index_or_name]
        error.context("Activating netdev for %s based on %s" %
                      (self.name, nic))
        msg_sfx = ("nic %s on vm %s with attach_cmd " %
                   (self.virtnet[nic_index_or_name], self.name))

        attach_cmd = "netdev_add"
        if nic.nettype in ['bridge', 'macvtap']:
            error.context("Opening tap device node for %s " % nic.ifname,
                          logging.debug)
            if nic.nettype == "bridge":
                tun_tap_dev = "/dev/net/tun"
                python_tapfds = utils_net.open_tap(tun_tap_dev,
                                                   nic.ifname,
                                                   queues=nic.queues,
                                                   vnet_hdr=False)
            elif nic.nettype == "macvtap":
                macvtap_mode = self.params.get("macvtap_mode", "vepa")
                o_macvtap = utils_net.create_macvtap(nic.ifname, macvtap_mode,
                                                     nic.netdst, nic.mac)
                tun_tap_dev = o_macvtap.get_device()
                python_tapfds = utils_net.open_macvtap(o_macvtap, nic.queues)

            qemu_fds = "/proc/%s/fd" % self.get_pid()
            openfd_list = os.listdir(qemu_fds)
            for i in range(int(nic.queues)):
                error.context("Assigning tap %s to qemu by fd" %
                              nic.tapfd_ids[i], logging.info)
                self.monitor.getfd(int(python_tapfds.split(':')[i]),
                                   nic.tapfd_ids[i])
            n_openfd_list = os.listdir(qemu_fds)
            new_fds = list(set(n_openfd_list) - set(openfd_list))

            if not new_fds:
                err_msg = "Can't get the fd that qemu process opened!"
                raise virt_vm.VMAddNetDevError(err_msg)
            qemu_tapfds = [fd for fd in new_fds if os.readlink(
                           os.path.join(qemu_fds, fd)) == tun_tap_dev]
            if not qemu_tapfds or len(qemu_tapfds) != int(nic.queues):
                err_msg = "Can't get the tap fd in qemu process!"
                raise virt_vm.VMAddNetDevError(err_msg)
            nic.set_if_none("tapfds", ":".join(qemu_tapfds))

            if not self.devices:
                err_msg = "Can't add nic for VM which is not running."
                raise virt_vm.VMAddNetDevError(err_msg)
            if ((int(nic.queues)) > 1 and
                    ',fds=' in self.devices.get_help_text()):
                attach_cmd += " type=tap,id=%s,fds=%s" % (nic.device_id,
                                                          nic.tapfds)
            else:
                attach_cmd += " type=tap,id=%s,fd=%s" % (nic.device_id,
                                                         nic.tapfds)
            error.context("Raising interface for " + msg_sfx + attach_cmd,
                          logging.debug)
            utils_net.bring_up_ifname(nic.ifname)
            # assume this will puke if netdst unset
            if nic.netdst is not None and nic.nettype == "bridge":
                error.context("Raising bridge for " + msg_sfx + attach_cmd,
                              logging.debug)
                utils_net.add_to_bridge(nic.ifname, nic.netdst)
        elif nic.nettype == 'user':
            attach_cmd += " user,id=%s" % nic.device_id
        elif nic.nettype == 'none':
            attach_cmd += " none"
        else:  # unsupported nettype
            raise virt_vm.VMUnknownNetTypeError(self.name, nic_index_or_name,
                                                nic.nettype)
        if nic.has_key('netdev_extra_params') and nic.netdev_extra_params:
            attach_cmd += nic.netdev_extra_params
        error.context("Hotplugging " + msg_sfx + attach_cmd, logging.debug)

        if self.monitor.protocol == 'qmp':
            self.monitor.send_args_cmd(attach_cmd)
        else:
            self.monitor.send_args_cmd(attach_cmd, convert=False)

        network_info = self.monitor.info("network")
        if nic.device_id not in network_info:
            # Don't leave resources dangling
            self.deactivate_netdev(nic_index_or_name)
            raise virt_vm.VMAddNetDevError(("Failed to add netdev: %s for " %
                                            nic.device_id) + msg_sfx +
                                           attach_cmd)

    @error.context_aware
    def activate_nic(self, nic_index_or_name):
        """
        Activate an VM's inactive NIC device and verify state

        :param nic_index_or_name: name or index number for existing NIC
        """
        error.context("Retrieving info for NIC %s on VM %s" % (
                      nic_index_or_name, self.name))
        nic = self.virtnet[nic_index_or_name]
        device_add_cmd = "device_add"
        if nic.has_key('nic_model'):
            device_add_cmd += ' driver=%s' % nic.nic_model
        device_add_cmd += ",netdev=%s" % nic.device_id
        if nic.has_key('mac'):
            device_add_cmd += ",mac=%s" % nic.mac
        device_add_cmd += ",id=%s" % nic.nic_name
        if nic['nic_model'] == 'virtio-net-pci':
            if int(nic['queues']) > 1:
                device_add_cmd += ",mq=on"
            if nic.has_key('vectors'):
                device_add_cmd += ",vectors=%s" % nic.vectors
        device_add_cmd += nic.get('nic_extra_params', '')
        if nic.has_key('romfile'):
            device_add_cmd += ",romfile=%s" % nic.romfile
        error.context("Activating nic on VM %s with monitor command %s" % (
            self.name, device_add_cmd))

        if self.monitor.protocol == 'qmp':
            self.monitor.send_args_cmd(device_add_cmd)
        else:
            self.monitor.send_args_cmd(device_add_cmd, convert=False)

        error.context("Verifying nic %s shows in qtree" % nic.nic_name)
        qtree = self.monitor.info("qtree")
        if nic.nic_name not in qtree:
            logging.error(qtree)
            raise virt_vm.VMAddNicError("Device %s was not plugged into qdev"
                                        "tree" % nic.nic_name)

    @error.context_aware
    def deactivate_nic(self, nic_index_or_name, wait=20):
        """
        Reverses what activate_nic did

        :param nic_index_or_name: name or index number for existing NIC
        :param wait: Time test will wait for the guest to unplug the device
        """
        nic = self.virtnet[nic_index_or_name]
        error.context("Removing nic %s from VM %s" % (nic_index_or_name,
                                                      self.name))
        nic_del_cmd = "device_del id=%s" % (nic.nic_name)

        if self.monitor.protocol == 'qmp':
            self.monitor.send_args_cmd(nic_del_cmd)
        else:
            self.monitor.send_args_cmd(nic_del_cmd, convert=True)

        if wait:
            logging.info("waiting for the guest to finish the unplug")
            nic_eigenvalue = r'dev:\s+%s,\s+id\s+"%s"' % (nic.nic_model,
                                                          nic.nic_name)
            if not utils_misc.wait_for(lambda: nic_eigenvalue not in
                                       self.monitor.info("qtree"),
                                       wait, 5, 1):
                raise virt_vm.VMDelNicError("Device is not unplugged by "
                                            "guest, please check whether the "
                                            "hotplug module was loaded in "
                                            "guest")

    @error.context_aware
    def deactivate_netdev(self, nic_index_or_name):
        """
        Reverses what activate_netdev() did

        :param: nic_index_or_name: name or index number for existing NIC
        """
        # FIXME: Need to down interface & remove from bridge????
        nic = self.virtnet[nic_index_or_name]
        netdev_id = nic.device_id
        error.context("removing netdev id %s from vm %s" %
                      (netdev_id, self.name))
        nic_del_cmd = "netdev_del id=%s" % netdev_id

        if self.monitor.protocol == 'qmp':
            self.monitor.send_args_cmd(nic_del_cmd)
        else:
            self.monitor.send_args_cmd(nic_del_cmd, convert=True)

        network_info = self.monitor.info("network")
        netdev_eigenvalue = r'netdev\s+=\s+%s' % netdev_id
        if netdev_eigenvalue in network_info:
            raise virt_vm.VMDelNetDevError("Fail to remove netdev %s" %
                                           netdev_id)
        if nic.nettype == 'macvtap':
            tap = utils_net.Macvtap(nic.ifname)
            tap.delete()

    @error.context_aware
    def del_nic(self, nic_index_or_name):
        """
        Undefine nic prameters, reverses what add_nic did.

        :param nic_index_or_name: name or index number for existing NIC
        :param wait: Time test will wait for the guest to unplug the device
        """
        super(VM, self).del_nic(nic_index_or_name)

    @error.context_aware
    def send_fd(self, fd, fd_name="migfd"):
        """
        Send file descriptor over unix socket to VM.

        :param fd: File descriptor.
        :param fd_name: File descriptor identificator in VM.
        """
        error.context("Send fd %d like %s to VM %s" % (fd, fd_name, self.name))

        logging.debug("Send file descriptor %s to source VM.", fd_name)
        if self.monitor.protocol == 'human':
            self.monitor.cmd("getfd %s" % (fd_name), fd=fd)
        elif self.monitor.protocol == 'qmp':
            self.monitor.cmd("getfd", args={'fdname': fd_name}, fd=fd)
        error.context()

    def mig_finished(self):
        ret = True
        if (self.params["display"] == "spice" and
                self.get_spice_var("spice_seamless_migration") == "on"):
            s = self.monitor.info("spice")
            if isinstance(s, str):
                ret = "migrated: true" in s
            else:
                ret = s.get("migrated") == "true"
        o = self.monitor.info("migrate")
        if isinstance(o, str):
            return ret and ("status: active" not in o)
        else:
            return ret and (o.get("status") != "active")

    def mig_succeeded(self):
        o = self.monitor.info("migrate")
        if isinstance(o, str):
            return "status: completed" in o
        else:
            return o.get("status") == "completed"

    def mig_failed(self):
        o = self.monitor.info("migrate")
        if isinstance(o, str):
            return "status: failed" in o
        else:
            return o.get("status") == "failed"

    def mig_cancelled(self):
        if self.mig_succeeded():
            raise virt_vm.VMMigrateCancelError(
                "Migration completed successfully")
        elif self.mig_failed():
            raise virt_vm.VMMigrateFailedError("Migration failed")
        o = self.monitor.info("migrate")
        if isinstance(o, str):
            return ("Migration status: cancelled" in o or
                    "Migration status: canceled" in o)
        else:
            return (o.get("status") == "cancelled" or
                    o.get("status") == "canceled")

    def wait_for_migration(self, timeout):
        if not utils_misc.wait_for(self.mig_finished, timeout, 2, 2,
                                   "Waiting for migration to complete"):
            raise virt_vm.VMMigrateTimeoutError("Timeout expired while waiting"
                                                " for migration to finish")

    @error.context_aware
    def migrate(self, timeout=virt_vm.BaseVM.MIGRATE_TIMEOUT, protocol="tcp",
                cancel_delay=None, offline=False, stable_check=False,
                clean=True, save_path="/tmp", dest_host="localhost",
                remote_port=None, not_wait_for_migration=False,
                fd_src=None, fd_dst=None, migration_exec_cmd_src=None,
                migration_exec_cmd_dst=None, env=None):
        """
        Migrate the VM.

        If the migration is local, the VM object's state is switched with that
        of the destination VM.  Otherwise, the state is switched with that of
        a dead VM (returned by self.clone()).

        :param timeout: Time to wait for migration to complete.
        :param protocol: Migration protocol (as defined in MIGRATION_PROTOS)
        :param cancel_delay: If provided, specifies a time duration after which
                migration will be canceled.  Used for testing migrate_cancel.
        :param offline: If True, pause the source VM before migration.
        :param stable_check: If True, compare the VM's state after migration to
                its state before migration and raise an exception if they
                differ.
        :param clean: If True, delete the saved state files (relevant only if
                stable_check is also True).
        :param save_path: The path for state files.
        :param dest_host: Destination host (defaults to 'localhost').
        :param remote_port: Port to use for remote migration.
        :param not_wait_for_migration: If True migration start but not wait till
                the end of migration.
        :param fd_s: File descriptor for migration to which source
                     VM write data. Descriptor is closed during the migration.
        :param fd_d: File descriptor for migration from which destination
                     VM read data.
        :param migration_exec_cmd_src: Command to embed in '-incoming "exec: "'
                (e.g. 'exec:gzip -c > filename') if migration_mode is 'exec'
                default to listening on a random TCP port
        :param migration_exec_cmd_dst: Command to embed in '-incoming "exec: "'
                (e.g. 'gzip -c -d filename') if migration_mode is 'exec'
                default to listening on a random TCP port
        :param env: Dictionary with test environment
        """
        if protocol not in self.MIGRATION_PROTOS:
            raise virt_vm.VMMigrateProtoUnknownError(protocol)

        error.base_context("migrating '%s'" % self.name)

        local = dest_host == "localhost"
        mig_fd_name = None

        if protocol == "fd":
            # Check if descriptors aren't None for local migration.
            if local and (fd_dst is None or fd_src is None):
                (fd_dst, fd_src) = os.pipe()

            mig_fd_name = "migfd_%d_%d" % (fd_src, time.time())
            self.send_fd(fd_src, mig_fd_name)
            os.close(fd_src)

        clone = self.clone()
        if self.params.get('qemu_dst_binary', None) is not None:
            clone.params['qemu_binary'] = utils_misc.get_qemu_dst_binary(self.params)
        if env:
            env.register_vm("%s_clone" % clone.name, clone)
        if (local and not (migration_exec_cmd_src
                           and "gzip" in migration_exec_cmd_src)):
            error.context("creating destination VM")
            if stable_check:
                # Pause the dest vm after creation
                extra_params = clone.params.get("extra_params", "") + " -S"
                clone.params["extra_params"] = extra_params

            clone.create(migration_mode=protocol, mac_source=self,
                         migration_fd=fd_dst,
                         migration_exec_cmd=migration_exec_cmd_dst)
            if fd_dst:
                os.close(fd_dst)
            error.context()

        try:
            if (self.params["display"] == "spice" and local and
                not (protocol == "exec" and
                     (migration_exec_cmd_src and "gzip" in migration_exec_cmd_src))):
                host_ip = utils_net.get_host_ip_address(self.params)
                dest_port = clone.spice_options.get('spice_port', '')
                if self.params.get("spice_ssl") == "yes":
                    dest_tls_port = clone.spice_options.get("spice_tls_port",
                                                            "")
                    cert_s = clone.spice_options.get("spice_x509_server_subj",
                                                     "")
                    cert_subj = "%s" % cert_s[1:]
                    cert_subj += host_ip
                    cert_subj = "\"%s\"" % cert_subj
                else:
                    dest_tls_port = ""
                    cert_subj = ""
                logging.debug("Informing migration to spice client")
                commands = ["__com.redhat_spice_migrate_info",
                            "spice_migrate_info",
                            "client_migrate_info"]

                cmdline = ""
                for command in commands:
                    try:
                        self.monitor.verify_supported_cmd(command)
                    except qemu_monitor.MonitorNotSupportedCmdError:
                        continue
                    # spice_migrate_info requires host_ip, dest_port
                    # client_migrate_info also requires protocol
                    cmdline = "%s hostname=%s" % (command, host_ip)
                    if command == "client_migrate_info":
                        cmdline += " ,protocol=%s" % self.params['display']
                    if dest_port:
                        cmdline += ",port=%s" % dest_port
                    if dest_tls_port:
                        cmdline += ",tls-port=%s" % dest_tls_port
                    if cert_subj:
                        cmdline += ",cert-subject=%s" % cert_subj
                    break
                if cmdline:
                    self.monitor.send_args_cmd(cmdline)

            if protocol in ["tcp", "rdma", "x-rdma"]:
                if local:
                    uri = protocol + ":localhost:%d" % clone.migration_port
                else:
                    uri = protocol + ":%s:%d" % (dest_host, remote_port)
            elif protocol == "unix":
                uri = "unix:%s" % clone.migration_file
            elif protocol == "exec":
                if local:
                    if not migration_exec_cmd_src:
                        uri = '"exec:nc localhost %s"' % clone.migration_port
                    else:
                        uri = '"exec:%s"' % (migration_exec_cmd_src)
                else:
                    uri = '"exec:%s"' % (migration_exec_cmd_src)
            elif protocol == "fd":
                uri = "fd:%s" % mig_fd_name

            if offline is True:
                self.monitor.cmd("stop")

            logging.info("Migrating to %s", uri)
            self.monitor.migrate(uri)
            if not_wait_for_migration:
                return clone

            if cancel_delay:
                time.sleep(cancel_delay)
                self.monitor.cmd("migrate_cancel")
                if not utils_misc.wait_for(self.mig_cancelled, 60, 2, 2,
                                           "Waiting for migration "
                                           "cancellation"):
                    raise virt_vm.VMMigrateCancelError(
                        "Cannot cancel migration")
                return

            self.wait_for_migration(timeout)

            if (local and (migration_exec_cmd_src
                           and "gzip" in migration_exec_cmd_src)):
                error.context("creating destination VM")
                if stable_check:
                    # Pause the dest vm after creation
                    extra_params = clone.params.get("extra_params", "") + " -S"
                    clone.params["extra_params"] = extra_params
                clone.create(migration_mode=protocol, mac_source=self,
                             migration_fd=fd_dst,
                             migration_exec_cmd=migration_exec_cmd_dst)

            self.verify_alive()

            # Report migration status
            if self.mig_succeeded():
                logging.info("Migration completed successfully")
            elif self.mig_failed():
                raise virt_vm.VMMigrateFailedError("Migration failed")
            else:
                raise virt_vm.VMMigrateFailedError("Migration ended with "
                                                   "unknown status")

            # Switch self <-> clone
            temp = self.clone(copy_state=True)
            self.__dict__ = clone.__dict__
            clone = temp

            # From now on, clone is the source VM that will soon be destroyed
            # and self is the destination VM that will remain alive.  If this
            # is remote migration, self is a dead VM object.

            error.context("after migration")
            if local:
                time.sleep(1)
                self.verify_kernel_crash()
                self.verify_alive()

            if local and stable_check:
                try:
                    save1 = os.path.join(save_path, "src-" + clone.instance)
                    save2 = os.path.join(save_path, "dst-" + self.instance)
                    clone.save_to_file(save1)
                    self.save_to_file(save2)
                    # Fail if we see deltas
                    md5_save1 = utils.hash_file(save1)
                    md5_save2 = utils.hash_file(save2)
                    if md5_save1 != md5_save2:
                        raise virt_vm.VMMigrateStateMismatchError()
                finally:
                    if clean:
                        if os.path.isfile(save1):
                            os.remove(save1)
                        if os.path.isfile(save2):
                            os.remove(save2)

        finally:
            # If we're doing remote migration and it's completed successfully,
            # self points to a dead VM object
            if not not_wait_for_migration:
                if self.is_alive():
                    self.monitor.cmd("cont")
                clone.destroy(gracefully=False)
                if env:
                    env.unregister_vm("%s_clone" % self.name)

    @error.context_aware
    def reboot(self, session=None, method="shell", nic_index=0,
               timeout=virt_vm.BaseVM.REBOOT_TIMEOUT):
        """
        Reboot the VM and wait for it to come back up by trying to log in until
        timeout expires.

        :param session: A shell session object or None.
        :param method: Reboot method.  Can be "shell" (send a shell reboot
                command) or "system_reset" (send a system_reset monitor command).
        :param nic_index: Index of NIC to access in the VM, when logging in
                after rebooting.
        :param timeout: Time to wait for login to succeed (after rebooting).
        :return: A new shell session object.
        """
        error.base_context("rebooting '%s'" % self.name, logging.info)
        error.context("before reboot")
        error.context()

        if method == "shell":
            session = session or self.login()
            session.sendline(self.params.get("reboot_command"))
            error.context("waiting for guest to go down", logging.info)
            if not utils_misc.wait_for(
                lambda:
                    not session.is_responsive(
                        timeout=self.CLOSE_SESSION_TIMEOUT),
                    timeout / 2, 0, 1):
                raise virt_vm.VMRebootError("Guest refuses to go down")
            session.close()

        elif method == "system_reset":
            # Clear the event list of all QMP monitors
            qmp_monitors = [m for m in self.monitors if m.protocol == "qmp"]
            for m in qmp_monitors:
                m.clear_events()
            # Send a system_reset monitor command
            self.monitor.cmd("system_reset")
            # Look for RESET QMP events
            time.sleep(1)
            for m in qmp_monitors:
                if m.get_event("RESET"):
                    logging.info("RESET QMP event received")
                else:
                    raise virt_vm.VMRebootError("RESET QMP event not received "
                                                "after system_reset "
                                                "(monitor '%s')" % m.name)
        else:
            raise virt_vm.VMRebootError("Unknown reboot method: %s" % method)

        if self.params.get("mac_changeable") == "yes":
            utils_net.update_mac_ip_address(self, self.params)

        error.context("logging in after reboot", logging.info)
        return self.wait_for_login(nic_index, timeout=timeout)

    def send_key(self, keystr):
        """
        Send a key event to the VM.

        :param keystr: A key event string (e.g. "ctrl-alt-delete")
        """
        # For compatibility with versions of QEMU that do not recognize all
        # key names: replace keyname with the hex value from the dict, which
        # QEMU will definitely accept
        key_mapping = {"semicolon": "0x27",
                       "comma": "0x33",
                       "dot": "0x34",
                       "slash": "0x35"}
        for key, value in key_mapping.items():
            keystr = keystr.replace(key, value)
        self.monitor.sendkey(keystr)
        time.sleep(0.2)

    # should this really be expected from VMs of all hypervisor types?
    def screendump(self, filename, debug=True):
        try:
            if self.monitor:
                self.monitor.screendump(filename=filename, debug=debug)
        except qemu_monitor.MonitorError, e:
            logging.warn(e)

    def save_to_file(self, path):
        """
        Override BaseVM save_to_file method
        """
        self.verify_status('paused')  # Throws exception if not
        # Set high speed 1TB/S
        self.monitor.migrate_set_speed(str(2 << 39))
        self.monitor.migrate_set_downtime(self.MIGRATE_TIMEOUT)
        logging.debug("Saving VM %s to %s" % (self.name, path))
        # Can only check status if background migration
        self.monitor.migrate("exec:cat>%s" % path, wait=False)
        utils_misc.wait_for(
            # no monitor.migrate-status method
            lambda:
            re.search("(status.*completed)",
                      str(self.monitor.info("migrate")), re.M),
            self.MIGRATE_TIMEOUT, 2, 2,
            "Waiting for save to %s to complete" % path)
        # Restore the speed and downtime to default values
        self.monitor.migrate_set_speed(str(32 << 20))
        self.monitor.migrate_set_downtime(0.03)
        # Base class defines VM must be off after a save
        self.monitor.cmd("system_reset")
        self.verify_status('paused')  # Throws exception if not

    def restore_from_file(self, path):
        """
        Override BaseVM restore_from_file method
        """
        self.verify_status('paused')  # Throws exception if not
        logging.debug("Restoring VM %s from %s" % (self.name, path))
        # Rely on create() in incoming migration mode to do the 'right thing'
        self.create(name=self.name, params=self.params, root_dir=self.root_dir,
                    timeout=self.MIGRATE_TIMEOUT, migration_mode="exec",
                    migration_exec_cmd="cat " + path, mac_source=self)
        self.verify_status('running')  # Throws exception if not

    def savevm(self, tag_name):
        """
        Override BaseVM savevm method
        """
        self.verify_status('paused')  # Throws exception if not
        logging.debug("Saving VM %s to %s" % (self.name, tag_name))
        self.monitor.send_args_cmd("savevm id=%s" % tag_name)
        self.monitor.cmd("system_reset")
        self.verify_status('paused')  # Throws exception if not

    def loadvm(self, tag_name):
        """
        Override BaseVM loadvm method
        """
        self.verify_status('paused')  # Throws exception if not
        logging.debug("Loading VM %s from %s" % (self.name, tag_name))
        self.monitor.send_args_cmd("loadvm id=%s" % tag_name)
        self.verify_status('paused')  # Throws exception if not

    def pause(self):
        """
        Pause the VM operation.
        """
        self.monitor.cmd("stop")

    def resume(self):
        """
        Resume the VM operation in case it's stopped.
        """
        self.monitor.cmd("cont")

    def set_link(self, netdev_name, up):
        """
        Set link up/down.

        :param name: Link name
        :param up: Bool value, True=set up this link, False=Set down this link
        """
        self.monitor.set_link(netdev_name, up)

    def get_block_old(self, blocks_info, p_dict={}):
        """
        Get specified block device from monitor's info block command.
        The block device is defined by parameter in p_dict.

        :param p_dict: Dictionary that contains parameters and its value used
                       to define specified block device.

        :param blocks_info: the results of monitor command 'info block'

        :return: Matched block device name, None when not find any device.
        """
        if isinstance(blocks_info, str):
            for block in blocks_info.splitlines():
                match = True
                for key, value in p_dict.iteritems():
                    if value is True:
                        check_str = "%s=1" % key
                    elif value is False:
                        check_str = "%s=0" % key
                    else:
                        check_str = "%s=%s" % (key, value)
                    if check_str not in block:
                        match = False
                        break
                if match:
                    return block.split(":")[0]
        else:
            for block in blocks_info:
                match = True
                for key, value in p_dict.iteritems():
                    if isinstance(value, bool):
                        check_str = "u'%s': %s" % (key, value)
                    else:
                        check_str = "u'%s': u'%s'" % (key, value)
                    if check_str not in str(block):
                        match = False
                        break
                if match:
                    return block['device']
        return None

    def process_info_block(self, blocks_info):
        """
        Process the info block, so that can deal with the new and old
        qemu format.

        :param blocks_info: the output of qemu command
                            'info block'
        """
        block_list = []
        block_entry = []
        for block in blocks_info.splitlines():
            if block:
                block_entry.append(block.strip())
            else:
                block_list.append(' '.join(block_entry))
                block_entry = []
        # don't forget the last one
        block_list.append(' '.join(block_entry))
        return block_list

    def get_block(self, p_dict={}):
        """
        Get specified block device from monitor's info block command.
        The block device is defined by parameter in p_dict.

        :param p_dict: Dictionary that contains parameters and its value used
                       to define specified block device.

        :return: Matched block device name, None when not find any device.
        """
        blocks_info = self.monitor.info("block")
        block = self.get_block_old(blocks_info, p_dict)
        if block:
            return block

        block_list = self.process_info_block(blocks_info)
        for block in block_list:
            for key, value in p_dict.iteritems():
                    # for new qemu we just deal with key = [removable,
                    # file,backing_file], for other types key, we should
                    # fixup later
                logging.info("block = %s" % block)
                if key == 'removable':
                    if value is False:
                        if 'Removable device' not in block:
                            return block.split(":")[0]
                    elif value is True:
                        if 'Removable device' in block:
                            return block.split(":")[0]
                # file in key means both file and backing_file
                if ('file' in key) and (value in block):
                    return block.split(":")[0]

        return None

    def check_block_locked(self, value):
        """
        Check whether specified block device is locked or not.
        Return True, if device is locked, else False.

        :param vm: VM object
        :param value: Parameter that can specify block device.
                      Can be any possible identification of a device,
                      Such as device name/image file name/...

        :return: True if device is locked, False if device is unlocked.
        """
        assert value, "Device identification not specified"

        blocks_info = self.monitor.info("block")

        assert value in str(blocks_info), \
            "Device %s not listed in monitor's output" % value

        if isinstance(blocks_info, str):
            lock_str = "locked=1"
            lock_str_new = "locked"
            no_lock_str = "not locked"
            for block in blocks_info.splitlines():
                if (value in block) and (lock_str in block):
                    return True
            # deal with new qemu
            block_list = self.process_info_block(blocks_info)
            for block_new in block_list:
                if (value in block_new) and ("Removable device" in block_new):
                    if no_lock_str in block_new:
                        return False
                    elif lock_str_new in block_new:
                        return True
        else:
            for block in blocks_info:
                if value in str(block):
                    return block['locked']
        return False

    def live_snapshot(self, base_file, snapshot_file,
                      snapshot_format="qcow2"):
        """
        Take a live disk snapshot.

        :param base_file: base file name
        :param snapshot_file: snapshot file name
        :param snapshot_format: snapshot file format

        :return: File name of disk snapshot.
        """
        device = self.get_block({"file": base_file})

        output = self.monitor.live_snapshot(device, snapshot_file,
                                            snapshot_format)
        logging.debug(output)
        device = self.get_block({"file": snapshot_file})
        if device:
            current_file = device
        else:
            current_file = None

        return current_file

    def block_stream(self, device, speed, base=None, correct=True):
        """
        start to stream block device, aka merge snapshot;

        :param device: device ID;
        :param speed: limited speed, default unit B/s;
        :param base: base file;
        :param correct: auto correct cmd, correct by default
        """
        cmd = self.params.get("block_stream_cmd", "block-stream")
        return self.monitor.block_stream(device, speed, base,
                                         cmd, correct=correct)

    def block_mirror(self, device, target, speed, sync,
                     format, mode="absolute-paths", correct=True):
        """
        Mirror block device to target file;

        :param device: device ID
        :param target: destination image file name;
        :param speed: max limited speed, default unit is B/s;
        :param sync: what parts of the disk image should be copied to the
                     destination;
        :param mode: new image open mode
        :param format: target image format
        :param correct: auto correct cmd, correct by default
        """
        cmd = self.params.get("block_mirror_cmd", "drive-mirror")
        return self.monitor.block_mirror(device, target, speed, sync,
                                         format, mode, cmd, correct=correct)

    def block_reopen(self, device, new_image, format="qcow2", correct=True):
        """
        Reopen a new image, no need to do this step in rhel7 host

        :param device: device ID
        :param new_image: new image filename
        :param format: new image format
        :param correct: auto correct cmd, correct by default
        """
        cmd = self.params.get("block_reopen_cmd", "block-job-complete")
        return self.monitor.block_reopen(device, new_image,
                                         format, cmd, correct=correct)

    def cancel_block_job(self, device, correct=True):
        """
        cancel active job on the image_file

        :param device: device ID
        :param correct: auto correct cmd, correct by default
        """
        cmd = self.params.get("block_job_cancel_cmd", "block-job-cancel")
        return self.monitor.cancel_block_job(device, cmd, correct=correct)

    def set_job_speed(self, device, speed="0", correct=True):
        """
        set max speed of block job;

        :param device: device ID
        :param speed: max speed of block job
        :param correct: auto correct cmd, correct by default
        """
        cmd = self.params.get("set_block_job_speed", "block-job-set-speed")
        return self.monitor.set_block_job_speed(device, speed,
                                                cmd, correct=correct)

    def get_job_status(self, device):
        """
        get block job info;

        :param device: device ID
        """
        return self.monitor.query_block_job(device)

    def eject_cdrom(self, device, force=False):
        """
        Eject cdrom and open door of the CDROM;

        :param device: device ID;
        :param force: force eject or not;
        """
        return self.monitor.eject_cdrom(device, force)

    def change_media(self, device, target):
        """
        Change media of cdrom;

        :param device: Device ID;
        :param target: new media file;
        """
        return self.monitor.change_media(device, target)
