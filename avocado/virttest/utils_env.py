import cPickle
import UserDict
import os
import logging
import re
import time

import utils_misc
import virt_vm
import aexpect
import remote
import threading

ENV_VERSION = 1


def get_env_version():
    return ENV_VERSION


class EnvSaveError(Exception):
    pass


def lock_safe(function):
    """
    Get the environment safe lock, run the function, then release the lock.

    Unfortunately, it only works if the 1st argument of the function is an
    Env instance. This is mostly to save up code.

    :param function: Function to wrap.
    """
    def wrapper(*args, **kwargs):
        env = args[0]
        env.save_lock.acquire()
        try:
            return function(*args, **kwargs)
        finally:
            env.save_lock.release()
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    wrapper.__dict__.update(function.__dict__)
    return wrapper


@lock_safe
def _update_address_cache(env, line):
    if re.search("Your.IP", line, re.IGNORECASE):
        matches = re.findall(r"\d*\.\d*\.\d*\.\d*", line)
        if matches:
            env["address_cache"]["last_seen"] = matches[0]

    if re.search("Client.Ethernet.Address", line, re.IGNORECASE):
        matches = re.findall(r"\w*:\w*:\w*:\w*:\w*:\w*", line)
        if matches and env["address_cache"].get("last_seen"):
            mac_address = matches[0].lower()
            last_time = env["address_cache"].get("time_%s" % mac_address, 0)
            last_ip = env["address_cache"].get("last_seen")
            cached_ip = env["address_cache"].get(mac_address)

            if (time.time() - last_time > 5 or cached_ip != last_ip):
                logging.debug("(address cache) DHCP lease OK: %s --> %s",
                              mac_address, env["address_cache"].get("last_seen"))

            env["address_cache"][mac_address] = env["address_cache"].get("last_seen")
            env["address_cache"]["time_%s" % mac_address] = time.time()
            del env["address_cache"]["last_seen"]
        elif matches:
            env["address_cache"]["last_seen_mac"] = matches[0]

    if re.search("Requested.IP", line, re.IGNORECASE):
        matches = matches = re.findall(r"\d*\.\d*\.\d*\.\d*", line)
        if matches and env["address_cache"].get("last_seen_mac"):
            ip_address = matches[0]
            mac_address = env["address_cache"].get("last_seen_mac")
            last_time = env["address_cache"].get("time_%s" % mac_address, 0)

            if time.time() - last_time > 10:
                logging.debug("(address cache) DHCP lease OK: %s --> %s",
                              mac_address, ip_address)

            env["address_cache"][mac_address] = ip_address
            env["address_cache"]["time_%s" % mac_address] = time.time()
            del env["address_cache"]["last_seen_mac"]

    # ipv6 address cache:
    mac_ipv6_reg = r"client-ID.*?([0-9a-fA-F]{12})\).*IA_ADDR (.*) pltime"
    if re.search("dhcp6 (request|renew|confirm)", line, re.IGNORECASE):
        matches = re.search(mac_ipv6_reg, line, re.I)
        if matches:
            ipinfo = matches.groups()
            mac_address = ":".join(re.findall("..", ipinfo[0])).lower()
            request_ip = ipinfo[1].lower()
            logging.debug("(address cache) DHCPV6 lease OK: %s --> %s",
                          mac_address, request_ip)
            env["address_cache"]["%s_6" % mac_address] = request_ip

    if re.search("dhcp6 (reply|advertise)", line, re.IGNORECASE):
        ipv6_mac_reg = "IA_ADDR (.*) pltime.*client-ID.*?([0-9a-fA-F]{12})\)"
        matches = re.search(ipv6_mac_reg, line, re.I)
        if matches:
            ipinfo = matches.groups()
            mac_address = ":".join(re.findall("..", ipinfo[1])).lower()
            allocate_ip = ipinfo[0].lower()
            logging.debug("(address cache) DHCPV6 lease OK: %s --> %s",
                          mac_address, allocate_ip)
            env["address_cache"]["%s_6" % mac_address] = allocate_ip


def _tcpdump_handler(env, filename, line):
    """
    Helper for handler tcpdump output.

    :params address_cache: address cache path.
    :params filename: Log file name for tcpdump message.
    :params line: Tcpdump output message.
    """
    try:
        utils_misc.log_line(filename, line)
    except Exception, reason:
        logging.warn("Can't log tcpdump output, '%s'", reason)

    _update_address_cache(env, line)


class Env(UserDict.IterableUserDict):

    """
    A dict-like object containing global objects used by tests.
    """

    def __init__(self, filename=None, version=0):
        """
        Create an empty Env object or load an existing one from a file.

        If the version recorded in the file is lower than version, or if some
        error occurs during unpickling, or if filename is not supplied,
        create an empty Env object.

        :param filename: Path to an env file.
        :param version: Required env version (int).
        """
        UserDict.IterableUserDict.__init__(self)
        empty = {"version": version}
        self._filename = filename
        self._tcpdump = None
        self._params = None
        self.save_lock = threading.RLock()
        if filename:
            try:
                if os.path.isfile(filename):
                    f = open(filename, "r")
                    env = cPickle.load(f)
                    f.close()
                    if env.get("version", 0) >= version:
                        self.data = env
                    else:
                        logging.warn(
                            "Incompatible env file found. Not using it.")
                        self.data = empty
                else:
                    # No previous env file found, proceed...
                    logging.warn("Creating new, empty env file")
                    self.data = empty
            # Almost any exception can be raised during unpickling, so let's
            # catch them all
            except Exception, e:
                logging.warn("Exception thrown while loading env")
                logging.warn(e)
                logging.warn("Creating new, empty env file")
                self.data = empty
        else:
            logging.warn("Creating new, empty env file")
            self.data = empty

    def save(self, filename=None):
        """
        Pickle the contents of the Env object into a file.

        :param filename: Filename to pickle the dict into.  If not supplied,
                use the filename from which the dict was loaded.
        """
        filename = filename or self._filename
        if filename is None:
            raise EnvSaveError("No filename specified for this env file")
        self.save_lock.acquire()
        try:
            f = open(filename, "w")
            cPickle.dump(self.data, f)
            f.close()
        finally:
            self.save_lock.release()

    def get_all_vms(self):
        """
        Return a list of all VM objects in this Env object.
        """
        vm_list = []
        for key in self.data.keys():
            if key and key.startswith("vm__"):
                vm_list.append(self.data[key])
        return vm_list

    def clean_objects(self):
        """
        Destroy all objects registered in this Env object.
        """
        self.stop_tcpdump()
        for key in self.data:
            try:
                if key.startswith("vm__"):
                    self.data[key].destroy(gracefully=False)
            except Exception:
                pass
        self.data = {}

    def destroy(self):
        """
        Destroy all objects stored in Env and remove the backing file.
        """
        self.clean_objects()
        if self._filename is not None:
            if os.path.isfile(self._filename):
                os.unlink(self._filename)

    def get_vm(self, name):
        """
        Return a VM object by its name.

        :param name: VM name.
        """
        return self.data.get("vm__%s" % name)

    def create_vm(self, vm_type, target, name, params, bindir):
        """
        Create and register a VM in this Env object
        """
        vm_class = virt_vm.BaseVM.lookup_vm_class(vm_type, target)
        if vm_class is not None:
            vm = vm_class(name, params, bindir, self.get("address_cache"))
            self.register_vm(name, vm)
            return vm

    @lock_safe
    def register_vm(self, name, vm):
        """
        Register a VM in this Env object.

        :param name: VM name.
        :param vm: VM object.
        """
        self.data["vm__%s" % name] = vm

    @lock_safe
    def unregister_vm(self, name):
        """
        Remove a given VM.

        :param name: VM name.
        """
        del self.data["vm__%s" % name]

    @lock_safe
    def register_syncserver(self, port, server):
        """
        Register a Sync Server in this Env object.

        :param port: Sync Server port.
        :param server: Sync Server object.
        """
        self.data["sync__%s" % port] = server

    @lock_safe
    def unregister_syncserver(self, port):
        """
        Remove a given Sync Server.

        :param port: Sync Server port.
        """
        del self.data["sync__%s" % port]

    def get_syncserver(self, port):
        """
        Return a Sync Server object by its port.

        :param port: Sync Server port.
        """
        return self.data.get("sync__%s" % port)

    @lock_safe
    def register_lvmdev(self, name, lvmdev):
        """
        Register lvm device object into env;

        :param name: name of register lvmdev object
        :param lvmdev: lvmdev object;
        """
        self.data["lvmdev__%s" % name] = lvmdev

    @lock_safe
    def unregister_lvmdev(self, name):
        """
        Remove lvm device object from env;

        :param name: name of lvm device object;
        """
        del self.data["lvmdev__%s" % name]

    def get_lvmdev(self, name):
        """
        Get lvm device object by name from env;

        :param name: lvm device object name;
        :return: lvmdev object
        """
        return self.data.get("lvmdev__%s" % name)

    def _start_tcpdump(self):
        port = self._params.get('shell_port')
        prompt = self._params.get('shell_prompt')
        address = self._params.get('ovirt_node_address')
        username = self._params.get('ovirt_node_user')
        password = self._params.get('ovirt_node_password')

        cmd_template = "%s -npvvvi any 'port 68 or port 546'"
        cmd = cmd_template % utils_misc.find_command("tcpdump")
        if self._params.get("remote_preprocess") == "yes":
            login_cmd = ("ssh -o UserKnownHostsFile=/dev/null "
                         "-o StrictHostKeyChecking=no "
                         "-o PreferredAuthentications=password -p %s %s@%s" %
                         (port, username, address))

            self._tcpdump = aexpect.ShellSession(
                login_cmd,
                output_func=_update_address_cache,
                output_params=(self,))

            remote.handle_prompts(self._tcpdump, username, password, prompt)
            self._tcpdump.sendline(cmd)

        else:
            self._tcpdump = aexpect.Tail(command=cmd,
                                         output_func=_tcpdump_handler,
                                         output_params=(self, "tcpdump.log"))

        if utils_misc.wait_for(lambda: not self._tcpdump.is_alive(),
                               0.1, 0.1, 1.0):
            logging.warn("Could not start tcpdump")
            logging.warn("Status: %s", self._tcpdump.get_status())
            msg = utils_misc.format_str_for_message(self._tcpdump.get_output())
            logging.warn("Output: %s", msg)

    def start_tcpdump(self, params):
        self._params = params

        if "address_cache" not in self.data:
            self.data["address_cache"] = {}

        if self._tcpdump is None:
            self._start_tcpdump()
        else:
            if not self._tcpdump.is_alive():
                del self._tcpdump
                self._start_tcpdump()

    def stop_tcpdump(self):
        if self._tcpdump is not None:
            self._tcpdump.close()
            del self._tcpdump
            self._tcpdump = None
