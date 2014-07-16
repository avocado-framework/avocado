import os
import logging
import re
from autotest.client import utils
import remote
import aexpect
import data_dir


class NetperfError(Exception):
    pass


class NetperfPackageError(NetperfError):

    def __init__(self, error_info):
        NetperfError.__init__(self)
        self.error_info = error_info

    def __str__(self):
        e_msg = "Packeage Error: %s" % self.error_info
        return e_msg


class NetserverError(NetperfError):

    def __init__(self, error_info):
        NetperfError.__init__(self)
        self.error_info = error_info

    def __str__(self):
        e_msg = "%s" % self.error_info
        return e_msg


class NetperfTestError(NetperfError):

    def __init__(self, error_info):
        NetperfError.__init__(self)
        self.error_info = error_info

    def __str__(self):
        e_msg = "Netperf test error: %s" % self.error_info
        return e_msg


class NetperfPackage(remote.Remote_Package):

    def __init__(self, address, netperf_path, md5sum="", netperf_source="",
                 client="ssh", port="22", username="root", password="123456"):
        """
        Class NetperfPackage just represent the netperf package
        Init NetperfPackage class.

        :param address: Remote host or guest address
        :param netperf_path: Installed netperf path
        :param me5sum: Local netperf package me5sum
        :param netperf_source: source netperf (path or link) path
        :param client: The client to use ('ssh', 'telnet' or 'nc')
        :param port: Port to connect to
        :param username: Username (if required)
        :param password: Password (if required)
        """
        super(NetperfPackage, self).__init__(address, client, username,
                                             password, port, netperf_path)

        self.netperf_source = netperf_source
        self.pack_suffix = ""
        self.netperf_dir = None
        self.build_tool = False
        self.md5sum = md5sum
        self.netperf_base_dir = self.remote_path
        self.netperf_file = os.path.basename(self.netperf_source)

        if client == "nc":
            self.prompt = r"^\w:\\.*>\s*$"
            self.linesep = "\r\n"
        else:
            self.prompt = "^\[.*\][\#\$]\s*$"
            self.linesep = "\n"
            if self.netperf_source.endswith("tar.bz2"):
                self.pack_suffix = ".tar.bz2"
                self.decomp_cmd = "tar jxvf"
            elif self.netperf_source.endswith("tar.gz"):
                self.pack_suffix = ".tar.gz"
                self.decomp_cmd = "tar zxvf"
            self.netperf_dir = os.path.join(self.remote_path,
                                            self.netperf_file.rstrip(self.pack_suffix))

        if self.pack_suffix:
            self.netserver_path = os.path.join(self.netperf_dir,
                                               "src/netserver")
            self.netperf_path = os.path.join(self.netperf_dir,
                                             "src/netperf")
        else:
            self.netserver_path = os.path.join(self.netperf_base_dir,
                                               self.netperf_file)
            self.netperf_path = os.path.join(self.netperf_base_dir,
                                             self.netperf_file)

        logging.debug("Create remote session")
        self.session = remote.remote_login(self.client, self.address,
                                           self.port, self.username,
                                           self.password, self.prompt,
                                           self.linesep, timeout=360)

    def __del__(self):
        self.env_cleanup()

    def env_cleanup(self, clean_all=True):
        clean_cmd = ""
        if self.netperf_dir:
            clean_cmd = "rm -rf %s" % self.netperf_dir
        if clean_all:
            clean_cmd += " rm -rf %s" % os.path.join(self.remote_path,
                                                     self.netperf_file)
        self.session.cmd(clean_cmd, ignore_all_errors=True)

    def pack_compile(self, compile_option=""):
        pre_setup_cmd = "cd %s " % self.netperf_base_dir
        pre_setup_cmd += " && %s %s" % (self.decomp_cmd, self.netperf_file)
        pre_setup_cmd += " && cd %s " % self.netperf_dir
        setup_cmd = "./configure %s > /dev/null " % compile_option
        setup_cmd += " && make > /dev/null"
        self.env_cleanup(clean_all=False)
        cmd = "%s && %s " % (pre_setup_cmd, setup_cmd)
        try:
            self.session.cmd(cmd)
        except aexpect.ShellError, e:
            raise NetperfPackageError("Compile failed: %s" % e)

    def pull_file(self, netperf_source=None):
        """
        Copy file from remote to local.
        """

        if utils.is_url(netperf_source):
            logging.debug("Download URL file to local path")
            tmp_dir = data_dir.get_download_dir()
            self.netperf_source = utils.unmap_url_cache(tmp_dir, netperf_source,
                                                        self.md5sum)
        else:
            self.netperf_source = netperf_source
        return self.netperf_source

    def install(self, install, compile_option):
        cmd = "which netperf"
        try:
            status, netperf = self.session.cmd_status_output(cmd)
        except aexpect.ShellError:
            status = 1
        if not status:
            self.netperf_path = netperf.rstrip()
            cmd = "which netserver"
            self.netserver_path = self.session.cmd_output(cmd).rstrip()
            install = False
        if install:
            self.build_tool = True
            self.pull_file(self.netperf_source)
            self.push_file(self.netperf_source)
            if self.pack_suffix:
                logging.debug("Compiling netserver from source")
                self.pack_compile(compile_option)

        msg = "Using local netperf: %s and %s" % (self.netperf_path,
                                                  self.netserver_path)
        logging.debug(msg)
        return (self.netserver_path, self.netperf_path)


class Netperf(object):

    def __init__(self, address, netperf_path, md5sum="", netperf_source="",
                 client="ssh", port="22", username="root", password="redhat",
                 compile_option="--enable-demo=yes", install=True):
        """
        Init NetperfServer class.

        :param address: Remote host or guest address
        :param netperf_path: Remote netperf path
        :param me5sum: Local netperf package me5sum
        :param netperf_source: netperf source file (path or link) which will
                               transfer to remote
        :param client: The client to use ('ssh', 'telnet' or 'nc')
        :param port: Port to connect to
        :param username: Username (if required)
        :param password: Password (if required)
        """
        self.client = client
        if client == "nc":
            self.prompt = r"^\w:\\.*>\s*$"
            self.linesep = "\r\n"
        else:
            self.prompt = "^\[.*\][\#\$]\s*$"
            self.linesep = "\n"

        self.package = NetperfPackage(address, netperf_path, md5sum,
                                      netperf_source, client, port, username,
                                      password)
        self.netserver_path, self.netperf_path = self.package.install(install,
                                                                      compile_option)
        logging.debug("Create remote session")
        self.session = remote.remote_login(client, address, port, username,
                                           password, self.prompt,
                                           self.linesep, timeout=360)

    def is_target_running(self, target):
        if self.client == "nc":
            check_reg = re.compile(r"%s.*EXE" % target.upper(), re.I)
            if check_reg.findall(self.session.cmd_output("tasklist")):
                return True
        else:
            status_cmd = "pidof %s" % target
            if not self.session.cmd_status(status_cmd):
                return True
        return False

    def stop(self, target):
        if self.client == "nc":
            stop_cmd = "taskkill /F /IM %s*" % target
        else:
            stop_cmd = "killall %s" % target
        if self.is_target_running(target):
            self.session.cmd(stop_cmd, ignore_all_errors=True)
        if self.is_target_running(target):
            raise NetserverError("Cannot stop %s" % target)
        logging.info("Stop %s successfully" % target)


class NetperfServer(Netperf):

    def __init__(self, address, netperf_path, md5sum="", netperf_source="",
                 client="ssh", port="22", username="root", password="redhat",
                 compile_option="--enable-demo=yes", install=True):
        """
        Init NetperfServer class.

        :param address: Remote host or guest address
        :param netperf_path: Remote netperf path
        :param me5sum: Local netperf package me5sum
        :param netperf_source: Local netperf (path or link) with will transfer to
                           remote
        :param client: The client to use ('ssh', 'telnet' or 'nc')
        :param port: Port to connect to
        :param username: Username (if required)
        :param password: Password (if required)
        """
        super(NetperfServer, self).__init__(address, netperf_path, md5sum,
                                            netperf_source, client, port, username,
                                            password, compile_option, install)

    def start(self, restart=False):
        """
        Start/Restart netserver

        :param restart: if restart=True, will restart the netserver
        """

        logging.info("Start netserver ...")
        server_cmd = ""
        if self.client == "nc":
            server_cmd += "start /b %s" % self.netserver_path
        else:
            server_cmd = self.netserver_path

        if restart:
            self.stop()
        if not self.is_server_running():
            logging.info("Start netserver with cmd: '%s'" % server_cmd)
            self.session.cmd_output_safe(server_cmd)

        if not self.is_server_running():
            raise NetserverError("Can not start netperf server!")
        logging.info("Netserver start successfully")

    def is_server_running(self):
        return self.is_target_running("netserver")

    def stop(self):
        super(NetperfServer, self).stop("netserver")


class NetperfClient(Netperf):

    def __init__(self, address, netperf_path, md5sum="", netperf_source="",
                 client="ssh", port="22", username="root", password="redhat",
                 compile_option="", install=True):
        """
        Init NetperfClient class.

        :param address: Remote host or guest address
        :param netperf_path: Remote netperf path
        :param me5sum: Local netperf package me5sum
        :param netperf_source: Netperf source file (path or link) which will
                               transfer to remote
        :param client: The client to use ('ssh', 'telnet' or 'nc')
        :param port: Port to connect to
        :param username: Username (if required)
        :param password: Password (if required)
        """
        super(NetperfClient, self).__init__(address, netperf_path, md5sum,
                                            netperf_source, client, port, username,
                                            password, compile_option, install)

    def start(self, server_address, test_option="", timeout=1200,
              cmd_prefix=""):
        """
        Run netperf test

        :param server_address: Remote netserver address
        :param netperf_path: netperf test option (global/test option)
        :param timeout: Netperf test timeout(-l)
        :return: return test result
        """
        netperf_cmd = "%s %s -H %s %s " % (cmd_prefix, self.netperf_path,
                                           server_address, test_option)
        logging.debug("Start netperf with cmd: '%s'" % netperf_cmd)
        try:
            output = self.session.cmd_output_safe(netperf_cmd, timeout=timeout)
        except aexpect.ShellError, err:
            raise NetperfTestError("Run netperf error. %s" % str(err))
        self.result = output
        return self.result

    def bg_start(self, server_address, test_option="", session_num=1,
                 cmd_prefix=""):
        """
        Run netperf background, for stress test, Only support linux now
        Have no output

        :param server_address: Remote netserver address
        :param netperf_path: netperf test option (global/test option)
        :param timeout: Netperf test timeout(-l)
        """
        if self.client == "nc":
            netperf_cmd = "start /b %s %s -H %s %s " % (cmd_prefix,
                                                        self.netperf_path,
                                                        server_address,
                                                        test_option)
            logging.info("Start %s sessions netperf background with cmd: '%s'" %
                         (session_num, netperf_cmd))
            for num in xrange(int(session_num)):
                self.session.cmd_output_safe(netperf_cmd)
            return
        else:
            netperf_cmd = "%s %s -H %s %s " % (cmd_prefix, self.netperf_path,
                                               server_address, test_option)
            logging.debug("Start %s sessions netperf background with cmd: '%s'" %
                          (session_num, netperf_cmd))
            for num in xrange(int(session_num)):
                self.session.cmd_output_safe("%s &" % netperf_cmd)
            return

    def is_netperf_running(self):
        return self.is_target_running("netperf")

    def stop(self):
        super(NetperfClient, self).stop("netperf")
