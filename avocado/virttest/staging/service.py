#  Copyright(c) 2013 Intel Corporation.
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms and conditions of the GNU General Public License,
#  version 2, as published by the Free Software Foundation.
#
#  This program is distributed in the hope it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin St - Fifth Floor, Boston, MA 02110-1301 USA.
#
#  The full GNU General Public License is included in this distribution in
#  the file called "COPYING".

import os
import re
import logging

from autotest.client.shared import error
from tempfile import mktemp
from autotest.client import utils


_COMMAND_TABLE_DOC = """

Taken from http://fedoraproject.org/wiki/SysVinit_to_Systemd_Cheatsheet

service frobozz start
systemctl start frobozz.service
 Used to start a service (not reboot persistent)

service frobozz stop
systemctl stop frobozz.service
 Used to stop a service (not reboot persistent)

service frobozz restart
systemctl restart frobozz.service
 Used to stop and then start a service

service frobozz reload
systemctl reload frobozz.service
 When supported, reloads the config file without interrupting pending operations.

service frobozz condrestart
systemctl condrestart frobozz.service
 Restarts if the service is already running.

service frobozz status
systemctl status frobozz.service
 Tells whether a service is currently running.

ls /etc/rc.d/init.d/
systemctl list-unit-files --type=service (preferred)
 Used to list the services that can be started or stopped
ls /lib/systemd/system/*.service /etc/systemd/system/*.service
 Used to list all the services and other units

chkconfig frobozz on
systemctl enable frobozz.service
 Turn the service on, for start at next boot, or other trigger.

chkconfig frobozz off
systemctl disable frobozz.service
 Turn the service off for the next reboot, or any other trigger.

chkconfig frobozz
systemctl is-enabled frobozz.service
 Used to check whether a service is configured to start or not in the current environment.

chkconfig --list
systemctl list-unit-files --type=service(preferred)
ls /etc/systemd/system/*.wants/
 Print a table of services that lists which runlevels each is configured on or off

chkconfig frobozz --list
ls /etc/systemd/system/*.wants/frobozz.service
 Used to list what levels this service is configured on or off

chkconfig frobozz --add
systemctl daemon-reload
 Used when you create a new service file or modify any configuration


"""


def sys_v_init_result_parser(command):
    """
    Parse results from sys_v style commands.

    Valid commands:
        status:
            return true if service is running.
        is_enabled:
            return true if service is enabled.
        list:
            return a dict from service name to status.
        others:
            return true if operate success.

    :param command: command.
    :type command: str.
    :return: different from the command.
    """
    if command == "status":
        def method(cmdResult):
            """
            Parse method for service XXX status.

            Returns True if XXX is running.
            Returns False if XXX is stopped.
            Returns None if XXX is unrecognized.
            """
            # If service is stopped, exit_status is also not zero.
            # So, we can't use exit_status to check result.
            output = cmdResult.stdout.lower()
            # Returns None if XXX is unrecognized.
            if re.search(r"unrecognized", output):
                return None
            # Returns False if XXX is stopped.
            dead_flags = [r"stopped", r"not running", r"dead"]
            for flag in dead_flags:
                if re.search(flag, output):
                    return False
            # If output does not contain a dead flag, check it with "running".
            return bool(re.search(r"running", output))
        return method
    elif command == "list":
        def method(cmdResult):
            """
            Parse method for service XXX list.

            Return dict from service name to status.

            e.g:
                {"sshd": {0: 'off', 1: 'off', 2: 'off', 3: 'off', 4: 'off', 5: 'off', 6: 'off'},
                 "vsftpd": {0: 'off', 1: 'off', 2: 'off', 3: 'off', 4: 'off', 5: 'off', 6: 'off'},
                 "xinetd": {'discard-dgram:': 'off', 'rsync:': 'off'...'chargen-stream:': 'off'},
                 ...
                 }
            """
            if cmdResult.exit_status:
                raise error.CmdError(cmdResult.command, cmdResult)
            # The final dict to return.
            _service2statusOnTarget_dict = {}
            # Dict to store status on every target for each service.
            _status_on_target = {}
            # Dict to store the status for service based on xinetd.
            _service2statusOnXinet_dict = {}
            lines = cmdResult.stdout.strip().splitlines()
            for line in lines:
                sublines = line.strip().split()
                if len(sublines) == 8:
                    # Service and status on each target.
                    service_name = sublines[0]
                    # Store the status of each target in _status_on_target.
                    for target in range(7):
                        status = sublines[target + 1].split(":")[-1]
                        _status_on_target[target] = status
                    _service2statusOnTarget_dict[
                        service_name] = _status_on_target.copy()

                elif len(sublines) == 2:
                    # Service based on xinetd.
                    service_name = sublines[0].strip(":")
                    status = sublines[-1]
                    _service2statusOnXinet_dict[service_name] = status

                else:
                    # Header or some lines useless.
                    continue
            # Add xinetd based service in the main dict.
            _service2statusOnTarget_dict[
                "xinetd"] = _service2statusOnXinet_dict
            return _service2statusOnTarget_dict
        return method
    else:
        return _ServiceResultParser.default_method


def systemd_result_parser(command):
    """
    Parse results from systemd style commands.

    Valid commands:
        status:
            return true if service is running.
        is_enabled:
            return true if service is enabled.
        list:
            return a dict from service name to status.
        others:
            return true if operate success.

    :param command: command.
    :type command: str.
    :return: different from the command.
    """
    if command == "status":
        def method(cmdResult):
            """
            Parse method for systemctl status XXX.service.

            Returns True if XXX.service is running.
            Returns False if XXX.service is stopped.
            Returns None if XXX.service is not loaded.
            """
            # If service is stopped, exit_status is also not zero.
            # So, we can't use exit_status to check result.
            output = cmdResult.stdout
            # Returns None if XXX is not loaded.
            if not re.search(r"Loaded: loaded", output):
                return None
            # Check it with Active status.
            return (output.count("Active: active") > 0)
        return method
    elif command == "list":
        def method(cmdResult):
            """
            Parse method for systemctl list XXX.service.

            Return a dict from service name to status.

            e.g:
                {"sshd": "enabled",
                 "vsftpd": "disabled",
                 "systemd-sysctl": "static",
                 ...
                 }
            """
            if cmdResult.exit_status:
                raise error.CmdError(cmdResult.command, cmdResult)
            # Dict to store service name to status.
            _service2status_dict = {}
            lines = cmdResult.stdout.strip().splitlines()
            for line in lines:
                sublines = line.strip().split()
                if (not len(sublines) == 2) or (not sublines[0].endswith("service")):
                    # Some lines useless.
                    continue
                service_name = sublines[0].rstrip(".service")
                status = sublines[-1]
                _service2status_dict[service_name] = status
            return _service2status_dict
        return method
    else:
        return _ServiceResultParser.default_method


def sys_v_init_command_generator(command):
    """
    Generate lists of command arguments for sys_v style inits.

    :param command: start,stop,restart, etc.
    :type command: str
    :return: list of commands to pass to utils.run or similar function
    :rtype: list
    """
    command_name = "service"
    if command == "is_enabled":
        command_name = "chkconfig"
        command = ""
    elif command == 'enable':
        command_name = "chkconfig"
        command = "on"
    elif command == 'disable':
        command_name = "chkconfig"
        command = "off"
    elif command == 'list':
        # noinspection PyUnusedLocal
        def list_command(service_name):
            return ["chkconfig", "--list"]
        return list_command
    elif command == "set_target":
        def set_target_command(target):
            target = convert_systemd_target_to_runlevel(target)
            return ["telinit", target]
        return set_target_command

    def method(service_name):
        return [command_name, service_name, command]
    return method


def systemd_command_generator(command):
    """
    Generate list of command line argument strings for systemctl.
    One argument per string for compatibility Popen

    WARNING: If systemctl detects that it is running on a tty it will use color,
    pipe to $PAGER, change column sizes and not truncate unit names.
    Use --no-pager to suppress pager output, or set PAGER=cat in the environment.
    You may need to take other steps to suppress color output.
    See https://bugzilla.redhat.com/show_bug.cgi?id=713567

    :param command: start,stop,restart, etc.
    :type command: str
    :return: list of command and arguments to pass to utils.run or similar functions
    :rtype: list
    """
    command_name = "systemctl"
    if command == "is_enabled":
        command = "is-enabled"
    elif command == "list":
        # noinspection PyUnusedLocal
        def list_command(service_name):
            # systemctl pipes to `less` or $PAGER by default. Workaround this
            # add '--full' to avoid systemctl truncates service names.
            return [command_name, "list-unit-files",
                    "--type=service", "--no-pager", "--full"]
        return list_command
    elif command == "set_target":
        def set_target_command(target):
            return [command_name, "isolate", target]
        return set_target_command

    def method(service_name):
        return [command_name, command, "%s.service" % service_name]
    return method


COMMANDS = (
    "start",
    "stop",
    "reload",
    "restart",
    "condrestart",
    "status",
    "enable",
    "disable",
    "is_enabled",
    "list",
    "set_target",
)


class _ServiceResultParser(object):

    """
    A class that contains staticmethods to parse the result of service command.
    """

    def __init__(self, result_parser, command_list=COMMANDS):
        """
            Create staticmethods for each command in command_list using setattr and the
            result_parser

            :param result_parser: function that generates functions that parse the result of command.
            :type result_parser: function
            :param command_list: list of all the commands, e.g. start, stop, restart, etc.
            :type command_list: list
        """
        self.commands = command_list
        for command in self.commands:
            setattr(self, command, result_parser(command))

    @staticmethod
    def default_method(cmdResult):
        """
        Default method to parse result from command which is not 'list' nor 'status'.

        Returns True if command was executed successfully.
        """
        if cmdResult.exit_status:
            logging.debug(cmdResult)
            return False
        else:
            return True


class _ServiceCommandGenerator(object):

    """
    A class that contains staticmethods that generate partial functions that
    generate command lists for starting/stopping services.
    """

    def __init__(self, command_generator, command_list=COMMANDS):
        """
            Create staticmethods for each command in command_list using setattr and the
            command_generator

            :param command_generator: function that generates functions that generate lists of command strings
            :type command_generator: function
            :param command_list: list of all the commands, e.g. start, stop, restart, etc.
            :type command_list: list
        """
        self.commands = command_list
        for command in self.commands:
            setattr(self, command, command_generator(command))


class _SpecificServiceManager(object):

    def __init__(self, service_name, service_command_generator, service_result_parser, run=utils.run):
        """
        Create staticmethods that call utils.run with the given service_name
        for each command in service_command_generator.

        lldpad = SpecificServiceManager("lldpad",
                                        auto_create_specific_service_command_generator())
        lldpad.start()
        lldpad.stop()

        :param service_name: init service name or systemd unit name
        :type service_name: str
        :param service_command_generator: a sys_v_init or systemd command generator
        :type service_command_generator: _ServiceCommandGenerator
        :param run: function that executes the commands and return CmdResult object, default utils.run
        :type run: function
        """
        for cmd in service_command_generator.commands:
            setattr(self, cmd,
                    self.generate_run_function(run,
                                               getattr(
                                                   service_result_parser, cmd),
                                               getattr(
                                                   service_command_generator, cmd),
                                               service_name))

    @staticmethod
    def generate_run_function(run_func, parse_func, command, service_name):
        """
        Generate the wrapped call to utils.run for the given service_name.

        :param run_func:  function to execute command and return CmdResult object.
        :type run_func:  function
        :param parse_func: function to parse the result from run.
        :type parse_func: function
        :param command: partial function that generates the command list
        :type command: function
        :param service_name: init service name or systemd unit name
        :type service_name: str
        :return: wrapped utils.run function.
        :rtype: function
        """
        def run(**kwargs):
            """
            Wrapped utils.run invocation that will start, stop, restart, etc. a service.

            :param kwargs: extra arguments to utils.run, .e.g. timeout. But not for ignore_status.
                           We need a CmdResult to parse and raise a error.TestError if command failed.
                           We will not let the CmdError out.
            :return: result of parse_func.
            """
            # If run_func is utils.run by default, we need to set
            # ignore_status = True. Otherwise, skip this setting.
            if run_func is utils.run:
                logging.debug("Setting ignore_status to True.")
                kwargs["ignore_status"] = True
            result = run_func(" ".join(command(service_name)), **kwargs)
            return parse_func(result)
        return run


class _GenericServiceManager(object):

    """
    Base class for SysVInitServiceManager and SystemdServiceManager.
    """

    def __init__(self, service_command_generator, service_result_parser, run=utils.run):
        """
        Create staticmethods for each service command, e.g. start, stop, restart.
        These staticmethods take as an argument the service to be started or stopped.

        systemd = SpecificServiceManager(auto_create_specific_service_command_generator())
        systemd.start("lldpad")
        systemd.stop("lldpad")

        :param service_command_generator: a sys_v_init or systemd command generator
        :type service_command_generator: _ServiceCommandGenerator
        :param run: function to call the run the commands, default utils.run
        :type run: function
        """
        # create staticmethods in class attributes (not used)
        # for cmd in service_command_generator.commands:
        #     setattr(self.__class__, cmd,
        #             staticmethod(self.generate_run_function(run, getattr(service_command_generator, cmd))))
        # create functions in instance attributes
        for cmd in service_command_generator.commands:
            setattr(self, cmd,
                    self.generate_run_function(run,
                                               getattr(
                                                   service_result_parser, cmd),
                                               getattr(service_command_generator, cmd)))

    @staticmethod
    def generate_run_function(run_func, parse_func, command):
        """
        Generate the wrapped call to utils.run for the service command, "service" or "systemctl"

        :param run_func:  utils.run
        :type run_func:  function
        :param command: partial function that generates the command list
        :type command: function
        :return: wrapped utils.run function.
        :rtype: function
        """
        def run(service="", **kwargs):
            """
            Wrapped utils.run invocation that will start, stop, restart, etc. a service.

            :param service: service name, e.g. crond, dbus, etc.
            :param kwargs: extra arguments to utils.run, .e.g. timeout. But not for ignore_status.
                           We need a CmdResult to parse and raise a error.TestError if command failed.
                           We will not let the CmdError out.
            :return: result of parse_func.
            """
            # If run_func is utils.run by default, we need to set
            # ignore_status = True. Otherwise, skip this setting.
            if run_func is utils.run:
                logging.debug("Setting ignore_status to True.")
                kwargs["ignore_status"] = True
            result = run_func(" ".join(command(service)), **kwargs)
            return parse_func(result)
        return run


class _SysVInitServiceManager(_GenericServiceManager):

    """
    Concrete class that implements the SysVInitServiceManager
    """

    def __init__(self, service_command_generator, service_result_parser, run=utils.run):
        """
        Create the GenericServiceManager for SysV services.

        :param service_command_generator:
        :type service_command_generator: _ServiceCommandGenerator
        :param run: function to call to run the commands, default utils.run
        :type run: function
        """
        super(
            _SysVInitServiceManager, self).__init__(service_command_generator,
                                                    service_result_parser, run)

    # @staticmethod
    # def change_default_runlevel(runlevel='3'):
    #     """
    #     Set the default sys_v runlevel
    #
    #     :param runlevel: sys_v runlevel to set as default in inittab
    #     :type runlevel: str
    #     """
    #     raise NotImplemented


def convert_sysv_runlevel(level):
    """
    Convert runlevel to systemd target.

    :param level: sys_v runlevel
    :type level: str or int
    :return: systemd target
    :rtype: str
    :raise ValueError: when runlevel is unknown
    """
    runlevel = str(level)
    if runlevel == '0':
        target = "poweroff.target"
    elif runlevel in ['1', "s", "single"]:
        target = "rescue.target"
    elif runlevel in ['2', '3', '4']:
        target = "multi-user.target"
    elif runlevel == '5':
        target = "graphical.target"
    elif runlevel == '6':
        target = "reboot.target"
    else:
        raise ValueError("unknown runlevel %s" % level)
    return target


def convert_systemd_target_to_runlevel(target):
    """
    Convert systemd target to runlevel.

    :param target: systemd target
    :type target: str
    :return: sys_v runlevel
    :rtype: str
    :raise ValueError: when systemd target is unknown
    """
    if target == "poweroff.target":
        runlevel = '0'
    elif target == "rescue.target":
        runlevel = 's'
    elif target == "multi-user.target":
        runlevel = '3'
    elif target == "graphical.target":
        runlevel = '5'
    elif target == "reboot.target":
        runlevel = '6'
    else:
        raise ValueError("unknown target %s" % target)
    return runlevel


class _SystemdServiceManager(_GenericServiceManager):

    """
    Concrete class that implements the SystemdServiceManager
    """

    def __init__(self, service_command_generator, service_result_parser, run=utils.run):
        """
        Create the GenericServiceManager for systemd services.

        :param service_command_generator:
        :type service_command_generator: _ServiceCommandGenerator
        :param run: function to call to run the commands, default utils.run
        :type run: function
        """
        super(_SystemdServiceManager, self).__init__(service_command_generator,
                                                     service_result_parser, run)

    @staticmethod
    def change_default_runlevel(runlevel='multi-user.target'):
        # atomic symlinking, symlink and then rename
        """
        Set the default systemd target.
        Create the symlink in a temp directory and then use
        atomic rename to move the symlink into place.

        :param runlevel: default systemd target
        :type runlevel: str
        """
        tmp_symlink = mktemp(dir="/etc/systemd/system")
        os.symlink("/usr/lib/systemd/system/%s" % runlevel, tmp_symlink)
        os.rename(tmp_symlink, "/etc/systemd/system/default.target")


class Factory(object):

    """
    Class to create different kinds of ServiceManager.
    The all interfaces to create manager are staticmethod,
    so we do not have to create an instance of factory
    when create manager.

    * GenericServiceManager:
        * Interface: create_generic_service()
        * Description: Object to manage the all services(lldp, sshd and so on).
                You can list the all services by GenericServiceManager.list().
                And you can operate any service by passing the service name,
                such as GenericServiceManager.start("sshd").

                Example:
                # Get the system service manager
                service_manager = Factory.create_generic_service()

                # Stating service/unit "sshd"
                service_manager.start("sshd")

                # Getting a list of available units
                units = service_manager.list()

    * SpecificServiceManager:
        * interface: create_specific_service(service_name)
        * description: Object to manage specific service(such as sshd). You can
                not operate the other services nor list the all information on
                this host.

                # Get the specific service manager for sshd
                sshd = Factory.create_specific_service("sshd")
                sshd.start()
                sshd.stop()

    After all, there is an unified interface to create both of them,
    create_service(service_name=None).

    If we pass a service_name to it, it will return a SpecificServiceManager,
    otherwise, it will return GenericServiceManager.
    """

    class FactoryHelper(object):

        """
        Internal class to help create service manager.

        Provide some functions to auto detect system type.
        And auto create command_generator and result_parser.
        """
        _command_generators = {"init": sys_v_init_command_generator,
                               "systemd": systemd_command_generator}

        _result_parsers = {"init": sys_v_init_result_parser,
                           "systemd": systemd_result_parser}

        _service_managers = {"init": _SysVInitServiceManager,
                             "systemd": _SystemdServiceManager}

        def __init__(self, run=utils.run):
            """
            Init a helper to create service manager.

            :param run: Funtion to run command.
            :type: utils.run-like function.
            """
            result = run("true")
            if not isinstance(result, utils.CmdResult):
                raise ValueError("Param run is a/an %s, "
                                 "but not an instance of utils.CmdResult."
                                 % (type(result)))
            self.run = run
            self.init_name = self.get_name_of_init()

        def get_name_of_init(self):
            """
            Internal function to determine what executable is PID 1,
            :return: executable name for PID 1, aka init
            :rtype:  str
            """
            output = self.run("ps -o comm 1").stdout
            return output.splitlines()[-1].strip()

        def get_generic_service_manager_type(self):
            """
            Get the ServiceManager type using the auto-detect init command.

            :return: Subclass type of _GenericServiceManager from the current init command.
            :rtype: _SysVInitServiceManager or _SystemdServiceManager.
            """
            return self._service_managers[self.init_name]

        def get_generic_service_result_parser(self):
            """
            Get the ServiceResultParser using the auto-detect init command.

            :return: ServiceResultParser fro the current init command.
            :rtype: _ServiceResultParser
            """
            result_parser = self._result_parsers[self.init_name]
            return _ServiceResultParser(result_parser)

        def get_generic_service_command_generator(self):
            """
            Lazy initializer for ServiceCommandGenerator using the auto-detect init command.

            :return: ServiceCommandGenerator for the current init command.
            :rtype: _ServiceCommandGenerator
            """
            command_generator = self._command_generators[self.init_name]
            return _ServiceCommandGenerator(command_generator)

        def get_specific_service_result_parser(self):
            """
            Create a class that will create partial functions that generate result_parser
            for the current init command.

            :return: A ServiceResultParser for the auto-detected init command.
            :rtype: _ServiceResultParser
            """
            result_parser = self._result_parsers[self.init_name]
            # remove list method
            command_list = [
                c for c in COMMANDS if c not in ["list", "set_target"]]
            return _ServiceResultParser(result_parser, command_list)

        def get_specific_service_command_generator(self):
            """
            Create a class that will create partial functions that generate commands
            for the current init command.

            ::

                lldpad = SpecificServiceManager("lldpad",
                             auto_create_specific_service_command_generator())
                lldpad.start()
                lldpad.stop()

            :return: A ServiceCommandGenerator for the auto-detected init command.
            :rtype: _ServiceCommandGenerator
            """
            command_generator = self._command_generators[self.init_name]
            # remove list method
            command_list = [
                c for c in COMMANDS if c not in ["list", "set_target"]]
            return _ServiceCommandGenerator(command_generator, command_list)

    @staticmethod
    def create_generic_service(run=utils.run):
        """
        Detect which init program is being used, init or systemd and return a
        class with methods to start/stop services.

        ::

            # Get the system service manager
            service_manager = Factory.create_generic_service()

            # Stating service/unit "sshd"
            service_manager.start("sshd")

            # Getting a list of available units
            units = service_manager.list()

            # Disabling and stopping a list of services
            services_to_disable = ['ntpd', 'httpd']
            for s in services_to_disable:
                service_manager.disable(s)
                service_manager.stop(s)

        :return: SysVInitServiceManager or SystemdServiceManager
        :rtype: _GenericServiceManager
        """
        helper = Factory.FactoryHelper(run)
        service_manager = helper.get_generic_service_manager_type()
        command_generator = helper.get_generic_service_command_generator()
        result_parser = helper.get_generic_service_result_parser()
        return service_manager(command_generator, result_parser, run)

    @staticmethod
    def create_specific_service(service_name, run=utils.run):
        """

        # Get the specific service manager for sshd
        sshd = Factory.create_specific_service("sshd")
        sshd.start()
        sshd.stop()
        sshd.reload()
        sshd.restart()
        sshd.condrestart()
        sshd.status()
        sshd.enable()
        sshd.disable()
        sshd.is_enabled()

        :param service_name: systemd unit or init.d service to manager
        :type service_name: str
        :return: SpecificServiceManager that has start/stop methods
        :rtype: _SpecificServiceManager
        """
        helper = Factory.FactoryHelper(run)
        command_generator = helper.get_specific_service_command_generator()
        result_parser = helper.get_specific_service_result_parser()

        return _SpecificServiceManager(service_name,
                                       command_generator,
                                       result_parser,
                                       run)

    @staticmethod
    def create_service(service_name=None, run=utils.run):
        """
        # Unified interface for generic and specific service manager.

        :return: _SpecificServiceManager if service_name is not None,
                _GenericServiceManager if service_name is None.
        """
        if service_name:
            return Factory.create_specific_service(service_name, run)
        return Factory.create_generic_service(run)
