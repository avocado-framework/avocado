"""
Assemble a QEMU command line from parameters.
"""

import commands
import logging
import os
import re

from avocado.core import data_dir
from avocado.utils import process
from avocado.utils import path
from avocado.utils import network
from avocado.utils import memory
from avocado.utils import crypto

from avocado.virt import exceptions
from avocado.virt.qemu import path as q_path
from avocado.virt.qemu import monitor
from avocado.virt.qemu.devices import qdevices
from avocado.virt.qemu.devices import qcontainer

log = logging.getLogger("avocado.test")


def has_option(option, qemu_path="/usr/bin/qemu-kvm"):
    """
    Helper function for command line option wrappers

    :param option: Option need check.
    :param qemu_path: Path for qemu-kvm.
    """
    hlp = commands.getoutput("%s -help" % qemu_path)
    return bool(re.search(r"^-%s(\s|$)" % option, hlp, re.MULTILINE))


class QemuCmdLine(object):

    def __init__(self, params, vm):
        self.params = params
        self.devices = None
        self.vm = vm
        self.qemu_binary = vm.qemu_binary
        # Start constructing devices representation
        self.devices = qcontainer.DevContainer(self.qemu_binary, self.name,
                                               self.params.get('strict_mode'),
                                               self.params.get('workaround_qemu_qmp_crash'),
                                               self.params.get('allow_hotplugged_vm'))

    def add_flag(self, option, value, option_type=None, first=False):
        """
        Add flag to the QEMU cmdline.
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
            # format of option.
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

    def add_name(self, name):
        return " -name '%s'" % name

    def process_sandbox(self, action):
        if action == "add":
            if self.devices.has_option("sandbox"):
                return " -sandbox on "
        elif action == "rem":
            if self.devices.has_option("sandbox"):
                return " -sandbox off "

    def add_human_monitor(self, monitor_name, filename):
        if not self.devices.has_option("chardev"):
            return " -monitor unix:'%s',server,nowait" % filename

        monitor_id = "hmp_id_%s" % monitor_name
        cmd = " -chardev socket"
        cmd += self.add_flag("id", monitor_id)
        cmd += self.add_flag("path", filename)
        cmd += self.add_flag("server", "NO_EQUAL_STRING")
        cmd += self.add_flag("nowait", "NO_EQUAL_STRING")
        cmd += " -mon chardev=%s" % monitor_id
        cmd += self.add_flag("mode", "readline")
        return cmd

    def add_qmp_monitor(self, monitor_name, filename):
        if not self.devices.has_option("qmp"):
            logging.warn("Falling back to human monitor since qmp is "
                         "unsupported")
            return self.add_human_monitor(monitor_name, filename)

        if not self.devices.has_option("chardev"):
            return " -qmp unix:'%s',server,nowait" % filename

        monitor_id = "qmp_id_%s" % monitor_name
        cmd = " -chardev socket"
        cmd += self.add_flag("id", monitor_id)
        cmd += self.add_flag("path", filename)
        cmd += self.add_flag("server", "NO_EQUAL_STRING")
        cmd += self.add_flag("nowait", "NO_EQUAL_STRING")
        cmd += " -mon chardev=%s" % monitor_id
        cmd += self.add_flag("mode", "control")
        return cmd

    def add_serial(self, name, filename):
        if not self.devices.has_option("chardev"):
            return " -serial unix:'%s',server,nowait" % filename

        serial_id = "serial_id_%s" % name
        cmd = " -chardev socket"
        cmd += self.add_flag("id", serial_id)
        cmd += self.add_flag("path", filename)
        cmd += self.add_flag("server", "NO_EQUAL_STRING")
        cmd += self.add_flag("nowait", "NO_EQUAL_STRING")
        cmd += " -device isa-serial"
        cmd += self.add_flag("chardev", serial_id)
        return cmd

    def add_virtio_port(self, name, bus, filename, porttype, chardev,
                        name_prefix=None, index=None, extra_params=""):
        """
        Appends virtio_serialport or virtio_console device to cmdline.

        :param help: qemu -h output
        :param name: Name of the port
        :param bus: Which virtio-serial-pci device use
        :param filename: Path to chardev filename
        :param porttype: Type of the port (serialport, console)
        :param chardev: Which chardev to use (socket, spicevmc)
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
        cmd += self.add_flag("bus", bus)
        # Space sepparated chardev params
        _params = ""
        for parm in extra_params.split():
            _params += ',' + parm
        cmd += _params
        return cmd

    def add_log_seabios(self):
        if not self.devices.has_device("isa-debugcon"):
            return ""

        default_id = "seabioslog_id_%s" % self.instance
        filename = "/tmp/seabios-%s" % self.instance
        self.logs["seabios"] = filename
        cmd = " -chardev socket"
        cmd += self.add_flag("id", default_id)
        cmd += self.add_flag("path", filename)
        cmd += self.add_flag("server", "NO_EQUAL_STRING")
        cmd += self.add_flag("nowait", "NO_EQUAL_STRING")
        cmd += " -device isa-debugcon"
        cmd += self.add_flag("chardev", default_id)
        cmd += self.add_flag("iobase", "0x402")
        return cmd

    def add_log_anaconda(self, pci_bus='pci.0'):
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
        self.devices.insert(dev)
        dev = qdevices.QDevice('virtio-serial-pci', parent_bus=pci_bus)
        dev.set_param("id", vioser_id)
        self.devices.insert(dev)
        dev = qdevices.QDevice('virtserialport')
        dev.set_param("bus", "%s.0" % vioser_id)
        dev.set_param("chardev", chardev_id)
        dev.set_param("name", "org.fedoraproject.anaconda.log.0")
        self.devices.insert(dev)

    def add_mem(self, mem):
        return " -m %s" % mem

    def add_smp(self):
        smp_str = " -smp %d" % self.cpuinfo.smp
        smp_pattern = "smp .*n\[,maxcpus=cpus\].*"
        if self.devices.has_option(smp_pattern):
            smp_str += ",maxcpus=%d" % self.cpuinfo.maxcpus
        smp_str += ",cores=%d" % self.cpuinfo.cores
        smp_str += ",threads=%d" % self.cpuinfo.threads
        smp_str += ",sockets=%d" % self.cpuinfo.sockets
        return smp_str

    def add_nic(self, vlan, model=None, mac=None, device_id=None,
                netdev_id=None, nic_extra_params=None, pci_addr=None,
                bootindex=None, queues=1, vectors=None, pci_bus='pci.0'):
        if model == 'none':
            return
        if self.devices.has_option("device"):
            if not model:
                model = "rtl8139"
            elif model == "virtio":
                model = "virtio-net-pci"
            dev = qdevices.QDevice(model)
            dev.set_param('mac', mac, dynamic=True)
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
        if self.devices.has_option("netdev"):
            dev.set_param('netdev', netdev_id)
        else:
            dev.set_param('vlan', vlan)
        self.devices.insert(dev)

    def add_net(self, vlan, nettype, ifname=None, tftp=None,
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

        if self.devices.has_option("netdev"):
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
                            'vhostfds=' in self.devices.get_help_text()):
                        cmd += ",vhostfds=%(vhostfds)s"
                        cmd_nd += ",vhostfds=DYN"
                    else:
                        txt = ""
                        if int(queues) > 1:
                            txt = "qemu do not support vhost multiqueue,"
                            txt += " Fall back to single queue."
                        if 'vhostfd=' in self.devices.get_help_text():
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
                        ',fds=' in self.devices.get_help_text()):
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
            if tftp and "[,tftp=" in self.devices.get_help_text():
                cmd += ",tftp='%s'" % tftp
                cmd_nd = cmd
            if bootfile and "[,bootfile=" in self.devices.get_help_text():
                cmd += ",bootfile='%s'" % bootfile
                cmd_nd = cmd
            if "[,hostfwd=" in self.devices.get_help_text():
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

    def add_floppy(self, filename, index):
        cmd_list = [" -fda '%s'", " -fdb '%s'"]
        return cmd_list[index] % filename

    def add_tftp(self, filename):
        # If the new syntax is supported, don't add -tftp
        if "[,tftp=" in self.devices.get_help_text():
            return ""
        else:
            return " -tftp '%s'" % filename

    def add_bootp(self, filename):
        # If the new syntax is supported, don't add -bootp
        if "[,bootfile=" in self.devices.get_help_text():
            return ""
        else:
            return " -bootp '%s'" % filename

    def add_tcp_redir(self, host_port, guest_port):
        # If the new syntax is supported, don't add -redir
        if "[,hostfwd=" in self.devices.get_help_text():
            return ""
        else:
            return " -redir tcp:%s::%s" % (host_port, guest_port)

    def add_vnc(self, vnc_port, vnc_password='no', extra_params=None):
        vnc_cmd = " -vnc :%d" % (vnc_port - 5900)
        if vnc_password == "yes":
            vnc_cmd += ",password"
        if extra_params:
            vnc_cmd += ",%s" % extra_params
        return vnc_cmd

    def add_sdl(self):
        if self.devices.has_option("sdl"):
            return " -sdl"
        else:
            return ""

    def add_nographic(self):
        return " -nographic"

    def add_uuid(self, uuid):
        return " -uuid '%s'" % uuid

    def add_pcidevice(self, host, params, device_driver="pci-assign",
                      pci_bus='pci.0'):
        if self.devices.has_device(device_driver):
            dev = qdevices.QDevice(device_driver, parent_bus=pci_bus)
        else:
            dev = qdevices.QCustomDevice('pcidevice', parent_bus=pci_bus)
        help_cmd = "%s -device %s,\\? 2>&1" % (self.qemu_binary, device_driver)
        pcidevice_help = process.system_output(help_cmd)
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
        self.devices.insert(dev)

    def add_spice_rhel5(self, spice_params, port_range=(3100, 3199)):
        """
        processes spice parameters on rhel5 host.

        :param spice_options - dict with spice keys/values
        :param port_range - tuple with port range, default: (3000, 3199)
        """

        if self.devices.has_option("spice"):
            cmd = " -spice"
        else:
            return ""
        spice_help = ""
        if self.devices.has_option("spice-help"):
            spice_help = commands.getoutput("%s -device \\?" % self.qemu_binary)
        s_port = str(network.find_free_port(*port_range))
        self.spice_options['spice_port'] = s_port
        cmd += " port=%s" % s_port
        for param in spice_params.split():
            value = self.params.get(param)
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
        if self.devices.has_option("qxl"):
            qxl_dev_nr = self.params.get("qxl_dev_nr", 1)
            cmd += " -qxl %s" % qxl_dev_nr
        return cmd

    def add_spice(self, port_range=(3000, 3199),
                  tls_port_range=(3200, 3399)):
        """
        processes spice parameters

        :param port_range: tuple with port range, default: (3000, 3199)
        :param tls_port_range: tuple with tls port range,
                               default: (3200, 3399)
        """
        spice_opts = []
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

        s_port = str(network.find_free_port(*port_range))
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
            host_ip = network.get_host_ip_address(self.params)
            self.spice_options['listening_addr'] = "ipv4"
            spice_opts.append("addr=%s" % host_ip)
        elif optget("listening_addr") == "ipv6":
            host_ip = network.get_host_ip_address(self.params)
            host_ip_ipv6 = network.convert_ipv4_to_ipv6(host_ip)
            self.spice_options['listening_addr'] = "ipv6"
            spice_opts.append("addr=%s" % host_ip_ipv6)

        set_yes_no_value(
            "disable_copy_paste", yes_value="disable-copy-paste")
        set_value("addr=%s", "spice_addr")

        if optget("spice_ssl") == "yes":
            # SSL only part
            t_port = str(network.find_free_port(*tls_port_range))
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
                    s_subj += network.get_host_ip_address(self.params)
                passwd = optget("spice_x509_key_password")
                secure = optget("spice_x509_secure")

                crypto.create_x509_dir(prefix, c_subj, s_subj, passwd,
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

    def add_qxl(self, qxl_nr, qxl_memory=None):
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

    def add_vga(self, vga):
        return " -vga %s" % vga

    def add_kernel(self, filename):
        return " -kernel '%s'" % filename

    def add_initrd(self, filename):
        return " -initrd '%s'" % filename

    def add_rtc(self):
        # Pay attention that rtc-td-hack is for early version
        # if "rtc " in help:
        if self.devices.has_option("rtc"):
            cmd = " -rtc base=%s" % self.params.get("rtc_base", "utc")
            cmd += self.add_flag("clock", self.params.get("rtc_clock", "host"))
            cmd += self.add_flag("driftfix", self.params.get("rtc_drift", "none"))
            return cmd
        elif self.devices.has_option("rtc-td-hack"):
            return " -rtc-td-hack"
        else:
            return ""

    def add_kernel_cmdline(self, cmdline):
        return " -append '%s'" % cmdline

    def add_testdev(self, filename=None):
        if self.devices.has_device("testdev"):
            return (" -chardev file,id=testlog,path=%s"
                    " -device testdev,chardev=testlog" % filename)
        elif self.devices.has_device("pc-testdev"):
            return " -device pc-testdev"
        else:
            return ""

    def add_isa_debug_exit(self, iobase=0xf4, iosize=0x04):
        if self.devices.has_device("isa-debug-exit"):
            return (" -device isa-debug-exit,iobase=%s,iosize=%s" %
                    (iobase, iosize))
        else:
            return ""

    def add_no_hpet(self):
        if self.devices.has_option("no-hpet"):
            return " -no-hpet"
        else:
            return ""

    def add_cpu_flags(self, cpu_model, flags=None, vendor_id=None,
                      family=None):
        if self.devices.has_option('cpu'):
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

    def add_boot(self, boot_order, boot_once, boot_menu):
        cmd = " -boot"
        pattern = "boot \[order=drives\]\[,once=drives\]\[,menu=on\|off\]"
        if self.devices.has_option("boot \[a\|c\|d\|n\]"):
            cmd += " %s" % boot_once
        elif self.devices.has_option(pattern):
            cmd += (" order=%s,once=%s,menu=%s" %
                    (boot_order, boot_once, boot_menu))
        else:
            cmd = ""
        return cmd

    def get_index(self, index):
        while self.index_in_use.get(str(index)):
            index += 1
        return index

    def add_sga(self):
        if not self.devices.has_option("device"):
            return ""

        return " -device sga"

    def add_watchdog(self, device_type=None, action="reset"):
        watchdog_cmd = ""
        if self.devices.has_option("watchdog"):
            if device_type:
                watchdog_cmd += " -watchdog %s" % device_type
            watchdog_cmd += " -watchdog-action %s" % action

        return watchdog_cmd

    def add_option_rom(self, opt_rom):
        if not self.devices.has_option("option-rom"):
            return ""

        return " -option-rom %s" % opt_rom

    def add_smartcard(self, sc_chardev, sc_id):
        sc_cmd = " -device usb-ccid,id=ccid0"
        sc_cmd += " -chardev " + sc_chardev
        sc_cmd += ",id=" + sc_id + ",name=smartcard"
        sc_cmd += " -device ccid-card-passthru,chardev=" + sc_id

        return sc_cmd

    def add_numa_node(self, mem=None, cpus=None, nodeid=None):
        """
        This function used to add numa node to guest command line
        """
        if not self.devices.has_option("numa"):
            return ""
        numa_cmd = " -numa node"
        if mem is not None:
            numa_cmd += ",mem=%s" % mem
        if cpus is not None:
            numa_cmd += ",cpus=%s" % cpus
        if nodeid is not None:
            numa_cmd += ",nodeid=%s" % nodeid
        return numa_cmd

    def assemble(self, vm):
        """
        Assemble the qemu command line.
        """
        name = self.vm.name
        params = self.vm.params

        pci_bus = {'aobject': params.get('pci_bus', 'pci.0')}

        self.last_boot_index = 0
        if params.get("kernel"):
            self.last_boot_index = 1

        qemu_binary = q_path.get_qemu_binary(params)

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
            if len(memory.get_node_cpus()) < int(params.get("smp", 1)):
                logging.info("Skip pinning, no enough nodes")
            elif numa_node < 0:
                n = memory.NumaNode(numa_node)
                cmd += "numactl -m %s " % n.node_id
            else:
                n = numa_node - 1
                cmd += "numactl -m %s " % n

        self.devices.insert(qdevices.QStringDevice('PREFIX', cmdline=cmd))
        # Add the qemu binary
        self.devices.insert(qdevices.QStringDevice('qemu', cmdline=qemu_binary))
        self.devices.insert(qdevices.QStringDevice('-S', cmdline="-S"))
        # Add the VM's name
        self.devices.insert(qdevices.QStringDevice('vmname', cmdline=self.add_name(name)))

        if params.get("qemu_sandbox", "on") == "on":
            self.devices.insert(qdevices.QStringDevice('sandbox',
                                                       cmdline=self.process_sandbox("add")))
        elif params.get("sandbox", "off") == "off":
            self.devices.insert(qdevices.QStringDevice('qemu_sandbox',
                                                       cmdline=self.process_sandbox("rem")))

        devs = self.devices.machine_by_params(params)
        for dev in devs:
            self.devices.insert(dev)

        # no automagic self.devices please
        defaults = params.get("defaults", "no")
        if self.devices.has_option("nodefaults") and defaults != "yes":
            self.devices.insert(qdevices.QStringDevice('nodefaults', cmdline=" -nodefaults"))

        vga = params.get("vga")
        if vga:
            if vga != 'none':
                self.devices.insert(qdevices.QStringDevice('VGA-%s' % vga,
                                                           cmdline=self.add_vga(vga),
                                                           parent_bus={'aobject': 'pci.0'}))
            else:
                self.devices.insert(qdevices.QStringDevice('VGA-none', cmdline=self.add_vga(vga)))

            if vga == "qxl":
                qxl_dev_memory = int(params.get("qxl_dev_memory", 0))
                qxl_dev_nr = int(params.get("qxl_dev_nr", 1))
                self.devices.insert(qdevices.QStringDevice('qxl',
                                                           cmdline=self.add_qxl(qxl_dev_nr, qxl_dev_memory)))
        elif params.get('defaults', 'no') != 'no':  # by default add cirrus
            self.devices.insert(qdevices.QStringDevice('VGA-cirrus',
                                                       cmdline=self.add_vga(vga),
                                                       parent_bus={'aobject': 'pci.0'}))

        # When old scsi fmt is used, new device with lowest pci_addr is created
        self.devices.hook_fill_scsi_hbas(params)

        # Additional PCI RC/switch/bridges
        for pcic in params.objects("pci_controllers"):
            devs = self.devices.pcic_by_params(pcic, params.object_params(pcic))
            self.devices.insert(devs)

        # -soundhw addresses are always the lowest after scsi
        soundhw = params.get("soundcards")
        if soundhw:
            if not self.devices.has_option('device') or soundhw == "all":
                for sndcard in ('AC97', 'ES1370', 'intel-hda'):
                    # Add all dummy PCI self.devices and the actuall command below
                    self.devices.insert(qdevices.QStringDevice("SND-%s" % sndcard,
                                                               parent_bus=pci_bus))
                self.devices.insert(qdevices.QStringDevice('SoundHW',
                                                           cmdline="-soundhw %s" % soundhw))
            else:
                # TODO: Use qdevices.QDevices for this and set the addresses properly
                for sound_device in soundhw.split(","):
                    if "hda" in sound_device:
                        self.devices.insert(qdevices.QDevice('intel-hda',
                                                             parent_bus=pci_bus))
                        self.devices.insert(qdevices.QDevice('hda-duplex'))
                    elif sound_device in ["es1370", "ac97"]:
                        self.devices.insert(qdevices.QDevice(sound_device.upper(),
                                                             parent_bus=pci_bus))
                    else:
                        self.devices.insert(qdevices.QDevice(sound_device,
                                                             parent_bus=pci_bus))

        # Add monitors
        for monitor_name in params.objects("monitors"):
            monitor_params = params.object_params(monitor_name)
            monitor_filename = monitor.get_monitor_filename(vm, monitor_name)
            if monitor_params.get("monitor_type") == "qmp":
                cmd = self.add_qmp_monitor(monitor_name, monitor_filename)
                self.devices.insert(qdevices.QStringDevice('QMP-%s' % monitor_name, cmdline=cmd))
            else:
                cmd = self.add_human_monitor(monitor_name, monitor_filename)
                self.devices.insert(qdevices.QStringDevice('HMP-%s' % monitor_name, cmdline=cmd))

        # Add serial console redirection
        for serial in params.objects("isa_serials"):
            serial_filename = vm.get_serial_console_filename(serial)
            cmd = self.add_serial(serial, serial_filename)
            self.devices.insert(qdevices.QStringDevice('SER-%s' % serial, cmdline=cmd))

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
            # Multiple virtio console self.devices can't share a
            # single virtio-serial-pci bus. So add a virtio-serial-pci bus
            # when the port is a virtio console.
            if (port_params.get('virtio_port_type') == 'console'
                    and params.get('virtio_port_bus') is None):
                dev = qdevices.QDevice('virtio-serial-pci', parent_bus=pci_bus)
                dev.set_param('id',
                              'virtio_serial_pci%d' % no_virtio_serial_pcis)
                self.devices.insert(dev)
                no_virtio_serial_pcis += 1
            for i in range(no_virtio_serial_pcis, bus + 1):
                dev = qdevices.QDevice('virtio-serial-pci', parent_bus=pci_bus)
                dev.set_param('id', 'virtio_serial_pci%d' % i)
                self.devices.insert(dev)
                no_virtio_serial_pcis += 1
            if bus is not False:
                bus = "virtio_serial_pci%d.0" % bus
            # Add actual ports
            cmd = self.add_virtio_port(port_name, bus,
                                       self.get_virtio_port_filename(port_name),
                                       port_params.get('virtio_port_type'),
                                       port_params.get('virtio_port_chardev'),
                                       port_params.get('virtio_port_name_prefix'),
                                       no_virtio_ports,
                                       port_params.get('virtio_port_params', ''))
            self.devices.insert(qdevices.QStringDevice('VIO-%s' % port_name, cmdline=cmd))
            no_virtio_ports += 1

        # Add logging
        self.devices.insert(qdevices.QStringDevice('isa-log', cmdline=self.add_log_seabios()))
        if params.get("anaconda_log", "no") == "yes":
            self.add_log_anaconda(pci_bus)

        # Add USB controllers
        usbs = params.objects("usbs")
        if not self.devices.has_option("device"):
            usbs = ("oldusb",)  # Old qemu, add only one controller '-usb'
        for usb_name in usbs:
            usb_params = params.object_params(usb_name)
            for dev in self.devices.usbc_by_params(usb_name, usb_params):
                self.devices.insert(dev)

        # Add images (harddrives)
        for image_name in params.objects("images"):
            # FIXME: Use qemu_self.devices for handling indexes
            image_params = params.object_params(image_name)
            if image_params.get("boot_drive") == "no":
                continue
            if params.get("index_enable") == "yes":
                drive_index = image_params.get("drive_index")
                if drive_index:
                    index = drive_index
                else:
                    self.last_driver_index = self.get_index(self.last_driver_index)
                    index = str(self.last_driver_index)
                    self.last_driver_index += 1
            else:
                index = None
            image_bootindex = None
            image_boot = image_params.get("image_boot")
            if not re.search("boot=on\|off", self.devices.get_help_text(),
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
            devs = self.devices.images_define_by_params(image_name, image_params,
                                                        'disk', index, image_boot,
                                                        image_bootindex)
            for _ in devs:
                self.devices.insert(_)

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
                    script = path.get_path(script_dir, script)
                if downscript:
                    downscript = path.get_path(script_dir, downscript)
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
                    tftp = path.get_path(data_dir.get_data_dir(), nic.get("tftp"))
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
                self.add_nic(vlan, nic_model, mac,
                             device_id, netdev_id, nic_extra,
                             nic_params.get("nic_pci_addr"),
                             bootindex, queues, vectors, pci_bus)

                # Handle the '-net tap' or '-net user' or '-netdev' part
                cmd, cmd_nd = self.add_net(vlan, nettype, ifname, tftp,
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
                self.devices.insert(qdevices.QStringDevice("NET-%s" % nettype, cmdline=cmd,
                                                           params=net_params, cmdline_nd=cmd_nd))
            else:
                device_driver = nic_params.get("device_driver", "pci-assign")
                pci_id = vm.pa_pci_ids[iov]
                pci_id = ":".join(pci_id.split(":")[1:])
                self.add_pci_device(self.devices, pci_id, params=nic_params,
                                    device_driver=device_driver,
                                    pci_bus=pci_bus)
                iov += 1

        mem = params.get("mem")
        if mem:
            self.devices.insert(qdevices.QStringDevice('mem', cmdline=self.add_mem(mem)))

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
        self.devices.insert(qdevices.QStringDevice('smp', cmdline=self.add_smp()))

        numa_total_cpus = 0
        numa_total_mem = 0
        for numa_node in params.objects("guest_numa_nodes"):
            numa_params = params.object_params(numa_node)
            numa_mem = numa_params.get("numa_mem")
            numa_cpus = numa_params.get("numa_cpus")
            if numa_mem is not None:
                numa_total_mem += int(numa_mem)
            if numa_cpus is not None:
                numa_total_cpus += len(memory.cpu_str_to_list(numa_cpus))
            self.devices.insert(qdevices.QStringDevice('numa', cmdline=self.add_numa_node()))

        if params.get("numa_consistency_check_cpu_mem", "no") == "yes":
            if (numa_total_cpus > int(smp) or numa_total_mem > int(mem)
                    or len(params.objects("guest_numa_nodes")) > int(smp)):
                logging.debug("-numa need %s vcpu and %s memory. It is not "
                              "matched the -smp and -mem. The vcpu number "
                              "from -smp is %s, and memory size from -mem is"
                              " %s" % (numa_total_cpus, numa_total_mem, smp,
                                       mem))
                raise exceptions.VMDeviceError("The numa node cfg can not fit"
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
            cmd = self.add_cpu_flags(cpu_model, flags, vendor, family)
            self.devices.insert(qdevices.QStringDevice('cpu', cmdline=cmd))

        # Add cdroms
        for cdrom in params.objects("cdroms"):
            image_params = params.object_params(cdrom)
            # FIXME: Use qemu_self.devices for handling indexes
            if image_params.get("boot_drive") == "no":
                continue
            if params.get("index_enable") == "yes":
                drive_index = image_params.get("drive_index")
                if drive_index:
                    index = drive_index
                else:
                    self.last_driver_index = self.get_index(self.last_driver_index)
                    index = str(self.last_driver_index)
                    self.last_driver_index += 1
            else:
                index = None
            image_bootindex = None
            image_boot = image_params.get("image_boot")
            if not re.search("boot=on\|off", self.devices.get_help_text(),
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
                devs = self.devices.cdroms_define_by_params(cdrom, image_params,
                                                            'cdrom', index,
                                                            image_boot,
                                                            image_bootindex)
                for _ in devs:
                    self.devices.insert(_)

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
            image_params['image_name'] = path.get_path(
                data_dir.get_data_dir(),
                image_params["floppy_name"])
            image_params['image_format'] = None
            devs = self.devices.images_define_by_params(floppy_name, image_params,
                                                        media='')
            for _ in devs:
                self.devices.insert(_)

        # Add usb self.devices
        for usb_dev in params.objects("usb_devices"):
            usb_dev_params = params.object_params(usb_dev)
            self.devices.insert(self.devices.usb_by_params(usb_dev, usb_dev_params))

        tftp = params.get("tftp")
        if tftp:
            tftp = path.get_path(data_dir.get_data_dir(), tftp)
            self.devices.insert(qdevices.QStringDevice('tftp', cmdline=self.add_tftp(tftp)))

        bootp = params.get("bootp")
        if bootp:
            self.devices.insert(qdevices.QStringDevice('bootp',
                                                       cmdline=self.add_bootp(bootp)))

        kernel = params.get("kernel")
        if kernel:
            kernel = path.get_path(data_dir.get_data_dir(), kernel)
            self.devices.insert(qdevices.QStringDevice('kernel',
                                                       cmdline=self.add_kernel(kernel)))

        kernel_params = params.get("kernel_params")
        if kernel_params:
            cmd = self.add_kernel_cmdline(kernel_params)
            self.devices.insert(qdevices.QStringDevice('kernel-params', cmdline=cmd))

        initrd = params.get("initrd")
        if initrd:
            initrd = path.get_path(data_dir.get_data_dir(), initrd)
            self.devices.insert(qdevices.QStringDevice('initrd',
                                                       cmdline=self.add_initrd(initrd)))

        for host_port, guest_port in redirs:
            cmd = self.add_tcp_redir(host_port, guest_port)
            self.devices.insert(qdevices.QStringDevice('tcp-redir', cmdline=cmd))

        cmd = ""
        if params.get("display") == "vnc":
            vnc_extra_params = params.get("vnc_extra_params")
            vnc_password = params.get("vnc_password", "no")
            cmd += self.add_vnc(self.vnc_port, vnc_password,
                                vnc_extra_params)
        elif params.get("display") == "sdl":
            cmd += self.add_sdl()
        elif params.get("display") == "nographic":
            cmd += self.add_nographic()
        elif params.get("display") == "spice":
            if params.get("rhel5_spice"):
                spice_params = params.get("spice_params")
                cmd += self.add_spice_rhel5(self.devices, spice_params)
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

                cmd += self.add_spice()
        if cmd:
            self.devices.insert(qdevices.QStringDevice('display', cmdline=cmd))

        if params.get("uuid") == "random":
            cmd = self.add_uuid(vm.uuid)
            self.devices.insert(qdevices.QStringDevice('uuid', cmdline=cmd))
        elif params.get("uuid"):
            cmd = self.add_uuid(params.get("uuid"))
            self.devices.insert(qdevices.QStringDevice('uuid', cmdline=cmd))

        if params.get("testdev") == "yes":
            cmd = self.add_testdev(vm.get_testlog_filename())
            self.devices.insert(qdevices.QStringDevice('testdev', cmdline=cmd))

        if params.get("isa_debugexit") == "yes":
            iobase = params.get("isa_debugexit_iobase")
            iosize = params.get("isa_debugexit_iosize")
            cmd = self.add_isa_debug_exit(iobase, iosize)
            self.devices.insert(qdevices.QStringDevice('isa_debugexit', cmdline=cmd))

        if params.get("disable_hpet") == "yes":
            self.devices.insert(qdevices.QStringDevice('nohpet', cmdline=self.add_no_hpet()))

        self.devices.insert(qdevices.QStringDevice('rtc', cmdline=self.add_rtc()))

        if self.devices.has_option("boot"):
            boot_order = params.get("boot_order", "cdn")
            boot_once = params.get("boot_once", "c")
            boot_menu = params.get("boot_menu", "off")
            cmd = self.add_boot(boot_order, boot_once, boot_menu)
            self.devices.insert(qdevices.QStringDevice('bootmenu', cmdline=cmd))

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
                    raise exceptions.VMImageMissingError("Socket name not "
                                                         "defined")
                cmd += p9_socket_name

            p9_immediate_writeout = params.get("9p_immediate_writeout")
            if p9_immediate_writeout == "yes":
                cmd += ",writeout=immediate"

            p9_readonly = params.get("9p_readonly")
            if p9_readonly == "yes":
                cmd += ",readonly"

            self.devices.insert(qdevices.QStringDevice('fsdev', cmdline=cmd))

            dev = qdevices.QDevice('virtio-9p-pci', parent_bus=pci_bus)
            dev.set_param('fsdev', 'local1')
            dev.set_param('mount_tag', 'autotest_tag')
            self.devices.insert(dev)

        extra_params = params.get("extra_params")
        if extra_params:
            self.devices.insert(qdevices.QStringDevice('extra', cmdline=extra_params))

        bios_path = params.get("bios_path")
        if bios_path:
            self.devices.insert(qdevices.QStringDevice('bios', cmdline="-bios %s" % bios_path))

        disable_kvm_option = ""
        if (self.devices.has_option("no-kvm")):
            disable_kvm_option = "-no-kvm"

        enable_kvm_option = ""
        if (self.devices.has_option("enable-kvm")):
            enable_kvm_option = "-enable-kvm"

        if (params.get("disable_kvm", "no") == "yes"):
            params["enable_kvm"] = "no"

        if (params.get("enable_kvm", "yes") == "no"):
            self.devices.insert(qdevices.QStringDevice('nokvm', cmdline=disable_kvm_option))
            logging.debug("qemu will run in TCG mode")
        else:
            self.devices.insert(qdevices.QStringDevice('kvm', cmdline=enable_kvm_option))
            logging.debug("qemu will run in KVM mode")

        self.no_shutdown = (self.devices.has_option("no-shutdown") and
                            params.get("disable_shutdown", "no") == "yes")
        if self.no_shutdown:
            self.devices.insert(qdevices.QStringDevice('noshutdown', cmdline="-no-shutdown"))

        user_runas = params.get("user_runas")
        if self.devices.has_option("runas") and user_runas:
            self.devices.insert(qdevices.QStringDevice('runas', cmdline="-runas %s" % user_runas))

        if params.get("enable_sga") == "yes":
            self.devices.insert(qdevices.QStringDevice('sga', cmdline=self.add_sga()))

        if params.get("smartcard", "no") == "yes":
            sc_chardev = params.get("smartcard_chardev")
            sc_id = params.get("smartcard_id")
            self.devices.insert(qdevices.QStringDevice('smartcard',
                                                       cmdline=self.add_smartcard(sc_chardev, sc_id)))

        if params.get("enable_watchdog", "no") == "yes":
            cmd = self.add_watchdog(params.get("watchdog_device_type", None),
                                    params.get("watchdog_action", "reset"))
            self.devices.insert(qdevices.QStringDevice('watchdog', cmdline=cmd))

        option_roms = params.get("option_roms")
        if option_roms:
            cmd = ""
            for opt_rom in option_roms.split():
                cmd += self.add_option_rom(opt_rom)
            if cmd:
                self.devices.insert(qdevices.QStringDevice('ROM', cmdline=cmd))

        return self.devices
