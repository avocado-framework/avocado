"""
Configure network when interface name and
interface IP is available.
"""

from . import distro
from . import process


def set_ip(ipaddr, gateway, interface):
    """
    Gets IP, Interface name and gateway.

    :return: NA
    """
    if distro.detect().name == 'rhel':
        conf_file = "/etc/sysconfig/network-scripts/ifcfg-" + interface
        cmd = "mv %s %s.backup" % (conf_file, conf_file)
        process.system(cmd)
        with open(conf_file, "w") as network_conf:
            network_conf.write("TYPE=Ethernet \n")
            network_conf.write("BOOTPROTO=none \n")
            network_conf.write("NAME=%s \n" % interface)
            network_conf.write("DEVICE=%s \n" % interface)
            network_conf.write("ONBOOT=yes \n")
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % gateway)

        cmd = "ifup %s" % interface
        process.system(cmd)

    if distro.detect().name == 'SuSE':
        conf_file = "/etc/sysconfig/ifcfg-" + interface
        cmd = "mv %s %s.backup" % (conf_file, conf_file)
        process.system(cmd)
        with open(conf_file, "w") as network_conf:
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % gateway)

        cmd = "ifup %s" % interface
        process.system(cmd)


def unset_ip(interface):
    """
    Gets interface name unassigns the IP
    """
    conf_file = "/etc/sysconfig/network-scripts/ifcfg-" + interface
    cmd = "ifdown %s" % interface
    process.system(cmd)
    cmd = "mv %s.backup %s" % (conf_file, conf_file)
    process.system(cmd)
