"""
Common spice test utility functions.

"""
import os
import logging
import time
import sys
from autotest.client.shared import error
from aexpect import ShellCmdError, ShellStatusError
from virttest import utils_net, utils_misc


class RVConnectError(Exception):

    """Exception raised in case that remote-viewer fails to connect"""
    pass


def _is_pid_alive(session, pid):

    try:
        session.cmd("ps -p %s" % pid)
    except ShellCmdError:
        return False

    return True


def wait_timeout(timeout=10):
    """
    time.sleep(timeout) + logging.debug(timeout)

    :param timeout=10
    """
    logging.debug("Waiting (timeout=%ss)", timeout)
    time.sleep(timeout)


def verify_established(client_vm, host, port, rv_binary,
                       tls_port=None, secure_channels=None):
    """
    Parses netstat output for established connection on host:port
    :param client_session - vm.wait_for_login()
    :param host - host ip addr
    :param port - port for client to connect
    :param rv_binary - remote-viewer binary
    """
    rv_binary = rv_binary.split(os.path.sep)[-1]

    client_session = client_vm.wait_for_login(timeout=60)
    tls_count = 0

    # !!! -n means do not resolve port names
    if ".exe" in rv_binary:
        cmd = "netstat -n"

    else:
        cmd = ('(netstat -pn 2>&1| grep "^tcp.*:.*%s.*ESTABLISHED.*%s.*")' %
               (host, rv_binary))
    netstat_out = client_session.cmd_output(cmd)
    logging.info("netstat output: %s", netstat_out)

    if tls_port:
        tls_count = netstat_out.count(tls_port)
    else:
        tls_port = port

    if (netstat_out.count(port) + tls_count) < 4:
        logging.error("Not enough channels were open")
        raise RVConnectError()
    if secure_channels:
        if tls_count < len(secure_channels.split(',')):
            logging.error("Not enough secure channels open")
            raise RVConnectError()
    for line in netstat_out.split('\n'):
        if ((port in line and "ESTABLISHED" not in line) or
                (tls_port in line and "ESTABLISHED" not in line)):
            logging.error("Failed to get established connection from netstat")
            raise RVConnectError()
    if "ESTABLISHED" not in netstat_out:
        logging.error("Failed to get established connection from netstat")
        raise RVConnectError()
    logging.info("%s connection to %s:%s successful.",
                 rv_binary, host, port)

    client_session.close()


def start_vdagent(guest_session, test_timeout):
    """
    Sending commands to start the spice-vdagentd service

    :param guest_session: ssh session of the VM
    :param test_timeout: timeout time for the cmds
    """
    cmd = "service spice-vdagentd start"
    try:
        guest_session.cmd(cmd, print_func=logging.info,
                          timeout=test_timeout)
    except ShellStatusError:
        logging.debug("Status code of \"%s\" was not obtained, most likely"
                      "due to a problem with colored output" % cmd)
    except:
        raise error.TestFail("Guest Vdagent Daemon Start failed")

    logging.debug("------------ End of guest checking for Spice Vdagent"
                  " Daemon ------------")
    wait_timeout(3)


def restart_vdagent(guest_session, test_timeout):
    """
    Sending commands to restart the spice-vdagentd service

    :param guest_session: ssh session of the VM
    :param test_timeout: timeout time for the cmds
    """
    cmd = "service spice-vdagentd restart"
    try:
        guest_session.cmd(cmd, print_func=logging.info,
                          timeout=test_timeout)
    except ShellCmdError:
        raise error.TestFail("Couldn't restart spice vdagent process")
    except:
        raise error.TestFail("Guest Vdagent Daemon Check failed")

    logging.debug("------------ End of Spice Vdagent"
                  " Daemon  Restart ------------")
    wait_timeout(3)


def stop_vdagent(guest_session, test_timeout):
    """
    Sending commands to stop the spice-vdagentd service

    :param guest_session: ssh session of the VM
    :param test_timeout: timeout time for the cmds
    """
    cmd = "service spice-vdagentd stop"
    try:
        guest_session.cmd(cmd, print_func=logging.info,
                          timeout=test_timeout)
    except ShellStatusError:
        logging.debug("Status code of \"%s\" was not obtained, most likely"
                      "due to a problem with colored output" % cmd)
    except ShellCmdError:
        raise error.TestFail("Couldn't turn off spice vdagent process")
    except:
        raise error.TestFail("Guest Vdagent Daemon Check failed")

    logging.debug("------------ End of guest checking for Spice Vdagent"
                  " Daemon ------------")
    wait_timeout(3)


def verify_vdagent(guest_session, test_timeout):
    """
    Verifying vdagent is installed on a VM

    :param guest_session: ssh session of the VM
    :param test_timeout: timeout time for the cmds
    """
    cmd = "rpm -qa | grep spice-vdagent"

    try:
        guest_session.cmd(cmd, print_func=logging.info, timeout=test_timeout)
    finally:
        logging.debug("----------- End of guest check to see if vdagent package"
                      " is available ------------")
    wait_timeout(3)


def get_vdagent_status(vm_session, test_timeout):
    """
    Return the status of vdagent
    :param vm_session:  ssh session of the VM
    :param test_timeout: timeout time for the cmd
    """
    output = ""
    cmd = "service spice-vdagentd status"

    wait_timeout(3)
    try:
        output = vm_session.cmd(
            cmd, print_func=logging.info, timeout=test_timeout)
    except ShellCmdError:
        # getting the status of vdagent stopped returns 3, which results in a
        # ShellCmdError
        return("stopped")
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise error.TestFail(
            "Failed attempting to get status of spice-vdagentd")
    wait_timeout(3)
    return(output)


def verify_virtio(guest_session, test_timeout):
    """
    Verify Virtio linux driver is properly loaded.

    :param guest_session: ssh session of the VM
    :param test_timeout: timeout time for the cmds
    """
    #cmd = "lsmod | grep virtio_console"
    cmd = "ls /dev/virtio-ports/"
    try:
        guest_session.cmd(cmd, print_func=logging.info, timeout=test_timeout)
    finally:
        logging.debug("------------ End of guest check of the Virtio-Serial"
                      " Driver------------")
    wait_timeout(3)


def install_rv_win(client, host_path, client_path='C:\\virt-viewer.msi'):
    """
    Install remote-viewer on a windows client

    :param client:      VM object
    :param host_path:   Location of installer on host
    :param client_path: Location of installer after copying
    """
    session = client.wait_for_login(
        timeout=int(client.params.get("login_timeout", 360)))
    client.copy_files_to(host_path, client_path)
    try:
        session.cmd_output(client_path + " /S")
    except:
        pass


def clear_interface(vm, login_timeout=360, timeout=5):
    """
    Clears user interface of a vm without restart

    :param vm:      VM where cleaning is required
    """
    logging.info("restarting X on: %s", vm.name)
    session = vm.wait_for_login(username="root", password="123456",
                                timeout=login_timeout)
    pid = session.cmd("pgrep Xorg")
    session.cmd("killall Xorg")

    utils_misc.wait_for(lambda: _is_pid_alive(session, pid), 10, timeout, 0.2)

    try:
        session.cmd("ps -C Xorg")
    except ShellCmdError:
        raise error.TestFail("X not running")


def deploy_epel_repo(guest_session, params):
    """
    Deploy epel repository to RHEL VM If It's RHEL6 or 5.

    :param guest_session - ssh session to guest VM
    :param params
    """

    # Check existence of epel repository
    try:
        guest_session.cmd("test -a /etc/yum.repos.d/epel.repo")
    except ShellCmdError:
        arch = guest_session.cmd("arch")
        if "i686" in arch:
            arch = "i386"
        else:
            arch = arch[:-1]
        if "release 5" in guest_session.cmd("cat /etc/redhat-release"):
            cmd = ("yum -y localinstall http://download.fedoraproject.org/"
                   "pub/epel/5/%s/epel-release-5-4.noarch.rpm 2>&1" % arch)
            logging.info("Installing epel repository to %s",
                         params.get("guest_vm"))
            guest_session.cmd(cmd, print_func=logging.info, timeout=90)
        elif "release 6" in guest_session.cmd("cat /etc/redhat-release"):
            cmd = ("yum -y localinstall http://download.fedoraproject.org/"
                   "pub/epel/6/%s/epel-release-6-8.noarch.rpm 2>&1" % arch)
            logging.info("Installing epel repository to %s",
                         params.get("guest_vm"))
            guest_session.cmd(cmd, print_func=logging.info, timeout=90)
        else:
            raise Exception("Unsupported RHEL guest")


def gen_rv_file(params, guest_vm, host_subj=None, cacert=None):
    """
    Generates vv file for remote-viewer

    :param params:          all parameters of the test
    :param guest_vm:        object of a guest VM
    :param host_subj:    subject of the host
    :param cacert:          location of certificate of host
    """
    full_screen = params.get("full_screen")
    proxy = params.get("spice_proxy")

    rv_file = open('rv_file.vv', 'w')
    rv_file.write("[virt-viewer]\n" +
                  "type=%s\n" % params.get("display") +
                  "host=%s\n" % utils_net.get_host_ip_address(params) +
                  "port=%s\n" % guest_vm.get_spice_var("spice_port"))

    ticket = params.get("spice_password")
    ticket_send = params.get("spice_password_send")
    qemu_ticket = params.get("qemu_password")
    if ticket_send:
        ticket = ticket_send
    if qemu_ticket:
        ticket = qemu_ticket
    rv_file.write("password=%s\n" % ticket)

    if guest_vm.get_spice_var("spice_ssl") == "yes":
        rv_file.write("tls-port=%s\n" %
                      guest_vm.get_spice_var("spice_tls_port"))
        rv_file.write("tls-ciphers=DEFAULT\n")
    if host_subj:
        rv_file.write("host-subject=%s\n" % host_subj)
    if cacert:
        cert = open(cacert)
        ca = cert.read()
        ca = ca.replace('\n', r'\n')
        rv_file.write("ca=%s\n" % ca)
    if full_screen == "yes":
        rv_file.write("fullscreen=1\n")
    if proxy:
        rv_file.write("proxy=%s\n" % proxy)
