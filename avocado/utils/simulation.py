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
# Copyright: Red Hat Inc. 2013-2014
# Author: Jan Scotka <jscotka@redhat.com>

"""
Module with simlation for various devices, network disc, etc
"""

import re
import logging
import time
import process

log = logging.getLogger('avocado.test')


class NetworkBridge(object):
    """
    Create network bridge device
    """

    def __init__(self, brname=None):
        """
        Creates network bridge device with name

        :param brname: name of bridge device
        """
        self.brname = brname
        self.devicelist = set()
        try:
            process.run("brctl --help", verbose=False)
        except:
            raise BaseException(
                "Unable to locate brdige-utils, please install them (yum install bridge-utils)")

        if self.brname and self.__checkifbridgeexist():
            log.debug("Bridge device ADD: " + self.brname)
            self.__createbridge()

    def getName(self):
        """
        Get bridge name

        :return: String
        """
        return self.brname

    def __listAllAttachedDevices(self):
        proc = process.run("sudo brctl show %s" % self.brname)
        out = [a.split("\t")[-1]
               for a in proc.stdout.split("\n")[1:] if len(a) > 0]
        return out

    def addDevice(self, device):
        """
        Add device to bridge explicitly

        :param device: String of device name
        :return: None
        """
        if device not in self.__listAllAttachedDevices():
            process.run("brctl addif %s %s" % (self.brname, device))
            log.debug("Bridge: ADD device %s to bridge %s" %
                      (device, self.brname))
        else:
            log.debug(
                "Bridge: already ADDed device %s to bridge %s" %
                (device, self.brname))
        self.devicelist.add(device)

    def delDevice(self, device):
        """
        Delete device to bridge explicitly

        :param device: String of device name
        :return: None
        """
        process.run("brctl delif %s %s" % (self.brname, device))
        log.debug("Bridge: DEL device %s from bridge %s" %
                  (device, self.brname))
        self.devicelist.discard(device)

    def clean(self):
        if self.brname and self.__checkifbridgeexist():
            dlcopy = self.devicelist.copy()
            for device in dlcopy:
                self.delDevice(device)
            log.debug("Bridge device DEL: " + self.brname)
            self.__delbridge()

    def __checkifbridgeexist(self):
        if self.brname:
            out = process.run("brctl show %s" % self.brname,
                              ignore_status=True, verbose=False)
            if "does not exist" not in out.stderr:
                return True
            else:
                return False
        else:
            return True

    def __createbridge(self):
        process.run("brctl addbr %s" % self.brname)
        process.run("brctl stp %s off" % self.brname)
        process.run("ip link set dev %s up" % self.brname)

    def __delbridge(self):
        try:
            process.run("ip link set dev %s down" % self.brname)
            process.run("brctl delbr %s" % self.brname)
        except process.CmdError as e:
            log.debug("already removed")


class SimulationNetwork(object):
    """
    Library to simulate network devices via dummy interface
    """

    def __init__(self, bridge=NetworkBridge()):
        """
        Create them inside network bridge if needed

        :param bridge:
        """
        try:
            process.run("modprobe dummy", verbose=False)
        except:
            raise BaseException("unable to load kernel module: dummy")
        self.bridge = bridge
        self.interfaces = set()

    def registerDeviceUp(self, device):
        process.run("ip link set dev {device} up".format(device=device))
        if self.bridge:
            self.bridge.addDevice(device)
        self.interfaces.add(device)

    def unregisterDeviceDown(self, device):
        if self.bridge:
            self.bridge.delDevice(device)
        process.run("ip link set dev {device} down".format(device=device))
        self.interfaces.discard(device)

    def isAdded(self, device):
        """
        Check if device is added to this object

        :param device:
        :return:
        """
        if device in self.interfaces:
            return True
        return False

    def addiface(self, device):
        """
        Create new network interface and add them to bridge if defined

        :param device:
        :return:
        """
        if not self.deviceExist(device):
            process.run("ip link add %s type dummy" % device)
        if not self.isAdded(device):
            self.registerDeviceUp(device)

    def deliface(self, device):
        """
        Delete device and unregister them from bridge

        :param device:
        :return:
        """
        if self.isAdded(device):
            self.unregisterDeviceDown(device)
            process.run("ip link del %s type dummy" % device)

    def clean(self):
        """
        Do explicit cleanup of all registered devices

        :return:
        """
        innner = self.interfaces.copy()
        for device in innner:
            self.deliface(device)

    def ifcfgGenerator(self, device, ipaddr, bootproto="none", staticpart=""):
        outfile = "/etc/sysconfig/network-scripts/ifcfg-%s" % device
        out = ""
        netmask = "24"
        if not staticpart:
            staticpart = """
NM_CONTROLLED ="yes"
ONBOOT ="no"
"""
        if re.search("([0-9]+\.[0-9]+\.[0-9]+\.[0-9])+/([0-9]+)", ipaddr):
            a = re.search("([0-9]+\.[0-9]+\.[0-9]+\.[0-9])+/([0-9]+)", ipaddr)
            ipaddr = a.groups()[1]
            netmask = a.groups()[2]
            log.debug("full IPv4 address specified")
        elif re.search("[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$", ipaddr):
            netmask = "24"
        out = """DEVICE={device}
IPADDR={ipaddr}
NETMASK={netmask}
BOOTPROTO={bootproto}
""".format(device=device, ipaddr=ipaddr, bootproto=bootproto, netmask=netmask) + staticpart
        with open(outfile, 'w') as ofile:
            ofile.write(out)

    def getValuesForDevice(self, device):
        return process.run(
            "ip a s dev {device}".format(device=device),
            ignore_status=True).stdout

    def deviceExist(self, device):
        proc = process.run(
            "ip a s dev {device}".format(device=device),
            ignore_status=True)
        if proc.exit_status == 0:
            return True
        else:
            return False


class SimulationNetworkVeth(SimulationNetwork):
    """
    Library to simulate network devices via virtual ethernet interface
    It provides full stack networking support.
    Best option for testing services binded to interfaces

    """

    def __init__(self, bridge=NetworkBridge()):
        """
        Create them inside network bridge if needed
        :param bridge:
        """
        try:
            process.run("modprobe veth", verbose=False)
        except:
            raise BaseException("unable to load kernel module: veth")
        self.bridge = bridge
        self.interfaces = set()

    def addiface(self, device):
        """
        Create new network interface and add them to bridge if defined

        :param device:
        :return:
        """
        if not self.deviceExist(device):
            process.run(
                "ip link add name {device}-br type veth peer name {device}".format(device=device))
            process.run("ip link set dev {device}-br up".format(device=device))
        if not (self.isAdded(device)):
            self.registerDeviceUp(device)

    def deliface(self, device):
        """
        Delete device and unregister them from bridge

        :param device:
        :return:
        """
        if self.isAdded(device):
            self.unregisterDeviceDown(device)
            process.run(
                "ip link set dev {device}-br down".format(device=device))
            process.run("ip link del {device}".format(device=device))


class SimulationNetworkTap(SimulationNetwork):
    """
    Library to simulate network devices via virtual ethernet interface
    It provides full stack networking support.
    Best option for testing services binded to interfaces

    """

    def __init__(self, bridge=NetworkBridge()):
        """
        Create them inside network bridge if needed
        :param bridge:
        """
        self.__util = None
        proc = process.run("ip tuntap s", ignore_status=True)
        if proc.exit_status == 0:
            self.__util = "ip tuntap"

        proc = process.run("locate tunctl", ignore_status=True)
        if not self.__util and proc.exit_status == 1:
            self.__util = "tunctl"
        if not self.__util:
            raise BaseException(
                "unable to use TAP network devices (missing tunctl utils or ip does not have support of tuntap subcommand)")
        self.bridge = bridge
        self.interfaces = set()

    def addiface(self, device):
        """
        Create new network interface and add them to bridge if defined

        :param device:
        :return:
        """
        if not self.deviceExist(device):
            if "tuntap" in self.__util:
                process.run(
                    "ip tuntap add dev {device} mode tap".format(
                        device=device))
            else:
                process.run("tunctl -t {device}".format(device=device))
        if not self.isAdded(device):
            self.registerDeviceUp(device)

    def deliface(self, device):
        """
        Delete device and unregister them from bridge

        :param device:
        :return:
        """
        if self.isAdded(device):
            self.unregisterDeviceDown(device)
            if "tuntap" in self.__util:
                process.run(
                    "ip tuntap del dev {device} mode tap".format(
                        device=device))
            else:
                process.run("tunctl -d {device}".format(device=device))
