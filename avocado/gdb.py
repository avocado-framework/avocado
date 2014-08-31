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
# Copyright: Red Hat Inc. 2014
# Authors: Cleber Rosa <cleber@redhat.com>

"""
Module that provides communication with GDB via its GDB/MI interpreter
"""

import os
import time
import fcntl
import subprocess

from avocado.utils import network
from avocado.external import gdbmi_parser

GDB_PROMPT = '(gdb)'
GDB_EXIT = '^exit'
GDB_BREAK_CONTITIONS = [GDB_PROMPT, GDB_EXIT]


class UnexpectedResponseError(Exception):

    '''
    A response different from the one expected was received from GDB
    '''
    pass


def parse_mi(line):
    '''
    Parse a GDB/MI line

    :param line: a string supposedely comming from GDB using MI language
    :type line: str
    :returns: a parsed GDB/MI response
    '''
    if not line.endswith('\n'):
        line = "%s\n" % line
    return gdbmi_parser.process(line)


def encode_mi_cli(command):
    """
    Encodes a regular (CLI) command into the proper MI form

    :param command: the regular cli command to send
    :type command: str
    :returns: the encoded (escaped) MI command
    :rtype: str
    """
    return '-interpreter-exec console "%s"' % command


class CommandResult(object):

    """
    A GDB command, its result, and other possible messages
    """

    def __init__(self, command):
        self.command = command
        self.timestamp = time.time()
        self.stream_messages = []
        self.application_output = []
        self.result = None

    def get_application_output(self):
        """
        Return all application output concatenated as a single string

        :returns: application output concatenated
        :rtype: str
        """
        return "".join(self.application_output)

    def get_stream_messages_text(self):
        """
        Return all stream messages text concatenated as a single string

        :returns: stream messages text concatenated
        :rtype: str
        """
        return "".join([m.value for m in self.stream_messages])

    def __repr__(self):
        return "%s at %s" % (self.command, self.timestamp)


class GDB(object):

    """
    Wraps a GDB subprocess for easier manipulation
    """

    GDB_PATH = '/usr/bin/gdb'

    GDB_ARGS = [GDB_PATH,
                '--interpreter=mi',
                '--quiet']

    def __init__(self):
        self.process = subprocess.Popen(self.GDB_ARGS,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        close_fds=True)

        fcntl.fcntl(self.process.stdout.fileno(),
                    fcntl.F_SETFL, os.O_NONBLOCK)
        self.read_until_break()

        # any GDB MI async messages
        self.async_messages = []

        self.commands_history = []

        # whatever comes from the app that is not a GDB MI message
        self.output_messages = []
        self.output_messages_queue = []

    def read_gdb_response(self, timeout=0.01, max_tries=100):
        '''
        Read raw reponses from GDB

        :param timeout: the amount of time to way between read attemps
        :type timeout: float
        :param max_tries: the maximum number of cycles to try to read until
                          a response is obtained
        :type max_tries: int
        :returns: a string containing a raw response from GDB
        :rtype: str
        '''
        current_try = 0
        while current_try < max_tries:
            try:
                line = self.process.stdout.readline()
                line = line.strip()
                if line:
                    return line
            except IOError:
                current_try += 1
            if current_try >= max_tries:
                raise ValueError("Could not read GDB response")
            else:
                time.sleep(timeout)

    def read_until_break(self, max_lines=100):
        '''
        Read lines from GDB until a break condition is reached

        :param max_lines: the maximum number of lines to read
        :type max_lines: int
        :returns: a list of messages read
        :rtype: list of str
        '''
        result = []
        while True:
            line = self.read_gdb_response()
            if line in GDB_BREAK_CONTITIONS:
                break
            if len(result) >= max_lines:
                break
            result.append(line)
        return result

    def send_gdb_command(self, command):
        '''
        Send a raw command to the GNU debugger input

        :param command: the GDB command, hopefully in MI language
        :type command: str
        :returns: None
        '''
        if not command.endswith('\n'):
            command = "%s\n" % command
        self.process.stdin.write(command)

    def cmd(self, command):
        """
        Sends a command and parses all lines until prompt is received

        :param command: the GDB command, hopefully in MI language
        :type command: str
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = CommandResult(command)

        self.send_gdb_command(command)
        responses = self.read_until_break()
        result_response = None

        for line in responses:
            # If the line can not be properly parsed, it is *most likely*
            # generated by the application being run inside the debugger
            try:
                parsed_response = parse_mi(line)
            except:
                cmd.application_output.append(line)
                continue

            if (parsed_response.type == 'console' and
                    parsed_response.record_type == 'stream'):
                cmd.stream_messages.append(parsed_response)
            elif parsed_response.type == 'result':
                if result_response is not None:
                    # raise an exception here, because no two result
                    # responses should come from a single command AFAIK
                    raise Exception("Many result responses to a single cmd")
                cmd.result = parsed_response
            else:
                self.async_messages.append(parsed_response)

        return cmd

    def cli_cmd(self, command):
        """
        Sends a cli command encoded as an MI command

        :param command: a regular GDB cli command
        :type command: str
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = encode_mi_cli(command)
        return self.cmd(cmd)

    def cmd_exists(self, command):
        """
        Checks if a given command exists

        :param command: a GDB MI command, including the dash (-) prefix
        :type command: str
        :returns: either True or False
        :rtype: bool
        """
        gdb_info_command = "-info-gdb-mi-command %s" % command[1:]
        r = self.cmd(gdb_info_command)
        return r.result.result.command.exists == 'true'

    def set_file(self, path):
        """
        Sets the file that will be executed

        :param path: the path of the binary that will be executed
        :type path: str
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        self.binary_name = os.path.basename(path)
        cmd = "-file-exec-and-symbols %s" % path
        r = self.cmd(cmd)
        if not r.result.class_ == 'done':
            raise UnexpectedResponseError
        return r

    def set_break(self, location):
        """
        Sets a new breakpoint on the binary currently being debugged

        :param location: a breakpoint location expression as accepted by GDB
        :type location: str
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = "-break-insert %s" % location
        r = self.cmd(cmd)
        if not r.result.class_ == 'done':
            raise UnexpectedResponseError
        return r

    def del_break(self, number):
        """
        Deletes a breakpoint by its number

        :param number: the breakpoint number
        :type number: int
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = "-break-delete %s" % number
        r = self.cmd(cmd)
        if not r.result.class_ == 'done':
            raise UnexpectedResponseError
        return r

    def run(self, args=[]):
        """
        Runs the application inside the debugger

        :param args: the arguments to be passed to the binary as command line
                     arguments
        :type args: list
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        args_text = ' '.join(args)
        cmd = '-exec-run %s' % args_text
        r = self.cmd(cmd)
        if not r.result.class_ == 'running':
            raise UnexpectedResponseError
        return r

    def connect(self, port):
        """
        Connects to a remote debugger (a gdbserver) at the given TCP port

        This uses the "extended-remote" target type only

        :param port: the TCP port number
        :type port: int
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = '-target-select extended-remote :%s' % port
        r = self.cmd(cmd)
        if not r.result.class_ == 'connected':
            raise UnexpectedResponseError
        return r

    def disconnect(self):
        """
        Disconnects from a remote debugger

        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        cmd = '-target-disconnect'
        r = self.cmd(cmd)
        if not r.result.class_ == 'done':
            raise UnexpectedResponseError
        return r

    def exit(self):
        """
        Exits the GDB application gracefully

        :returns: the result of :meth:`subprocess.POpen.wait`, that is, a
                  :attr:`subprocess.POpen.returncode`
        :rtype: int or None
        """
        self.cmd("-gdb-exit")
        return self.process.wait()


class GDBServer(object):

    """
    Wraps a gdbserver instance
    """

    #: The default arguments used when starting the GDB server process
    ARGS = ['/usr/bin/gdbserver',
            '--multi']

    #: The range from which a port to GDB server will try to be allocated from
    PORT_RANGE = (20000, 20999)

    def __init__(self):
        self.port = network.find_free_port(*self.PORT_RANGE)

        args = self.ARGS[:]
        args.append(":%s" % self.port)
        self.process = subprocess.Popen(args,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        close_fds=True)

    def exit(self, force=True):
        """
        Quits the gdb_server process

        Most correct way of quitting the GDB server is by sending it a command.
        If no GDB client is connected, then we can try to connect to it and
        send a quit command. If this is not possible, we send it a signal and
        wait for it to finish.

        :param force: if a forced exit (sending SIGTERM) should be attempted
        :type force: bool
        :returns: None
        """
        temp_client = GDB()
        try:
            temp_client.connect(self.port)
            temp_client.cli_cmd("monitor exit")
        except (UnexpectedResponseError, ValueError):
            if force:
                self.process.kill()
        finally:
            try:
                temp_client.disconnect()
                temp_client.exit()
            except (UnexpectedResponseError, ValueError):
                if force:
                    temp_client.process.kill()
                    temp_client.process.wait()
            self.process.wait()
