"""
Library to perform pre/post test setup for virt test.
"""
import os
import logging
import time
import re
import random
import math
import shutil
from autotest.client.shared import error, utils
from autotest.client import os_dep
import utils_misc

try:
    from virttest.staging import utils_memory
except ImportError:
    # pylint: disable=E0611
    from autotest.client import utils_memory


class THPError(Exception):

    """
    Base exception for Transparent Hugepage setup.
    """
    pass


class THPNotSupportedError(THPError):

    """
    Thrown when host does not support tansparent hugepages.
    """
    pass


class THPWriteConfigError(THPError):

    """
    Thrown when host does not support tansparent hugepages.
    """
    pass


class THPKhugepagedError(THPError):

    """
    Thrown when khugepaged is not behaving as expected.
    """
    pass


class PolkitConfigError(Exception):

    """
    Base exception for Polkit Config setup.
    """
    pass


class PolkitRulesSetupError(PolkitConfigError):

    """
    Thrown when setup polkit rules is not behaving as expected.
    """
    pass


class PolkitWriteLibvirtdConfigError(PolkitConfigError):

    """
    Thrown when setup libvirtd config file is not behaving as expected.
    """
    pass


class PolkitConfigCleanupError(PolkitConfigError):

    """
    Thrown when polkit config cleanup is not behaving as expected.
    """
    pass


class TransparentHugePageConfig(object):

    def __init__(self, test, params):
        """
        Find paths for transparent hugepages and kugepaged configuration. Also,
        back up original host configuration so it can be restored during
        cleanup.
        """
        self.params = params

        RH_THP_PATH = "/sys/kernel/mm/redhat_transparent_hugepage"
        UPSTREAM_THP_PATH = "/sys/kernel/mm/transparent_hugepage"
        if os.path.isdir(RH_THP_PATH):
            self.thp_path = RH_THP_PATH
        elif os.path.isdir(UPSTREAM_THP_PATH):
            self.thp_path = UPSTREAM_THP_PATH
        else:
            raise THPNotSupportedError("System doesn't support transparent "
                                       "hugepages")

        tmp_list = []
        test_cfg = {}
        test_config = self.params.get("test_config", None)
        if test_config is not None:
            tmp_list = re.split(';', test_config)
        while len(tmp_list) > 0:
            tmp_cfg = tmp_list.pop()
            test_cfg[re.split(":", tmp_cfg)[0]] = re.split(":", tmp_cfg)[1]
        # Save host current config, so we can restore it during cleanup
        # We will only save the writeable part of the config files
        original_config = {}
        # List of files that contain string config values
        self.file_list_str = []
        # List of files that contain integer config values
        self.file_list_num = []
        logging.info("Scanning THP base path and recording base values")
        for f in os.walk(self.thp_path):
            base_dir = f[0]
            if f[2]:
                for name in f[2]:
                    f_dir = os.path.join(base_dir, name)
                    parameter = file(f_dir, 'r').read()
                    logging.debug("Reading path %s: %s", f_dir,
                                  parameter.strip())
                    try:
                        # Verify if the path in question is writable
                        f = open(f_dir, 'w')
                        f.close()
                        if re.findall("\[(.*)\]", parameter):
                            original_config[f_dir] = re.findall("\[(.*)\]",
                                                                parameter)[0]
                            self.file_list_str.append(f_dir)
                        else:
                            original_config[f_dir] = int(parameter)
                            self.file_list_num.append(f_dir)
                    except IOError:
                        pass

        self.test_config = test_cfg
        self.original_config = original_config

    def set_env(self):
        """
        Applies test configuration on the host.
        """
        if self.test_config:
            logging.info("Applying custom THP test configuration")
            for path in self.test_config.keys():
                logging.info("Writing path %s: %s", path,
                             self.test_config[path])
                file(path, 'w').write(self.test_config[path])

    def value_listed(self, value):
        """
        Get a parameters list from a string
        """
        value_list = []
        for i in re.split("\[|\]|\n+|\s+", value):
            if i:
                value_list.append(i)
        return value_list

    def khugepaged_test(self):
        """
        Start, stop and frequency change test for khugepaged.
        """
        def check_status_with_value(action_list, file_name):
            """
            Check the status of khugepaged when set value to specify file.
            """
            for (act, ret) in action_list:
                logging.info("Writing path %s: %s, expected khugepage rc: %s ",
                             file_name, act, ret)
                try:
                    file_object = open(file_name, "w")
                    file_object.write(act)
                    file_object.close()
                except IOError, error_detail:
                    logging.info("IO Operation on path %s failed: %s",
                                 file_name, error_detail)
                timeout = time.time() + 50
                while time.time() < timeout:
                    try:
                        utils.run('pgrep khugepaged', verbose=False)
                        if ret != 0:
                            time.sleep(1)
                            continue
                    except error.CmdError:
                        if ret == 0:
                            time.sleep(1)
                            continue
                    break
                else:
                    if ret != 0:
                        raise THPKhugepagedError("Khugepaged still alive when"
                                                 "transparent huge page is "
                                                 "disabled")
                    else:
                        raise THPKhugepagedError("Khugepaged could not be set to"
                                                 "status %s" % act)

        logging.info("Testing khugepaged")
        for file_path in self.file_list_str:
            action_list = []
            if re.findall("enabled", file_path):
                # Start and stop test for khugepaged
                value_list = self.value_listed(open(file_path, "r").read())
                for i in value_list:
                    if re.match("n", i, re.I):
                        action_stop = (i, 256)
                for i in value_list:
                    if re.match("[^n]", i, re.I):
                        action = (i, 0)
                        action_list += [action_stop, action, action_stop]
                action_list += [action]

                check_status_with_value(action_list, file_path)
            else:
                value_list = self.value_listed(open(file_path, "r").read())
                for i in value_list:
                    action = (i, 0)
                    action_list.append(action)
                check_status_with_value(action_list, file_path)

        for file_path in self.file_list_num:
            action_list = []
            file_object = open(file_path, "r")
            value = file_object.read()
            value = int(value)
            file_object.close()
            if value != 0 and value != 1:
                new_value = random.random()
                action_list.append((str(int(value * new_value)), 0))
                action_list.append((str(int(value * (new_value + 1))), 0))
            else:
                action_list.append(("0", 0))
                action_list.append(("1", 0))

            check_status_with_value(action_list, file_path)

    def setup(self):
        """
        Configure host for testing. Also, check that khugepaged is working as
        expected.
        """
        self.set_env()
        self.khugepaged_test()

    def cleanup(self):
        """:
        Restore the host's original configuration after test
        """
        logging.info("Restoring host's original THP configuration")
        for path in self.original_config:
            logging.info("Writing path %s: %s", path,
                         self.original_config[path])
            try:
                p_file = open(path, 'w')
                p_file.write(str(self.original_config[path]))
                p_file.close()
            except IOError, error_detail:
                logging.info("IO operation failed on file %s: %s", path,
                             error_detail)


class HugePageConfig(object):

    def __init__(self, params):
        """
        Gets environment variable values and calculates the target number
        of huge memory pages.

        :param params: Dict like object containing parameters for the test.
        """
        self.vms = len(params.objects("vms"))
        self.mem = int(params.get("mem"))
        self.max_vms = int(params.get("max_vms", 0))
        self.qemu_overhead = int(params.get("hugepages_qemu_overhead", 128))
        self.deallocate = params.get("hugepages_deallocate", "yes") == "yes"
        self.hugepage_path = '/mnt/kvm_hugepage'
        self.kernel_hp_file = '/proc/sys/vm/nr_hugepages'
        self.hugepage_size = self.get_hugepage_size()
        self.hugepage_force_allocate = params.get("hugepage_force_allocate",
                                                  "no")
        self.suggest_mem = None
        self.lowest_mem_per_vm = int(params.get("lowest_mem", "256"))

        target_hugepages = params.get("target_hugepages")
        if target_hugepages is None:
            target_hugepages = self.get_target_hugepages()
        else:
            target_hugepages = int(target_hugepages)

        self.target_hugepages = target_hugepages

    def get_hugepage_size(self):
        """
        Get the current system setting for huge memory page size.
        """
        meminfo = open('/proc/meminfo', 'r').readlines()
        huge_line_list = [h for h in meminfo if h.startswith("Hugepagesize")]
        try:
            return int(huge_line_list[0].split()[1])
        except ValueError, e:
            raise ValueError("Could not get huge page size setting from "
                             "/proc/meminfo: %s" % e)

    def get_target_hugepages(self):
        """
        Calculate the target number of hugepages for testing purposes.
        """
        if self.vms < self.max_vms:
            self.vms = self.max_vms
        # memory of all VMs plus qemu overhead of 128MB per guest
        # (this value can be overriden in your cartesian config)
        vmsm = self.vms * (self.mem + self.qemu_overhead)
        target_hugepages = int(vmsm * 1024 / self.hugepage_size)

        # FIXME Now the buddyinfo can not get chunk info which is bigger
        # than 4M. So this will only fit for 2M size hugepages. Can not work
        # when hugepage size is 1G.
        # And sometimes huge page can not get all pages so decrease the page
        # for about 10 huge page to make sure the allocate can success

        decreased_pages = 10
        if self.hugepage_size > 2048:
            self.hugepage_force_allocate = "yes"

        if self.hugepage_force_allocate == "no":
            hugepage_allocated = open(self.kernel_hp_file, "r")
            available_hugepages = int(hugepage_allocated.read().strip())
            hugepage_allocated.close()
            chunk_bottom = int(math.log(self.hugepage_size / 4, 2))
            chunk_info = utils_memory.get_buddy_info(">=%s" % chunk_bottom,
                                                     zones="DMA32 Normal")
            for size in chunk_info:
                available_hugepages += int(chunk_info[size] * math.pow(2,
                                                                       int(int(size) - chunk_bottom)))

            available_hugepages = available_hugepages - decreased_pages
            if target_hugepages > available_hugepages:
                logging.warn("This test requires more huge pages than we"
                             " currently have, we'll try to allocate the"
                             " biggest number the system can support.")
                target_hugepages = available_hugepages
                available_mem = available_hugepages * self.hugepage_size
                self.suggest_mem = int(available_mem / self.vms / 1024
                                       - self.qemu_overhead)
                if self.suggest_mem < self.lowest_mem_per_vm:
                    raise MemoryError("This host doesn't have enough free "
                                      "large memory pages for this test to "
                                      "run (only %s MB memory available for "
                                      "each guest)" % self.suggest_mem)

        return target_hugepages

    @error.context_aware
    def set_hugepages(self):
        """
        Sets the hugepage limit to the target hugepage value calculated.
        """
        error.context("setting hugepages limit to %s" % self.target_hugepages)
        hugepage_cfg = open(self.kernel_hp_file, "r+")
        hp = hugepage_cfg.readline()
        while int(hp) < self.target_hugepages:
            loop_hp = hp
            hugepage_cfg.write(str(self.target_hugepages))
            hugepage_cfg.flush()
            hugepage_cfg.seek(0)
            hp = int(hugepage_cfg.readline())
            if loop_hp == hp:
                raise ValueError("Cannot set the kernel hugepage setting "
                                 "to the target value of %d hugepages." %
                                 self.target_hugepages)
        hugepage_cfg.close()
        logging.debug("Successfully set %s large memory pages on host ",
                      self.target_hugepages)

    @error.context_aware
    def mount_hugepage_fs(self):
        """
        Verify if there's a hugetlbfs mount set. If there's none, will set up
        a hugetlbfs mount using the class attribute that defines the mount
        point.
        """
        error.context("mounting hugepages path")
        if not os.path.ismount(self.hugepage_path):
            if not os.path.isdir(self.hugepage_path):
                os.makedirs(self.hugepage_path)
            cmd = "mount -t hugetlbfs none %s" % self.hugepage_path
            utils.system(cmd)

    def setup(self):
        logging.debug("Number of VMs this test will use: %d", self.vms)
        logging.debug("Amount of memory used by each vm: %s", self.mem)
        logging.debug("System setting for large memory page size: %s",
                      self.hugepage_size)
        logging.debug("Number of large memory pages needed for this test: %s",
                      self.target_hugepages)
        self.set_hugepages()
        self.mount_hugepage_fs()

        return self.suggest_mem

    @error.context_aware
    def cleanup(self):
        if self.deallocate:
            error.context("trying to dealocate hugepage memory")
            try:
                utils.system("umount %s" % self.hugepage_path)
            except error.CmdError:
                return
            utils.system("echo 0 > %s" % self.kernel_hp_file)
            logging.debug("Hugepage memory successfully dealocated")


class KSMConfig(object):

    def __init__(self, params, env):
        """
        :param params: Dict like object containing parameters for the test.
        """
        self.pages_to_scan = params.get("ksm_pages_to_scan")
        self.sleep_ms = params.get("ksm_sleep_ms")
        self.run = params.get("ksm_run", "1")
        self.ksm_module = params.get("ksm_module")

        if self.run == "yes":
            self.run = "1"
        elif self.run == "no":
            self.run == "0"

        # Get KSM module status if there is one
        self.ksmctler = utils_misc.KSMController()
        self.ksm_module_loaded = self.ksmctler.is_module_loaded()

        # load the ksm module for furthur information check
        if self.ksm_module and not self.ksm_module_loaded:
            self.ksmctler.load_ksm_module()

        # For ksmctl both pages_to_scan and sleep_ms should have value
        # So give some default value when it is not set up in params
        if self.pages_to_scan is None:
            self.pages_to_scan = "5000"
        if self.sleep_ms is None:
            self.sleep_ms = "50"

        # Check if ksmtuned is running before the test
        self.ksmtuned_process = self.ksmctler.get_ksmtuned_pid()

        # As ksmtuned may update KSM config most of the time we should disable
        # it when we test KSM
        self.disable_ksmtuned = params.get("disable_ksmtuned", "yes") == "yes"

        self.default_status = []
        self.default_status.append(self.ksmctler.get_ksm_feature("run"))
        self.default_status.append(self.ksmctler.get_ksm_feature(
            "pages_to_scan"))
        self.default_status.append(self.ksmctler.get_ksm_feature(
            "sleep_millisecs"))
        self.default_status.append(int(self.ksmtuned_process))
        self.default_status.append(self.ksm_module_loaded)

    def setup(self, env):
        if self.disable_ksmtuned:
            self.ksmctler.stop_ksmtuned()

        env.data["KSM_default_config"] = self.default_status
        self.ksmctler.set_ksm_feature({"run": self.run,
                                       "pages_to_scan": self.pages_to_scan,
                                       "sleep_millisecs": self.sleep_ms})

    def cleanup(self, env):
        default_status = env.data.get("KSM_default_config")

        # Get original ksm loaded status
        default_ksm_loaded = default_status.pop()
        # Remove pid of ksmtuned
        if default_status.pop() != 0:
            # ksmtuned used to run in host. Start the process
            # and don't need set up the configures.
            self.ksmctler.start_ksmtuned()
            return

        if default_status == self.default_status:
            # Nothing changed
            return

        self.ksmctler.set_ksm_feature({"run": default_status[0],
                                       "pages_to_scan": default_status[1],
                                       "sleep_millisecs": default_status[2]})

        if self.ksm_module and not default_ksm_loaded:
            self.ksmctler.unload_ksm_module()


class PrivateBridgeError(Exception):

    def __init__(self, brname):
        self.brname = brname

    def __str__(self):
        return "Bridge %s not available after setup" % self.brname


class PrivateBridgeConfig(object):
    __shared_state = {}

    def __init__(self, params=None):
        self.__dict__ = self.__shared_state
        if params is not None:
            self.brname = params.get("priv_brname", 'atbr0')
            self.subnet = params.get("priv_subnet", '192.168.58')
            self.ip_version = params.get("bridge_ip_version", "ipv4")
            self.dhcp_server_pid = None
            ports = params.get("priv_bridge_ports", '53 67').split()
            s_port = params.get("guest_port_remote_shell", "10022")
            if s_port not in ports:
                ports.append(s_port)
            ft_port = params.get("guest_port_file_transfer", "10023")
            if ft_port not in ports:
                ports.append(ft_port)
            u_port = params.get("guest_port_unattended_install", "13323")
            if u_port not in ports:
                ports.append(u_port)
            self.iptables_rules = self._assemble_iptables_rules(ports)
            self.physical_nic = params.get("physical_nic")
            self.force_create = False
            if params.get("bridge_force_create", "no") == "yes":
                self.force_create = True

    def _assemble_iptables_rules(self, port_list):
        rules = []
        index = 0
        for port in port_list:
            index += 1
            rules.append("INPUT %s -i %s -p tcp --dport %s -j ACCEPT" %
                         (index, self.brname, port))
            index += 1
            rules.append("INPUT %s -i %s -p udp --dport %s -j ACCEPT" %
                         (index, self.brname, port))
        rules.append("FORWARD 1 -m physdev --physdev-is-bridged -j ACCEPT")
        rules.append("FORWARD 2 -d %s.0/24 -o %s -m state "
                     "--state RELATED,ESTABLISHED -j ACCEPT" %
                     (self.subnet, self.brname))
        rules.append("FORWARD 3 -s %s.0/24 -i %s -j ACCEPT" %
                     (self.subnet, self.brname))
        rules.append("FORWARD 4 -i %s -o %s -j ACCEPT" %
                     (self.brname, self.brname))
        return rules

    def _add_bridge(self):
        utils.system("brctl addbr %s" % self.brname)
        ip_fwd_path = "/proc/sys/net/%s/ip_forward" % self.ip_version
        ip_fwd = open(ip_fwd_path, "w")
        ip_fwd.write("1\n")
        utils.system("brctl stp %s on" % self.brname)
        utils.system("brctl setfd %s 4" % self.brname)
        if self.physical_nic:
            utils.system("brctl addif %s %s" % (self.brname,
                                                self.physical_nic))

    def _bring_bridge_up(self):
        utils.system("ifconfig %s %s.1 up" % (self.brname, self.subnet))

    def _iptables_add(self, cmd):
        return utils.system("iptables -I %s" % cmd)

    def _iptables_del(self, cmd):
        return utils.system("iptables -D %s" % cmd)

    def _enable_nat(self):
        for rule in self.iptables_rules:
            self._iptables_add(rule)

    def _start_dhcp_server(self):
        utils.system("service dnsmasq stop")
        utils.system("dnsmasq --strict-order --bind-interfaces "
                     "--listen-address %s.1 --dhcp-range %s.2,%s.254 "
                     "--dhcp-lease-max=253 "
                     "--dhcp-no-override "
                     "--pid-file=/tmp/dnsmasq.pid "
                     "--log-facility=/tmp/dnsmasq.log" %
                     (self.subnet, self.subnet, self.subnet))
        self.dhcp_server_pid = None
        try:
            self.dhcp_server_pid = int(open('/tmp/dnsmasq.pid', 'r').read())
        except ValueError:
            raise PrivateBridgeError(self.brname)
        logging.debug("Started internal DHCP server with PID %s",
                      self.dhcp_server_pid)

    def _verify_bridge(self):
        brctl_output = utils.system_output("brctl show")
        if self.brname not in brctl_output:
            raise PrivateBridgeError(self.brname)

    def setup(self):
        brctl_output = utils.system_output("brctl show")
        if self.brname in brctl_output and self.force_create:
            self._bring_bridge_down()
            self._remove_bridge()
            brctl_output = utils.system_output("brctl show")
        if self.brname not in brctl_output:
            logging.info("Configuring KVM test private bridge %s", self.brname)
            try:
                self._add_bridge()
            except:
                self._remove_bridge()
                raise
            try:
                self._bring_bridge_up()
            except:
                self._bring_bridge_down()
                self._remove_bridge()
                raise
            try:
                self._enable_nat()
            except:
                self._disable_nat()
                self._bring_bridge_down()
                self._remove_bridge()
                raise
            try:
                self._start_dhcp_server()
            except:
                self._stop_dhcp_server()
                self._disable_nat()
                self._bring_bridge_down()
                self._remove_bridge()
                raise
            # Fix me the physical_nic always down after setup
            # Need manually up.
            if self.physical_nic:
                time.sleep(5)
                utils.system("ifconfig %s up" % self.physical_nic)

            self._verify_bridge()

    def _stop_dhcp_server(self):
        if self.dhcp_server_pid is not None:
            try:
                os.kill(self.dhcp_server_pid, 15)
            except OSError:
                pass
        else:
            try:
                dhcp_server_pid = int(open('/tmp/dnsmasq.pid', 'r').read())
            except ValueError:
                return
            try:
                os.kill(dhcp_server_pid, 15)
            except OSError:
                pass

    def _bring_bridge_down(self):
        utils.system("ifconfig %s down" % self.brname, ignore_status=True)

    def _disable_nat(self):
        for rule in self.iptables_rules:
            split_list = rule.split(' ')
            # We need to remove numbering here
            split_list.pop(1)
            rule = " ".join(split_list)
            self._iptables_del(rule)

    def _remove_bridge(self):
        utils.system("brctl delbr %s" % self.brname, ignore_status=True)

    def cleanup(self):
        brctl_output = utils.system_output("brctl show")
        cleanup = False
        for line in brctl_output.split("\n"):
            if line.startswith(self.brname):
                # len == 4 means there is a TAP using the bridge
                # so don't try to clean it up
                if len(line.split()) < 4:
                    cleanup = True
                    break
        if cleanup:
            logging.debug(
                "Cleaning up KVM test private bridge %s", self.brname)
            self._stop_dhcp_server()
            self._disable_nat()
            self._bring_bridge_down()
            self._remove_bridge()


class PciAssignable(object):

    """
    Request PCI assignable devices on host. It will check whether to request
    PF (physical Functions) or VF (Virtual Functions).
    """

    def __init__(self, driver=None, driver_option=None, host_set_flag=None,
                 kvm_params=None, vf_filter_re=None, pf_filter_re=None,
                 device_driver=None):
        """
        Initialize parameter 'type' which could be:
        vf: Virtual Functions
        pf: Physical Function (actual hardware)
        mixed:  Both includes VFs and PFs

        If pass through Physical NIC cards, we need to specify which devices
        to be assigned, e.g. 'eth1 eth2'.

        If pass through Virtual Functions, we need to specify max vfs in driver
        e.g. max_vfs = 7 in config file.

        :param type: PCI device type.
        :type type: string
        :param driver: Kernel module for the PCI assignable device.
        :type driver: string
        :param driver_option: Module option to specify the maximum number of
                VFs (eg 'max_vfs=7')
        :type driver_option: string
        :param host_set_flag: Flag for if the test should setup host env:
               0: do nothing
               1: do setup env
               2: do cleanup env
               3: setup and cleanup env
        :type host_set_flag: string
        :param kvm_params: a dict for kvm module parameters default value
        :type kvm_params: dict
        :param vf_filter_re: Regex used to filter vf from lspci.
        :type vf_filter_re: string
        :param pf_filter_re: Regex used to filter pf from lspci.
        :type pf_filter_re: string
        """
        self.devices = []
        self.driver = driver
        self.driver_option = driver_option
        self.name_list = []
        self.devices_requested = 0
        self.pf_vf_info = []
        self.dev_unbind_drivers = {}
        self.dev_drivers = {}
        self.vf_filter_re = vf_filter_re
        self.pf_filter_re = pf_filter_re
        if device_driver:
            if device_driver == "pci-assign":
                self.device_driver = "pci-stub"
            else:
                self.device_driver = device_driver
        else:
            self.device_driver = "pci-stub"
        if host_set_flag is not None:
            self.setup = int(host_set_flag) & 1 == 1
            self.cleanup = int(host_set_flag) & 2 == 2
        else:
            self.setup = False
            self.cleanup = False
        self.kvm_params = kvm_params
        self.auai_path = None
        if self.kvm_params is not None:
            for i in self.kvm_params:
                if "allow_unsafe_assigned_interrupts" in i:
                    self.auai_path = i
        if self.setup:
            self.sr_iov_setup()

    def add_device(self, device_type="vf", name=None, mac=None):
        """
        Add device type and name to class.

        :param device_type: vf/pf device is added.
        :type device_type: string
        :param name: Physical device interface name. eth1 or others
        :type name: string
        :param mac: set mac address for vf.
        :type mac: string
        """
        device = {}
        device['type'] = device_type
        if name is not None:
            device['name'] = name
        if mac:
            device['mac'] = mac
        self.devices.append(device)
        self.devices_requested += 1

    def _get_pf_pci_id(self, name=None):
        """
        Get the PF PCI ID according to name.
        It returns the first free pf, if no name matched.

        :param name: Name of the PCI device.
        :type name: string
        :return: pci id of the PF device.
        :rtype: string
        """
        pf_id = None
        if self.pf_vf_info:
            for pf in self.pf_vf_info:
                if "ethname" in pf and name == pf["ethname"]:
                    pf["occupied"] = True
                    pf_id = pf["pf_id"]
                    break
            if pf_id is None:
                for pf in self.pf_vf_info:
                    if not pf["occupied"]:
                        pf["occupied"] = True
                        pf_id = pf["pf_id"]
                        break
        return pf_id

    @error.context_aware
    def _release_dev(self, pci_id):
        """
        Release a single PCI device.

        :param pci_id: PCI ID of a given PCI device.
        :type pci_id: string
        :return: True if successfully release the device. else false.
        :rtype: bool
        """
        base_dir = "/sys/bus/pci"
        short_id = pci_id[5:]
        vendor_id = utils_misc.get_vendor_from_pci_id(short_id)
        drv_path = os.path.join(base_dir, "devices/%s/driver" % pci_id)
        if self.device_driver in os.readlink(drv_path):
            error.context("Release device %s to host" % pci_id, logging.info)
            driver = self.dev_unbind_drivers[pci_id]
            cmd = "echo '%s' > %s/new_id" % (vendor_id, driver)
            logging.info("Run command in host: %s" % cmd)
            try:
                output = utils.system_output(cmd, timeout=60)
            except error.CmdError:
                msg = "Command %s fail with output %s" % (cmd, output)
                logging.error(msg)
                return False

            stub_path = os.path.join(base_dir,
                                     "drivers/%s" % self.device_driver)
            cmd = "echo '%s' > %s/unbind" % (pci_id, stub_path)
            logging.info("Run command in host: %s" % cmd)
            try:
                output = utils.system_output(cmd, timeout=60)
            except error.CmdError:
                msg = "Command %s fail with output %s" % (cmd, output)
                logging.error(msg)
                return False

            driver = self.dev_unbind_drivers[pci_id]
            cmd = "echo '%s' > %s/bind" % (pci_id, driver)
            logging.info("Run command in host: %s" % cmd)
            try:
                output = utils.system_output(cmd, timeout=60)
            except error.CmdError:
                msg = "Command %s fail with output %s" % (cmd, output)
                logging.error(msg)
                return False
        if self.is_binded_to_stub(pci_id):
            return False
        return True

    def get_vf_status(self, vf_id):
        """
        Check whether one vf is assigned to VM.

        :param vf_id: vf id to check.
        :type vf_id: string
        :return: Return True if vf has already assinged to VM. Else
                 return false.
        :rtype: bool
        """
        base_dir = "/sys/bus/pci"
        tub_path = os.path.join(base_dir, "drivers/pci-stub")
        vf_res_path = os.path.join(tub_path, "%s/resource*" % vf_id)
        cmd = "lsof %s" % vf_res_path
        output = utils.system_output(cmd, timeout=60, ignore_status=True)
        if 'qemu' in output:
            return True
        else:
            return False

    def get_vf_num_by_id(self, vf_id):
        """
        Return corresponding pf eth name and vf num according to vf id.

        :param vf_id: vf id to check.
        :type vf_id: string
        :return: PF device name and vf num.
        :rtype: string
        """
        for pf in self.pf_vf_info:
            if vf_id in pf.get('vf_ids'):
                return pf['ethname'], pf["vf_ids"].index(vf_id)
        raise ValueError("Could not find vf id '%s' in '%s'" % (vf_id,
                                                                self.pf_vf_info))

    def get_pf_vf_info(self):
        """
        Get pf and vf related information in this host that match ``self.pf_filter_re``.

        for every pf it will create following information:

        pf_id:
            The id of the pf device.
        occupied:
            Whether the pf device assigned or not
        vf_ids:
            Id list of related vf in this pf.
        ethname:
            eth device name in host for this pf.

        :return: return a list contains pf vf information.
        :rtype: list of dict
        """

        base_dir = "/sys/bus/pci/devices"
        cmd = "lspci | awk '/%s/ {print $1}'" % self.pf_filter_re
        pf_ids = [i for i in utils.system_output(cmd).splitlines()]
        pf_vf_dict = []
        for pf_id in pf_ids:
            pf_info = {}
            vf_ids = []
            full_id = utils_misc.get_full_pci_id(pf_id)
            pf_info["pf_id"] = full_id
            pf_info["occupied"] = False
            d_link = os.path.join("/sys/bus/pci/devices", full_id)
            txt = utils.system_output("ls %s" % d_link)
            re_vfn = "(virtfn[0-9])"
            paths = re.findall(re_vfn, txt)
            for path in paths:
                f_path = os.path.join(d_link, path)
                vf_id = os.path.basename(os.path.realpath(f_path))
                vf_ids.append(vf_id)
            pf_info["vf_ids"] = vf_ids
            pf_vf_dict.append(pf_info)
        if_out = utils.system_output("ifconfig -a")
        re_ethname = "\w+(?=: flags)|eth[0-9](?=\s*Link)"
        ethnames = re.findall(re_ethname, if_out)
        for eth in ethnames:
            cmd = "ethtool -i %s | awk '/bus-info/ {print $2}'" % eth
            pci_id = utils.system_output(cmd)
            if not pci_id:
                continue
            for pf in pf_vf_dict:
                if pci_id in pf["pf_id"]:
                    pf["ethname"] = eth
        return pf_vf_dict

    def get_vf_devs(self):
        """
        Get all unused VFs PCI IDs.

        :return: List of all available PCI IDs for Virtual Functions.
        :rtype: List of string
        """
        vf_ids = []
        for pf in self.pf_vf_info:
            if pf["occupied"]:
                continue
            for vf_id in pf["vf_ids"]:
                if not self.is_binded_to_stub(vf_id):
                    vf_ids.append(vf_id)
        return vf_ids

    def get_pf_devs(self):
        """
        Get PFs PCI IDs requested by self.devices.
        It will try to get PF by device name.
        It will still return it, if device name you set already occupied.
        Please set unoccupied device name. If not sure, please just do not
        set device name. It will return unused PF list.

        :return: List with all PCI IDs for the physical hardware requested
        :rtype: List of string
        """
        pf_ids = []
        for device in self.devices:
            if device['type'] == 'pf':
                name = device.get('name', None)
                pf_id = self._get_pf_pci_id(name)
                if not pf_id:
                    continue
                pf_ids.append(pf_id)
        return pf_ids

    def get_devs(self, devices=None):
        """
        Get devices' PCI IDs according to parameters set in self.devices.

        :param devices: List of device dict that contain PF VF information.
        :type devices: List of dict
        :return: List of all available devices' PCI IDs
        :rtype: List of string
        """
        base_dir = "/sys/bus/pci"
        if not devices:
            devices = self.devices
        pf_ids = self.get_pf_devs()
        vf_ids = self.get_vf_devs()
        vf_ids.sort()
        dev_ids = []
        if isinstance(devices, dict):
            devices = [devices]
        for device in devices:
            d_type = device.get("type", "vf")
            if d_type == "vf":
                dev_id = vf_ids.pop(0)
                (ethname, vf_num) = self.get_vf_num_by_id(dev_id)
                set_mac_cmd = "ip link set dev %s vf %s mac %s " % (ethname,
                                                                    vf_num,
                                                                    device["mac"])
                utils.run(set_mac_cmd)

            elif d_type == "pf":
                dev_id = pf_ids.pop(0)
            dev_ids.append(dev_id)
            unbind_driver = os.path.realpath(os.path.join(base_dir,
                                                          "devices/%s/driver" % dev_id))
            self.dev_unbind_drivers[dev_id] = unbind_driver
        if len(dev_ids) != len(devices):
            logging.error("Did not get enough PCI Device")
        return dev_ids

    def get_vfs_count(self):
        """
        Get VFs count number according to lspci.
        """
        # FIXME: Need to think out a method of identify which
        # 'virtual function' belongs to which physical card considering
        # that if the host has more than one 82576 card. PCI_ID?
        cmd = "lspci | grep '%s' | wc -l" % self.vf_filter_re
        vf_num = int(utils.system_output(cmd, verbose=False))
        logging.info("Found %s vf in host", vf_num)
        return vf_num

    def get_same_group_devs(self, pci_id):
        """
        Get the device that in same iommu group.

        :param pci_id: Device's pci_id
        :type pci_id: string
        :return: Return the device's pci id that in same group with pci_id.
        :rtype: List of string.
        """
        pci_ids = []
        base_dir = "/sys/bus/pci/devices"
        devices_link = os.path.join(base_dir,
                                    "%s/iommu_group/devices/" % pci_id)
        out = utils.system_output("ls %s" % devices_link)

        if out:
            pci_ids = out.split()
        return pci_ids

    def check_vfs_count(self):
        """
        Check VFs count number according to the parameter driver_options.
        """
        # Network card 82576 has two network interfaces and each can be
        # virtualized up to 7 virtual functions, therefore we multiply
        # two for the value of driver_option 'max_vfs'.
        expected_count = int((re.findall("(\d)", self.driver_option)[0])) * 2
        return (self.get_vfs_count() == expected_count)

    def is_binded_to_stub(self, full_id):
        """
        Verify whether the device with full_id is already binded to driver.

        :param full_id: Full ID for the given PCI device
        :type full_id: String
        """
        base_dir = "/sys/bus/pci"
        stub_path = os.path.join(base_dir, "drivers/%s" % self.device_driver)
        if os.path.exists(os.path.join(stub_path, full_id)):
            return True
        return False

    @error.context_aware
    def sr_iov_setup(self):
        """
        Ensure the PCI device is working in sr_iov mode.

        Check if the PCI hardware device drive is loaded with the appropriate,
        parameters (number of VFs), and if it's not, perform setup.

        :return: True, if the setup was completed successfully, False otherwise.
        :rtype: bool
        """
        # Check if the host support interrupt remapping
        error.context("Set up host env for PCI assign test", logging.info)
        kvm_re_probe = True
        o = utils.system_output("dmesg")
        ecap = re.findall("ecap\s+(.\w+)", o)
        if not ecap:
            logging.error("Fail to check host interrupt remapping support.")
        else:
            if int(ecap[0], 16) & 8 == 8:
                # host support interrupt remapping.
                # No need enable allow_unsafe_assigned_interrupts.
                kvm_re_probe = False
            if self.kvm_params is not None:
                if self.auai_path and self.kvm_params[self.auai_path] == "Y":
                    kvm_re_probe = False
        # Try to re probe kvm module with interrupt remapping support
        if kvm_re_probe:
            cmd = "echo Y > %s" % self.auai_path
            error.context("enable PCI passthrough with '%s'" % cmd,
                          logging.info)
            try:
                utils.system(cmd)
            except Exception:
                logging.debug("Can not enable the interrupt remapping support")
        lnk = "/sys/module/vfio_iommu_type1/parameters/allow_unsafe_interrupts"
        if self.device_driver == "vfio-pci":
            status = utils.system('lsmod | grep vfio', ignore_status=True)
            if status:
                logging.info("Load vfio-pci module.")
                cmd = "modprobe vfio-pci"
                utils.run(cmd)
                time.sleep(3)
            if not ecap or (int(ecap[0], 16) & 8 != 8):
                cmd = "echo Y > %s" % lnk
                error.context("enable PCI passthrough with '%s'" % cmd,
                              logging.info)
                utils.run(cmd)
        re_probe = False
        status = utils.system("lsmod | grep %s" % self.driver,
                              ignore_status=True)
        if status:
            re_probe = True
        elif not self.check_vfs_count():
            utils.system_output("modprobe -r %s" % self.driver, timeout=60)
            re_probe = True
        else:
            self.setup = None
            return True

        # Re-probe driver with proper number of VFs
        if re_probe:
            cmd = "modprobe %s %s" % (self.driver, self.driver_option)
            error.context("Loading the driver '%s' with command '%s'" %
                          (self.driver, cmd), logging.info)
            status = utils.system(cmd, ignore_status=True)
            dmesg = utils.system_output("dmesg", timeout=60, ignore_status=True)
            file_name = "host_dmesg_after_load_%s.txt" % self.driver
            logging.info("Log dmesg after loading '%s' to '%s'.", self.driver,
                         file_name)
            utils_misc.log_line(file_name, dmesg)
            utils.system("/etc/init.d/network restart", ignore_status=True)
            if status:
                return False
            self.setup = None
            return True

    def sr_iov_cleanup(self):
        """
        Clean up the sriov setup

        Check if the PCI hardware device drive is loaded with the appropriate,
        parameters (none of VFs), and if it's not, perform cleanup.

        :return: True, if the setup was completed successfully, False otherwise.
        :rtype: bool
        """
        # Check if the host support interrupt remapping
        error.context("Clean up host env after PCI assign test", logging.info)
        kvm_re_probe = False
        if self.kvm_params is not None:
            for kvm_param, value in self.kvm_params.items():
                if open(kvm_param, "r").read().strip() != value:
                    cmd = "echo %s > %s" % (value, kvm_param)
                    logging.info("Write '%s' to '%s'", value, kvm_param)
                    try:
                        utils.system(cmd)
                    except Exception:
                        logging.error("Failed to write  '%s' to '%s'", value,
                                      kvm_param)

        re_probe = False
        status = utils.system('lsmod | grep %s' % self.driver,
                              ignore_status=True)
        if status:
            cmd = "modprobe -r %s" % self.driver
            logging.info("Running host command: %s" % cmd)
            utils.system_output(cmd, timeout=60)
            re_probe = True
        else:
            return True

        # Re-probe driver with proper number of VFs
        if re_probe:
            cmd = "modprobe %s" % self.driver
            msg = "Loading the driver '%s' without option" % self.driver
            error.context(msg, logging.info)
            status = utils.system(cmd, ignore_status=True)
            utils.system("/etc/init.d/network restart", ignore_status=True)
            if status:
                return False
            return True

    def request_devs(self, devices=None):
        """
        Implement setup process: unbind the PCI device and then bind it
        to the device driver.

        :param devices: List of device dict
        :type devices: List of dict
        :return: List of successfully requested devices' PCI IDs.
        :rtype: List of string
        """
        if not self.pf_vf_info:
            self.pf_vf_info = self.get_pf_vf_info()
        base_dir = "/sys/bus/pci"
        stub_path = os.path.join(base_dir, "drivers/%s" % self.device_driver)
        self.pci_ids = self.get_devs(devices)
        logging.info("The following pci_ids were found: %s", self.pci_ids)
        requested_pci_ids = []

        # Setup all devices specified for assignment to guest
        for p_id in self.pci_ids:
            if self.device_driver == "vfio-pci":
                pci_ids = self.get_same_group_devs(p_id)
                logging.info("Following devices are in same group: %s", pci_ids)
            else:
                pci_ids = [p_id]
            for pci_id in pci_ids:
                short_id = pci_id[5:]
                drv_path = os.path.join(base_dir, "devices/%s/driver" % pci_id)
                dev_prev_driver = os.path.realpath(os.path.join(drv_path,
                                                                os.readlink(drv_path)))
                self.dev_drivers[pci_id] = dev_prev_driver

                # Judge whether the device driver has been binded to stub
                if not self.is_binded_to_stub(pci_id):
                    error.context("Bind device %s to stub" % pci_id,
                                  logging.info)
                    vendor_id = utils_misc.get_vendor_from_pci_id(short_id)
                    stub_new_id = os.path.join(stub_path, 'new_id')
                    unbind_dev = os.path.join(drv_path, 'unbind')
                    stub_bind = os.path.join(stub_path, 'bind')

                    info_write_to_files = [(vendor_id, stub_new_id),
                                           (pci_id, unbind_dev),
                                           (pci_id, stub_bind)]

                    for content, f_name in info_write_to_files:
                        try:
                            logging.info("Write '%s' to file '%s'", content,
                                         f_name)
                            utils.open_write_close(f_name, content)
                        except IOError:
                            logging.debug("Failed to write %s to file %s",
                                          content, f_name)
                            continue

                    if not self.is_binded_to_stub(pci_id):
                        logging.error("Binding device %s to stub failed", pci_id)
                    continue
                else:
                    logging.debug("Device %s already binded to stub", pci_id)
            requested_pci_ids.append(p_id)
        return requested_pci_ids

    @error.context_aware
    def release_devs(self):
        """
        Release all PCI devices currently assigned to VMs back to the
        virtualization host.
        """
        try:
            for pci_id in self.dev_drivers:
                if not self._release_dev(pci_id):
                    logging.error(
                        "Failed to release device %s to host", pci_id)
                else:
                    logging.info("Released device %s successfully", pci_id)
            if self.cleanup:
                self.sr_iov_cleanup()
                self.devices = []
                self.devices_requested = 0
                self.dev_unbind_drivers = {}
        except Exception:
            return


class LibvirtPolkitConfig(object):

    """
    Enable polkit access driver for libvirtd and set polkit rules.

    For setting JavaScript polkit rule, using template of rule to satisify
    libvirt ACL API testing need, just replace keys in template.

    Create a non-privileged user 'testacl' for test if given
    'unprivileged_user' contains 'EXAMPLE', and delete the user at cleanup.

    Multiple rules could be add into one config file while action_id string
    is offered space seperated.

    e.g.
    action_id = "org.libvirt.api.domain.start org.libvirt.api.domain.write"

    then 2 actions "org.libvirt.api.domain.start" and
    "org.libvirt.api.domain.write" specified, which could be used to generate
    2 rules in one config file.
    """

    def __init__(self, params):
        """
        :param params: Dict like object containing parameters for the test.
        """
        self.libvirtd_path = "/etc/libvirt/libvirtd.conf"
        self.libvirtd_backup_path = "/etc/libvirt/libvirtd.conf.virttest.backup"
        self.polkit_rules_path = "/etc/polkit-1/rules.d/"
        self.polkit_rules_path += "500-libvirt-acl-virttest.rules"

        if params.get("action_id"):
            self.action_id = params.get("action_id").split()
        else:
            self.action_id = []
        self.user = params.get("unprivileged_user")
        if params.get("action_lookup"):
            # The action_lookup string should be seperated by space and
            # each seperated string should have ':' which represent key:value
            # for later use.
            self.attr = params.get("action_lookup").split()
        else:
            self.attr = []

    def file_replace_append(self, fpath, pat, repl):
        """
        Replace pattern in file with replacement str if pattern found in file,
        else append the replacement str to file.

        :param fpath: string, the file path
        :param pat: string, the pattern string
        :param repl: string, the string to replace
        """
        try:
            lines = open(fpath).readlines()
            if not any(re.search(pat, line) for line in lines):
                f = open(fpath, 'a')
                f.write(repl + '\n')
                f.close()
                return
            else:
                out_fpath = fpath + ".tmp"
                out = open(out_fpath, "w")
                for line in lines:
                    if re.search(pat, line):
                        out.write(repl + '\n')
                    else:
                        out.write(line)
                out.close()
                os.rename(out_fpath, fpath)
        except Exception:
            raise PolkitWriteLibvirtdConfigError("Failed to update file '%s'."
                                                 % fpath)

    def _setup_libvirtd(self):
        """
        Config libvirtd
        """
        # Backup libvirtd.conf
        shutil.copy(self.libvirtd_path, self.libvirtd_backup_path)

        # Set the API access control scheme
        access_str = "access_drivers = [ \"polkit\" ]"
        access_pat = "^ *access_drivers"
        self.file_replace_append(self.libvirtd_path, access_pat, access_str)

        # Set UNIX socket access controls
        sock_rw_str = "unix_sock_rw_perms = \"0777\""
        sock_rw_pat = "^ *unix_sock_rw_perms"
        self.file_replace_append(self.libvirtd_path, sock_rw_pat, sock_rw_str)

        # Set authentication mechanism
        auth_unix_str = "auth_unix_rw = \"none\""
        auth_unix_pat = "^ *auth_unix_rw"
        self.file_replace_append(self.libvirtd_path, auth_unix_pat,
                                 auth_unix_str)

    def _set_polkit_conf(self):
        """
        Set polkit libvirt ACL rule config file
        """
        # polkit template string
        template = "polkit.addRule(function(action, subject) {\n"
        template += "RULE"
        template += "});"

        # polkit rule template string
        rule = "    if (action.id == 'ACTION_ID'"
        rule += " && subject.user == 'USERNAME') {\n"
        rule += "HANDLE"
        rule += "    }\n"

        handle = "        if (ACTION_LOOKUP) {\n"
        handle += "            return polkit.Result.YES;\n"
        handle += "        } else {\n"
        handle += "            return polkit.Result.NO;\n"
        handle += "        }\n"

        action_str = "action.lookup('ATTR') == 'VAL'"

        try:
            # replace keys except 'ACTION_ID', these keys will remain same
            # as in different rules
            rule_tmp = rule.replace('USERNAME', self.user)

            # replace HANDLE part in rule
            action_opt = []
            if self.attr:
                for i in range(len(self.attr)):
                    attr_tmp = self.attr[i].split(':')
                    action_tmp = action_str.replace('ATTR', attr_tmp[0])
                    action_tmp = action_tmp.replace('VAL', attr_tmp[1])
                    action_opt.append(action_tmp)
                    if i > 0:
                        action_opt[i] = " && " + action_opt[i]

                action_tmp = ""
                for i in range(len(action_opt)):
                    action_tmp += action_opt[i]

                # replace ACTION_LOOKUP with string from self.attr
                handle_tmp = handle.replace('ACTION_LOOKUP', action_tmp)
                rule_tmp = rule_tmp.replace('HANDLE', handle_tmp)
            else:
                rule_tmp = rule_tmp.replace('HANDLE', "    ")

            # replace 'ACTION_ID' in loop and generate rules
            rules = ""
            for i in range(len(self.action_id)):
                rules += rule_tmp.replace('ACTION_ID', self.action_id[i])

            # repalce 'RULE' with rules in polkit template string
            self.template = template.replace('RULE', rules)
            logging.debug("The polkit config rule is:\n%s" % self.template)

            # write the config file
            utils.open_write_close(self.polkit_rules_path, self.template)
        except Exception:
            raise PolkitRulesSetupError("Set polkit rules file failed")

    def setup(self):
        """
        Enable polkit libvirt access driver and setup polkit ACL rules.
        """
        self._setup_libvirtd()
        # Use 'testacl' if unprivileged_user in cfg contains string 'EXAMPLE',
        # and if user 'testacl' is not exist on host, create it for test.
        if self.user.count('EXAMPLE'):
            cmd = "id testacl"
            if utils.system(cmd, ignore_status=True):
                logging.debug("Create new user 'testacl' on host.")
                cmd = "useradd testacl"
                utils.system(cmd, ignore_status=True)
            self.user = 'testacl'
        self._set_polkit_conf()

    def cleanup(self):
        """
        Cleanup polkit config
        """
        try:
            if os.path.exists(self.polkit_rules_path):
                os.unlink(self.polkit_rules_path)
            if os.path.exists(self.libvirtd_backup_path):
                os.rename(self.libvirtd_backup_path, self.libvirtd_path)
            if self.user.count('EXAMPLE'):
                logging.debug("Delete the created user 'testacl'.")
                cmd = "userdel -r testacl"
                utils.system(cmd, ignore_status=True)
        except Exception:
            raise PolkitConfigCleanupError("Failed to cleanup polkit config.")
