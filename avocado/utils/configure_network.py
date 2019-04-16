"""
Configure network when interface name and
interface IP is available.
"""
import shutil

from . import distro
from . import process

def set_ip(ipaddr, netmask, interface):
    """
    Gets interface name, IP, subnetmask and creates interface
    file based on distro.
    """
    if distro.detect().name == 'rhel':
        conf_file = "/etc/sysconfig/network-scripts/ifcfg-" + interface
        shutil.move(conf_file, conf_file+".backup")
        with open(conf_file, "w") as network_conf:
            network_conf.write("TYPE=Ethernet \n")
            network_conf.write("BOOTPROTO=none \n")
            network_conf.write("NAME=%s \n" % interface)
            network_conf.write("DEVICE=%s \n" % interface)
            network_conf.write("ONBOOT=yes \n")
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % netmask)

        cmd = "ifup %s" % interface
        process.system(cmd)

    if distro.detect().name == 'SuSE':
        conf_file = "/etc/sysconfig/ifcfg-" + interface
        shutil.move(conf_file, conf_file+".backup")
        with open(conf_file, "w") as network_conf:
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % netmask)

        cmd = "ifup %s" % interface
        process.system(cmd)

def unset_ip(interface):
    """
    Gets interface name unassigns the IP to the interface
    """
    if distro.detect().name == 'rhel':
        conf_file = "/etc/sysconfig/network-scripts/ifcfg-" + interface

    if distro.detect().name == 'SuSE':
        conf_file = "/etc/sysconfig/ifcfg-" + interface

    cmd = "ifdown %s" % interface
    process.system(cmd)
    shutil.move(conf_file+".backup", conf_file)
