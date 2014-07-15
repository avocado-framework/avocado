import logging
import re
import time
from avocado import aexpect
from avocado.utils import process
from avocado.utils import remote
from avocado.utils import misc
from avocado.utils import io

log = logging.getLogger("avocado.test")


class AddressCache(object):

    """
    Uses tcpdump to figure when a DHCP lease happened.

    As the leases happen, we can create a mapping MAC address <-> IP address.
    """

    def __init__(self, env):
        self.params = None
        self._env = env
        self._tcpdump = None
        self._tcpdump_log = 'tcpdump.log'
        self.mapping = self._env.data['address_cache']

    def _update(self, line):
        if re.search("Your.IP", line, re.IGNORECASE):
            matches = re.findall(r"\d*\.\d*\.\d*\.\d*", line)
            if matches:
                self.mapping["last_seen"] = matches[0]

        if re.search("Client.Ethernet.Address", line, re.IGNORECASE):
            matches = re.findall(r"\w*:\w*:\w*:\w*:\w*:\w*", line)
            if matches and self.mapping.get("last_seen"):
                mac_address = matches[0].lower()
                last_time = self.mapping.get("time_%s" %
                                             mac_address, 0)
                last_ip = self.mapping.get("last_seen")
                cached_ip = self.mapping.get(mac_address)

                if (time.time() - last_time > 5 or cached_ip != last_ip):
                    log.debug("(address cache) DHCP lease OK: %s --> %s",
                              mac_address,
                              self.mapping.get("last_seen"))

                self.mapping[mac_address] = self.mapping.get("last_seen")
                self.mapping["time_%s" % mac_address] = time.time()
                del self.mapping["last_seen"]
            elif matches:
                self.mapping["last_seen_mac"] = matches[0]

        if re.search("Requested.IP", line, re.IGNORECASE):
            matches = matches = re.findall(r"\d*\.\d*\.\d*\.\d*", line)
            if matches and self.mapping.get("last_seen_mac"):
                ip_address = matches[0]
                mac_address = self.mapping.get("last_seen_mac")
                last_time = self.mapping.get("time_%s" %
                                             mac_address, 0)

                if time.time() - last_time > 10:
                    log.debug("(address cache) DHCP lease OK: %s --> %s",
                              mac_address, ip_address)

                self.mapping[mac_address] = ip_address
                self.mapping["time_%s" % mac_address] = time.time()
                del self.mapping["last_seen_mac"]

        # ipv6 address cache:
        mac_ipv6_reg = r"client-ID.*?([0-9a-fA-F]{12})\).*IA_ADDR (.*) pltime"
        if re.search("dhcp6 (request|renew|confirm)", line, re.IGNORECASE):
            matches = re.search(mac_ipv6_reg, line, re.I)
            if matches:
                ipinfo = matches.groups()
                mac_address = ":".join(re.findall("..", ipinfo[0])).lower()
                request_ip = ipinfo[1].lower()
                log.debug("(address cache) DHCPV6 lease OK: %s --> %s",
                          mac_address, request_ip)
                self.mapping["%s_6" % mac_address] = request_ip

        if re.search("dhcp6 (reply|advertise)", line, re.IGNORECASE):
            ipv6_mac_reg = "IA_ADDR (.*) pltime.*client-ID.*?([0-9a-fA-F]{12})\)"
            matches = re.search(ipv6_mac_reg, line, re.I)
            if matches:
                ipinfo = matches.groups()
                mac_address = ":".join(re.findall("..", ipinfo[1])).lower()
                allocate_ip = ipinfo[0].lower()
                log.debug("(address cache) DHCPV6 lease OK: %s --> %s",
                          mac_address, allocate_ip)
                self.mapping["%s_6" % mac_address] = allocate_ip

    def _tcpdump_handler(self, line):
        """
        Handle tcpdump output.
    
        :params address_cache: address cache path.
        :params filename: Log file name for tcpdump message.
        :params line: Tcpdump output message.
        """
        try:
            io.log_line(self._tcpdump_log, line)
        except Exception, reason:
            log.warn("Can't log tcpdump output, '%s'", reason)

        self._update(line)

    def _start(self):
        port = self.params.get('shell_port')
        prompt = self.params.get('shell_prompt')
        address = self.params.get('ovirt_node_address')
        username = self.params.get('ovirt_node_user')
        password = self.params.get('ovirt_node_password')

        cmd_template = "%s -npvvvi any 'port 68 or port 546'"
        cmd = cmd_template % process.find_command("tcpdump")
        if self.params.get("remote_preprocess") == "yes":
            login_cmd = ("ssh -o UserKnownHostsFile=/dev/null "
                         "-o StrictHostKeyChecking=no "
                         "-o PreferredAuthentications=password -p %s %s@%s" %
                         (port, username, address))

            self._tcpdump = aexpect.ShellSession(login_cmd,
                                                 output_func=self.update,
                                                 output_params=(self,))

            remote.handle_prompts(self._tcpdump, username, password, prompt)
            self._tcpdump.sendline(cmd)

        else:
            self._tcpdump = aexpect.Tail(command=cmd,
                                         output_func=self._tcpdump_handler)

        if misc.wait_for(lambda: not self._tcpdump.is_alive(),
                         0.1, 0.1, 1.0):
            log.warn("Could not start tcpdump")
            log.warn("Status: %s", self._tcpdump.get_status())
            msg = misc.format_str_msg(self._tcpdump.get_output())
            log.warn("Output: %s", msg)

    def start(self, params=None):
        if params:
            self.params = params

        if "address_cache" not in self._env.data:
            self._env.data["address_cache"] = {}

        if self._tcpdump is None:
            self._start_tcpdump()
        else:
            if not self._tcpdump.is_alive():
                del self._tcpdump
                self._start_tcpdump()

    def stop(self):
        if self._tcpdump is not None:
            self._tcpdump.close()
            del self._tcpdump
            self._tcpdump = None
