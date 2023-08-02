# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
#
# Copyright: 2019-2020 IBM
# Copyright: 2019-2020 Red Hat Inc.
# Authors : Beraldo Leal <bleal@redhat.com>
#         : Praveen K Pandey <praveen@linux.vnet.ibm.com>
#         : Vaishnavi Bhat <vaishnavi@linux.vnet.ibm.com>

import json
import logging
import os
import re
import shutil
import subprocess
from ipaddress import IPv4Address, ip_interface

from avocado.utils import process
from avocado.utils.distro import detect as distro_detect
from avocado.utils.network.common import run_command
from avocado.utils.network.exceptions import NWException
from avocado.utils.wait import wait_for

LOG = logging.getLogger(__name__)


class NetworkInterface:
    """
    This class represents a network card interface (NIC).

    An "NetworkInterface" is attached to some host. This could be an instance
    of LocalHost or RemoteHost.  If a RemoteHost then all commands will be
    executed on a remote_session (host.remote_session). Otherwise will be
    executed locally.

    Here you will find a few methods to perform basic operations on a NIC.
    """

    def __init__(self, if_name, host, if_type="Ethernet"):
        self.name = if_name
        self.if_type = if_type
        self.host = host
        self.distro_is_rhel9 = False

    @property
    def config_filename(self):
        current_distro = distro_detect()
        if current_distro.name in ["rhel", "fedora"]:
            if self.distro_is_rhel9:
                path = "/etc/NetworkManager/system-connections"
            else:
                path = "/etc/sysconfig/network-scripts"
        elif current_distro.name == "SuSE":
            path = "/etc/sysconfig/network"
        else:
            msg = "Distro not supported by API. Could not get interface filename."
            raise NWException(msg)
        if self.distro_is_rhel9:
            return f"{path}/{self.name}.nmconnection"
        else:
            return f"{path}/ifcfg-{self.name}"

    @property
    def config_file_path(self):
        current_distro = distro_detect()
        if current_distro.name in ["rhel", "fedora"]:
            if self.distro_is_rhel9:
                return "/etc/NetworkManager/system-connections"
            else:
                return "/etc/sysconfig/network-scripts"
        elif current_distro.name == "SuSE":
            return "/etc/sysconfig/network"
        else:
            msg = "Distro not supported by API. Could not get interface filename."
            LOG.error(msg)

    @property
    def slave_config_filename(self):
        try:
            slave_dict = self._get_bondinterface_details()
            if self.distro_is_rhel9:
                return [
                    f"{self.config_file_path}/{slave}.nmconnection"
                    for slave in slave_dict["slaves"]
                ]
            else:
                return [
                    f"{self.config_file_path}/ifcfg-{slave}"
                    for slave in slave_dict["slaves"]
                ]
        except Exception:
            msg = "Slave config filename not available"
            LOG.debug(msg)
            return

    def _get_interface_details(self, version=None):
        cmd = f"ip -j link show {self.name}"
        if version:
            cmd = f"ip -{version} -j address show {self.name}"
        output = run_command(cmd, self.host)
        try:
            result = json.loads(output)
            for item in result:
                if item.get("ifname") == self.name:
                    return item
            raise NWException("Interface not found")
        except (NWException, json.JSONDecodeError):
            msg = f"Unable to get the details of interface {self.name}"
            LOG.error(msg)
            raise NWException(msg)

    def _get_bondinterface_details(self):
        cmd = (
            f"cat /sys/class/net/{self.name}/bonding/mode "
            f"/sys/class/net/{self.name}/bonding/slaves"
        )
        try:
            mode, slaves = run_command(cmd, self.host).splitlines()
            return {"mode": mode.split(), "slaves": slaves.split()}
        except Exception:
            raise NWException(f"Slave interface not found for " f"the bond {self.name}")

    def _move_file_to_backup(self, filename, ignore_missing=True):
        destination = f"{filename}.backup"
        if os.path.exists(filename):
            shutil.move(filename, destination)
        else:
            if not ignore_missing:
                raise NWException(f"{self.name} interface not available")

    def _write_to_file(self, filename, values):
        self._move_file_to_backup(filename)

        with open(filename, "w+") as fp:  # pylint: disable=W1514
            for key, value in values.items():
                fp.write(f"{key}={value}\n")

    def set_hwaddr(self, hwaddr):
        """Sets a Hardware Address (MAC Address) to the interface.

        This method will try to set a new hwaddr to this interface, if
        fails it will raise a NWException.

        You must have sudo permissions to run this method on a host.

        :param hwaddr: Hardware Address (Mac Address)
        """
        cmd = f"ip link set dev {self.name} address {hwaddr}"
        try:
            run_command(cmd, self.self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Adding hw address fails: {ex}")

    def add_ipaddr(self, ipaddr, netmask):
        """Add an IP Address (with netmask) to the interface.

        This method will try to add a new ipaddr/netmask this interface, if
        fails it will raise a NWException.

        You must have sudo permissions to run this method on a host.

        :param ipaddr: IP Address
        :param netmask: Network mask
        """

        ip = ip_interface(f"{ipaddr}/{netmask}")
        cmd = f"ip addr add {ip.compressed} dev {self.name}"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Failed to add address {ex}")

    @property
    def vlans(self):
        """Return all interface's VLAN.

        This is a dict were key is the VLAN number and the value is the name of
        the VLAN interface.

        rtype: dict
        """
        vlans = {}
        if not os.path.exists("/proc/net/vlan/config"):
            return vlans
        with open("/proc/net/vlan/config", encoding="utf-8") as vlan_config_file:
            for line in vlan_config_file:
                # entry is formatted as "vlan_name | vlan_id | parent_device"
                line = "".join(line.split())
                if line.endswith(self.name):
                    line = line.split("|")
                    vlans[line[1]] = line[0]
        return vlans

    def add_vlan_tag(self, vlan_num, vlan_name=None):
        """Configure 802.1Q VLAN tagging to the interface.

        This method will attempt to add a VLAN tag to this interface. If it
        fails, the method will raise a NWException.

        :param vlan_num: VLAN ID
        :param vlan_name: option to name VLAN interface, by default it is named
                          <interface_name>.<vlan_num>
        """

        vlan_name = vlan_name or f"{self.name}.{vlan_num}"
        cmd = (
            f"ip link add link {self.name} name {vlan_name} " f"type vlan id {vlan_num}"
        )
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Failed to add VLAN tag: {ex}")

    def remove_vlan_by_tag(self, vlan_num):
        """Remove the VLAN of the interface by tag number.

        This method will try to remove the VLAN tag of this interface. If it fails,
        the method will raise a NWException.

        :param vlan_num: VLAN ID
        :return: True or False, True if it found the VLAN interface and removed
                 it successfully, otherwise it will return False.
        """
        if str(vlan_num) in self.vlans:
            vlan_name = self.vlans[str(vlan_num)]
        else:
            return False
        cmd = f"ip link delete {vlan_name}"

        try:
            run_command(cmd, self.host, sudo=True)
            return True
        except Exception as ex:
            raise NWException(f"Failed to remove VLAN interface: {ex}")

    def remove_all_vlans(self):
        """Remove all VLANs of this interface.

        This method will remove all the VLAN interfaces associated by the
        interface. If it fails, the method will raise a NWException.
        """
        try:
            for v in self.vlans.values():
                cmd = f"ip link delete {v}"
                run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Failed to remove VLAN interface: {ex}")

    def bring_down(self):
        """Shutdown the interface.

        This will shutdown the interface link. Be careful, you might lost
        connection to the host.

        You must have sudo permissions to run this method on a host.
        """

        cmd = f"ip link set {self.name} down"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Failed to bring down: {ex}")

    def bring_up(self):
        """ "Wake-up the interface.

        This will wake-up the interface link.

        You must have sudo permissions to run this method on a host.
        """
        cmd = f"ip link set {self.name} up"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            raise NWException(f"Failed to bring up: {ex}")

    def is_admin_link_up(self):
        """Check the admin link state is up or not.

        :return: True or False, True if network interface state is 'UP'
                 otherwise will return False.
        """
        try:
            if "UP" in self._get_interface_details().get("flags"):
                return True
        except (NWException, IndexError):
            raise NWException("Could not get Administrative link state.")
        return False

    def is_operational_link_up(self):
        """Check Operational link state is up or not.

        :return: True or False. True if operational link state is LOWER_UP,
                 otherwise will return False.
        """
        try:
            if "LOWER_UP" in self._get_interface_details().get("flags"):
                return True
        except (NWException, IndexError):
            raise NWException("Could not get operational link state.")
        return False

    def is_link_up(self):
        """Check if the interface is up or not.

        :return: True or False. True if admin link state and operational
                 link state is up otherwise will return False.
        """
        return self.is_admin_link_up() and self.is_operational_link_up()

    def get_ipaddrs(self, version=4):
        """Get the IP addresses from a network interface.

        Interfaces can hold multiple IP addresses. This method will return a
        list with all addresses on this interface.

        :param version: Address Family Version (4 or 6). This must be a integer
                        and default is 4.
        :return: IP address as string.
        """
        if version not in [4, 6]:
            raise NWException(f"Version {version} not supported")

        try:
            details = self._get_interface_details(version)
            addr_info = details.get("addr_info")
            if addr_info:
                return [x.get("local") for x in addr_info]
        except (NWException, IndexError):
            msg = f"Could not get ip addresses for {self.name}"
            LOG.debug(msg)
            return []

    def get_hwaddr(self):
        """Get the Hardware Address (MAC) of this interface.

        This method will try to get the address and if fails it will raise a
        NWException.
        """
        cmd = f"cat /sys/class/net/{self.name}/address"
        try:
            return run_command(cmd, self.host)
        except Exception as ex:
            raise NWException(f"Failed to get hw address: {ex}")

    def get_mtu(self):
        """Return the current MTU value of this interface.

        This method will try to get the current MTU value, if fails will
        raise a NWException.
        """
        try:
            return self._get_interface_details().get("mtu")
        except (NWException, IndexError):
            raise NWException("Could not get MUT value.")

    def ping_check(self, peer_ip, count=2, options=None):
        """This method will try to ping a peer address (IPv4 or IPv6).

        You should provide a IPv4 or IPV6 that would like to ping. This
        method will try to ping the peer and if fails it will raise a
        NWException.

        :param peer_ip: Peer IP address (IPv4 or IPv6)
        :param count: How many packets to send. Default is 2
        :param options: ping command options. Default is None
        """
        cmd = f"ping -I {self.name} {peer_ip} -c {count}"
        if options is not None:
            cmd = f"{cmd} {options}"
        try:
            run_command(cmd, self.host)
        except Exception as ex:
            raise NWException(f"Failed to ping: {ex}")

    def save(self, ipaddr, netmask):
        """Save current interface IP Address to the system configuration file.

        If the ipaddr is valid (currently being used by the interface)
        this will try to save the current settings into /etc/. This
        check is necessary to avoid inconsistency. Before save, you
        should add_ipaddr, first.

        Currently, only RHEL, Fedora and SuSE are supported. And this
        will create a backup file of your current configuration if
        found.

        :param ipaddr : IP Address which need to configure for interface
        :param netmask: Network mask which is associated to the provided IP
        """
        if ipaddr not in self.get_ipaddrs():
            msg = (
                "ipaddr not configured on interface. To avoid "
                "inconsistency, please add the ipaddr first."
            )
            raise NWException(msg)

        current_distro = distro_detect()
        if current_distro.name == "rhel" and current_distro.version == "9":
            self.distro_is_rhel9 = "rhel9"

        filename = f"ifcfg-{self.name}"
        prefix = self.netmask_to_cidr(netmask)
        if current_distro.name in ["rhel", "fedora"]:
            if self.distro_is_rhel9:
                filename = f"{self.name}.nmconnection"
                path = "/etc/NetworkManager/system-connections"
            else:
                path = "/etc/sysconfig/network-scripts"
        elif current_distro.name == "SuSE":
            path = "/etc/sysconfig/network"
        else:
            msg = "Distro not supported by API. Could not save ipaddr."
            raise NWException(msg)

        if self.distro_is_rhel9:
            ifcfg_dict = ""
            if os.path.exists(f"{path}/{filename}") is False:
                run_command(
                    f"nmcli connection add con-name {self.name} ifname {self.name} type ethernet ipv4.address {ipaddr}/{prefix}",
                    self.host,
                )
            self._move_file_to_backup(f"{path}/{filename}")
            if os.path.exists(f"{path}/{filename}.backup"):
                destination = f"{path}/{filename}"
                shutil.copy(f"{path}/{filename}.backup", destination)
            run_command(
                f"nmcli c mod id {self.name} ipv4.method manual ipv4.address {ipaddr}/{prefix}",
                self.host,
            )
            run_command(f"nmcli connection up {self.name}", self.host)
        else:
            ifcfg_dict = {
                "TYPE": self.if_type,
                "BOOTPROTO": "static",
                "NAME": self.name,
                "DEVICE": self.name,
                "ONBOOT": "yes",
                "IPADDR": ipaddr,
                "NETMASK": netmask,
                "IPV6INIT": "yes",
                "IPV6_AUTOCONF": "yes",
                "IPV6_DEFROUTE": "yes",
            }
            if current_distro.name == "SuSE":
                ifcfg_dict = {
                    "IPADDR": f"{ipaddr}/{prefix}",
                    "BOOTPROTO": "static",
                    "STARTMODE": "auto",
                }
            self._write_to_file(f"{path}/{filename}", ifcfg_dict)

        if self.if_type == "Bond":
            bond_dict = self._get_bondinterface_details()
            if self.distro_is_rhel9:
                if os.path.exists(f"{path}/{filename}") is False:
                    run_command(
                        f"nmcli connection add con-name {self.name} ifname {self.name} type ethernet ipv4.address {ipaddr}/{prefix}",
                        self.host,
                    )
                self._move_file_to_backup(f"{path}/{filename}")
                if os.path.exists(f"{path}/{filename}.backup"):
                    destination = f"{path}/{filename}"
                    shutil.copy(f"{path}/{filename}.backup", destination)
                run_command(
                    f"nmcli c mod id {self.name} ipv4.method manual ipv4.address {ipaddr}/{prefix}",
                    self.host,
                )
                run_command(f"nmcli connection up {self.name}", self.host)
            else:
                ifcfg_dict["BONDING_MASTER"] = "yes"
                ifcfg_slave_dict = {
                    "SLAVE": "yes",
                    "ONBOOT": "yes",
                    "MASTER": self.name,
                }
                if current_distro.name == "SuSE":
                    ifcfg_dict["BONDING_MODULE_OPTS"] = "mode=" + bond_dict["mode"][0]
                    for index, slave in enumerate(bond_dict["slaves"]):
                        bonding_slave = f"BONDING_SLAVE{index}"
                        ifcfg_dict[bonding_slave] = slave
                        ifcfg_slave_dict.update({"NAME": slave, "DEVICE": slave})
                        self._write_to_file(f"{path}/ifcfg-{slave}", ifcfg_slave_dict)
                elif current_distro.name in ["rhel", "fedora"]:
                    ifcfg_dict["BONDING_OPTS"] = "mode=" + bond_dict["mode"][0]
                    for index, slave in enumerate(bond_dict["slaves"]):
                        ifcfg_slave_dict.update(
                            {"NAME": slave, "DEVICE": slave, "TYPE": "Ethernet"}
                        )
                        self._write_to_file(f"{path}/ifcfg-{slave}", ifcfg_slave_dict)
                else:
                    msg = "Distro not supported by API. Could not save ipaddr."
                    raise NWException(msg)

    def set_mtu(self, mtu, timeout=30):
        """Sets a new MTU value to this interface.

        This method will try to set a new MTU value to this interface,
        if fails it will raise a NWException. Also it will wait until
        the Interface is up before returning or until timeout be
        reached.

        You must have sudo permissions to run this method on a host.

        :param mtu:  mtu size that need to be set. This must be an int.
        :param timeout: how many seconds to wait until the interface is
                        up again. Default is 30.
        """
        cmd = f"ip link set {self.name} mtu {mtu}"
        run_command(cmd, self.host, sudo=True)
        wait_for(self.is_link_up, timeout=timeout)
        if int(mtu) != self.get_mtu():
            raise NWException("Failed to set MTU.")

    def remove_ipaddr(self, ipaddr, netmask):
        """Removes an IP address from this interface.

        This method will try to remove the address from this interface
        and if fails it will raise a NWException. Be careful, you can
        lost connection.

        You must have sudo permissions to run this method on a host.
        """
        ip = ip_interface(f"{ipaddr}/{netmask}")
        cmd = f"ip addr del {ip.compressed} dev {self.name}"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            msg = f"Failed to remove ipaddr. {ex}"
            raise NWException(msg)

    def flush_ipaddr(self):
        """Flush all the IP address for this interface.

        This method will try to flush the ip address from this interface
        and if fails it will raise a NWException. Be careful, you can
        lost connection.

        You must have sudo permissions to run this method on a host.
        """
        cmd = f"ip addr flush dev {self.name}"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            msg = f"Failed to flush ipaddr. {ex}"
            raise NWException(msg)

    def remove_link(self):
        """Deletes virtual interface link.

        This method will try to delete the virtual device link and the
        interface will no more be listed with 'ip a' and if fails it
        will raise a NWException. Be careful, you can lost connection.

        You must have sudo permissions to run this method on a host.
        """
        cmd = f"ip link del dev {self.name}"
        try:
            run_command(cmd, self.host, sudo=True)
        except Exception as ex:
            msg = f"Failed to delete link. {ex}"
            raise NWException(msg)

    def restore_from_backup(self):
        """Revert interface file from backup.

        This method checks if a backup version  is available for given
        interface then it copies backup file to interface file in /sysfs path.
        """

        backup_file = f"{self.config_filename}.backup"
        if os.path.exists(backup_file):
            shutil.move(backup_file, self.config_filename)
        else:
            raise NWException("Backup file not available, could not restore file.")

    def is_available(self):
        """Check if interface is available.

        This method checks if the interface is available.

        rtype: bool
        """
        cmd = f"ip link show dev {self.name}"
        try:
            run_command(cmd, self.host)
            return True
        except Exception as ex:
            msg = f"Interface {self.name} is not available. {ex}"
            LOG.debug(msg)
            return False

    def is_bond(self):
        """Check if interface is a bonding device.

        This method checks if the interface is a bonding device or not.

        rtype: bool
        """
        cmd = f"cat /proc/net/bonding/{self.name}"
        try:
            run_command(cmd, self.host)
            return True
        except Exception as ex:
            msg = f"{self.name} is not a bond device. {ex}"
            LOG.debug(msg)
            return False

    def is_veth(self):
        """Check if interface is a Virtual Ethernet.

        This method checks if the interface is a Virtual Ethernet or not.

        rtype: bool
        """
        if not os.path.isfile(f"/sys/class/net/{self.name}/device/devspec"):
            raise NWException("Network interface sysfs file does not exists")
        cmd = f"cat /sys/class/net/{self.name}/device/devspec"
        output = run_command(cmd, self.host)
        if "l-lan" in output:
            return True
        return False

    def is_vnic(self):
        """Check if interface is a virtual network.

        This method checks if the interface is a virtual NIC or not.

        rtype: bool
        """
        if not os.path.isfile(f"/sys/class/net/{self.name}/device/devspec"):
            raise NWException("Network interface sysfs file does not exists")
        cmd = f"cat /sys/class/net/{self.name}/device/devspec"
        output = run_command(cmd, self.host)
        if "vnic" in output:
            return True
        return False

    def is_sriov(self):
        """Check if interface is a SRIOV virtual interface.

        This method checks if the interface is SRIOV logical interface or not.

        rtype: bool
        """
        if not os.path.isfile(f"/sys/class/net/{self.name}/device/vpd"):
            raise NWException("Network interface sysfs file does not exists")
        cmd = f"cat /sys/class/net/{self.name}/device/vpd"
        output = run_command(cmd, self.host)
        for vpd in output.split():
            if "VF" in vpd and vpd.endswith("SN"):
                return True
        return False

    def remove_cfg_file(self):
        """
        Remove any config files that is created as a part of the test
        """
        if os.path.isfile(self.config_filename):
            os.remove(self.config_filename)

    def restore_slave_cfg_file(self):
        """
        Restore or delete slave config files.
        """
        if self.if_type != "Bond":
            return
        for slave_config in self.slave_config_filename:
            backup_slave_config = f"{slave_config}.backup"
            try:
                if os.path.exists(backup_slave_config):
                    shutil.move(backup_slave_config, slave_config)
                else:
                    os.remove(slave_config)
            except Exception as ex:
                raise NWException(f"Could not restore the config file {ex}")

    def are_packets_lost(self, peer_ip, options=None, sudo=False):
        """Check packet loss that occurs during ping.

        Function returns True for 0% packet loss and False
        if packet loss occurs.

        :param peer_ip: Peer IP address (IPv4 or IPv6)
        :param options: Type is List. Options such as -c, -f. Default is None
        :param sudo: If sudo permissions are needed. Default is False
        """
        cmd = f"ping -I {self.name} {peer_ip}"
        cmd = f"{cmd} "
        if options is not None:
            for elem in options:
                cmd += f"{elem} "
        try:
            output = run_command(cmd, self.host, sudo=sudo)
            if "0% packet loss" not in output:
                return False
            return True
        except Exception as ex:
            msg = f"Failed to ping. {ex}"
            raise NWException(msg)

    def netmask_to_cidr(self, netmask):
        """Function is used to check the netmask value and convert

        it into short form (mask) of netmask values
        Example : 255.255.255.0 = 24
        255.255.252.0 = 22

        :param netmask: Netmask value example 255.255.255.0
        :return : Returns mask value of given netmask
        """
        return sum(bin(int(bits)).count("1") for bits in netmask.split("."))

    def validate_ipv4_format(self, ip):
        """
        This function validates IPv4 address with following format set.

        1. A string in decimal-dot notation, consisting of four decimal
           integers in the inclusive range 0-255,separated by dots
           (e.g- 192.168.0.1).Each integer represents an octet in the address.
        2. An integer that fits into 32 bits.
        3. An integer packed into a bytes object of length 4.

        And for IP address which are not met above conditions,
        raises AddressValueError and returns False.

        :param ip: IP address
        :type pattern: str
        :return: True when IP address pattern/format matches if not
                 return False
        :rtype: boolean
        """
        try:
            IPv4Address(ip)
        except Exception as ex:
            LOG.debug("Failed to validate IP format %s", ex)
            return False
        return True

    def validate_ipv4_netmask_format(self, netmask):
        """
        This function validates IPv4 Netmask address with following format set.

        1. A string in decimal-dot notation,consisting of four decimal integers
           starting from 255 and octets separated by dots (e.g 255.255.255.0)
        2. An integer packed into a bytes object of length 4

        And for Netmask which are not met above conditions,
        [ eg : 255.0.255.0, 255.255.255, 255.255.255.256, 255.255.255.255.0]
        returns False.

        :param netmask: netmask address
        :type pattern: str
        :return: True when netmask address pattern/format matches if not
                 return False
        :rtype: boolean
        """
        netmask_list = netmask.split(".")
        if len(netmask_list) != 4:
            return False
        for octet in netmask_list:
            num = int(octet)
            if not 0 <= num <= 255:
                return False
        octet_bin = [format(int(i), "08b") for i in netmask_list]
        binary_netmask = ("").join(octet_bin)
        accept_zero_only = False
        first_bit = True
        for symbol in binary_netmask:
            if accept_zero_only and symbol == "1":
                return False
            elif symbol == "0":
                accept_zero_only = True
            if first_bit and symbol == "0":
                return False
            first_bit = False
        return True

    def ping_flood(self, int_name, peer_ip, ping_count):
        """
        Function to start ping to remote machine with "-f" [ flood ] option,
        on given interface.

        Also this function enables to track the live data to determine the
        ping flood failure, in case of failure the program will exit.

        :param int_name: source interface name.
        :param peer_ip: Peer IP address (IPv4 or IPv6)
        :param ping_count: How many ICMP echo packets to send.
        :return : returns True on successful ping flood.
                  returns False on ping flood failure.
        :rtype : boolean
        """
        cmd = f"ping -I {int_name} {peer_ip} -c {ping_count} -f "
        ping_process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        pattern = r"\.{10}"
        while True:
            char = ping_process.stdout.read(100)
            match = re.search(pattern, char)
            if match:
                ping_process.terminate()
                msg = "ping flood failed to remote machine, Please check the logs"
                LOG.debug(msg)
                return False
            return True
        ping_process.stdout.close()
        ping_process.wait()

    def get_device_IPI_name(self):
        """
        Function to convert IO device name to device_ipi names according to
        "/proc/interrupts" context.
        Ex: vnic@30000009 to vnic-30000009

        :return : A converted Network device according to device_ipi name.
        :rtype : string
        """

        if self.is_vnic():
            cmd = (
                f"cat /sys/class/net/{self.name}/device/devspec | "
                f"awk -F/ '{{print $3}}'"
            )
            interface_type = process.run(cmd, shell=True, ignore_status=True).decode(
                "utf-8"
            )
            cmd = f"echo {interface_type} | sed 's/@/-/' "
            interface_type = process.system_output(
                cmd, shell=True, ignore_status=True
            ).decode("utf-8")
            return interface_type
        elif self.is_veth():
            return self.name
