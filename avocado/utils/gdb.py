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

__all__ = ['GDB', 'GDBServer', 'GDBRemote']


import os
import time
import fcntl
import socket
import tempfile

try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

from . import network
from .external import gdbmi_parser

#: Contains a list of binary names that should be run via the GNU debugger
#: and be stopped at a given point. That means that a breakpoint will be set
#: using the given expression
GDB_RUN_BINARY_NAMES_EXPR = []

#: After loading a binary in binary in GDB, but before actually running it,
#: execute the given GDB commands present in the given file, one per line
GDB_PRERUN_COMMANDS = {}

#: Whether to enable the automatic generation of core dumps for applications
#: that are run inside the GNU debugger
GDB_ENABLE_CORE = False

#: Path to the GDB binary
GDB_PATH = None

#: Path to the gdbserver binary
GDBSERVER_PATH = None

GDB_PROMPT = '(gdb)'
GDB_EXIT = '^exit'
GDB_BREAK_CONDITIONS = [GDB_PROMPT, GDB_EXIT]

#: How the remote protocol signals a transmission success (in ACK mode)
REMOTE_TRANSMISSION_SUCCESS = '+'

#: How the remote protocol signals a transmission failure (in ACK mode)
REMOTE_TRANSMISSION_FAILURE = '-'

#: How the remote protocol flags the start of a packet
REMOTE_PREFIX = '$'

#: How the remote protocol flags the end of the packet payload, and that the
#: two digits checksum follow
REMOTE_DELIMITER = '#'

#: Rather conservative default maximum packet size for clients using the
#: remote protocol. Individual connections can ask (and do so by default)
#: the server about the maximum packet size they can handle.
REMOTE_MAX_PACKET_SIZE = 1024


class UnexpectedResponseError(Exception):

    """
    A response different from the one expected was received from GDB
    """
    pass


class ServerInitTimeoutError(Exception):

    """
    Server took longer than expected to initialize itself properly
    """
    pass


class InvalidPacketError(Exception):

    """
    Packet received has invalid format
    """
    pass


class NotConnectedError(Exception):

    """
    GDBRemote is not connected to a remote GDB server
    """
    pass


class RetransmissionRequestedError(Exception):

    """
    Message integrity was not validated and retransmission is being requested
    """
    pass


def parse_mi(line):
    """
    Parse a GDB/MI line

    :param line: a string supposedly coming from GDB using MI language
    :type line: str
    :returns: a parsed GDB/MI response
    """
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


def is_stopped_exit(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'class_') and
            (parsed_mi_msg.class_ == 'stopped') and
            hasattr(parsed_mi_msg, 'result') and
            hasattr(parsed_mi_msg.result, 'reason') and
            (parsed_mi_msg.result.reason == "exited"))


def is_thread_group_exit(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'class_') and
            (parsed_mi_msg.class_ == 'thread-group-exited'))


def is_exit(parsed_mi_msg):
    return (is_stopped_exit(parsed_mi_msg) or
            is_thread_group_exit(parsed_mi_msg))


def is_break_hit(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'class_') and
            (parsed_mi_msg.class_ == 'stopped') and
            hasattr(parsed_mi_msg, 'result') and
            hasattr(parsed_mi_msg.result, 'reason') and
            (parsed_mi_msg.result.reason == "breakpoint-hit"))


def is_sigsegv(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'class_') and
            (parsed_mi_msg.class_ == 'stopped') and
            hasattr(parsed_mi_msg, 'result') and
            hasattr(parsed_mi_msg.result, 'signal_name') and
            (parsed_mi_msg.result.reason == "SIGSEGV"))


def is_sigabrt_stopped(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'class_') and
            (parsed_mi_msg.class_ == 'stopped') and
            hasattr(parsed_mi_msg, 'record_type') and
            (parsed_mi_msg.record_type == 'result') and
            (parsed_mi_msg.result.reason == 'signal-received') and
            (parsed_mi_msg.result.signal_name == 'SIGABRT'))


def is_sigabrt_console(parsed_mi_msg):
    return (hasattr(parsed_mi_msg, 'record_type') and
            (parsed_mi_msg.record_type == 'stream') and
            hasattr(parsed_mi_msg, 'type') and
            (parsed_mi_msg.type == 'console') and
            hasattr(parsed_mi_msg, 'value') and
            parsed_mi_msg.value == 'SIGABRT, Aborted.\n')


def is_sigabrt(parsed_mi_msg):
    return (is_sigabrt_stopped(parsed_mi_msg) or
            is_sigabrt_console(parsed_mi_msg))


def is_fatal_signal(parsed_mi_msg):
    return is_sigsegv(parsed_mi_msg) or is_sigabrt(parsed_mi_msg)


def format_as_hex(char):
    """
    Formats a single ascii character as a lower case hex string

    :param char: a single ascii character
    :type char: str
    :returns: the character formatted as a lower case hex string
    :rtype: str
    """
    return "%2x" % ord(char)


def string_to_hex(text):
    """
    Formats a string of text into an hex representation

    :param text: a multi character string
    :type text: str
    :returns: the string converted to an hex representation
    :rtype: str
    """
    return "".join(map(format_as_hex, text))


def remote_checksum(input):
    """
    Calculates a remote message checksum

    :param input: the message input payload, without the start and end markers
    :type input: str
    :returns: two digit checksum
    :rtype: str
    """
    sum = 0
    for i in input:
        sum += ord(i)
    result = sum % 256

    hexa = "%2x" % result
    return hexa.lower()


def remote_encode(data):
    """
    Encodes a command

    That is, add prefix, suffix and checksum

    :param command_data: the command data payload
    :type command_data: str
    :returns: the encoded command, ready to be sent to a remote GDB
    :rtype: str
    """
    return "$%s#%s" % (data, remote_checksum(data))


def remote_decode(data):
    """
    Decodes a packet and returns its payload

    :param command_data: the command data payload
    :type command_data: str
    :returns: the encoded command, ready to be sent to a remote GDB
    :rtype: str
    """
    if data[0] != REMOTE_PREFIX:
        raise InvalidPacketError

    if data[-3] != REMOTE_DELIMITER:
        raise InvalidPacketError

    payload = data[1:-3]
    checksum = data[-2:]

    if payload == '':
        expected_checksum = '00'
    else:
        expected_checksum = remote_checksum(payload)

    if checksum != expected_checksum:
        raise InvalidPacketError

    return payload


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

    REQUIRED_ARGS = ['--interpreter=mi',
                     '--quiet']

    DEFAULT_BREAK = 'main'

    def __init__(self, path='/usr/bin/gdb', *extra_args):

        self.path = path
        args = [self.path]
        args += self.REQUIRED_ARGS
        args += extra_args

        try:
            self.process = subprocess.Popen(args,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            close_fds=True)
        except OSError as details:
            if details.errno == 2:
                exc = OSError("File '%s' not found" % args[0])
                exc.errno = 2
                raise exc
            else:
                raise

        fcntl.fcntl(self.process.stdout.fileno(),
                    fcntl.F_SETFL, os.O_NONBLOCK)
        self.read_until_break()

        # If this instance is connected to another target. If so, what
        # tcp port it's connected to
        self.connected_to = None

        # any GDB MI async messages
        self.async_messages = []

        self.commands_history = []

        # whatever comes from the app that is not a GDB MI message
        self.output_messages = []
        self.output_messages_queue = []

    def read_gdb_response(self, timeout=0.01, max_tries=100):
        """
        Read raw responses from GDB

        :param timeout: the amount of time to way between read attemps
        :type timeout: float
        :param max_tries: the maximum number of cycles to try to read until
                          a response is obtained
        :type max_tries: int
        :returns: a string containing a raw response from GDB
        :rtype: str
        """
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
        """
        Read lines from GDB until a break condition is reached

        :param max_lines: the maximum number of lines to read
        :type max_lines: int
        :returns: a list of messages read
        :rtype: list of str
        """
        result = []
        while True:
            line = self.read_gdb_response()
            if line in GDB_BREAK_CONDITIONS:
                break
            if len(result) >= max_lines:
                break
            result.append(line)
        return result

    def send_gdb_command(self, command):
        """
        Send a raw command to the GNU debugger input

        :param command: the GDB command, hopefully in MI language
        :type command: str
        :returns: None
        """
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
            except Exception:
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

        if self.connected_to is not None:
            cmd = 'set remote exec-file %s' % path
            r = self.cmd(cmd)
            if not r.result.class_ == 'done':
                raise UnexpectedResponseError
        return r

    def set_break(self, location, ignore_error=False):
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
            if not ignore_error:
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
        :type args: builtin.list
        :returns: a :class:`CommandResult` instance
        :rtype: :class:`CommandResult`
        """
        if args:
            args_text = ' '.join(args)
            cmd = '-exec-arguments %s' % args_text
            r = self.cmd(cmd)
            if not r.result.class_ == 'done':
                raise UnexpectedResponseError

        r = self.cmd('-exec-run')
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
        self.connected_to = port
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
        self.connected_to = None
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
    REQUIRED_ARGS = ['--multi']

    #: The range from which a port to GDB server will try to be allocated from
    PORT_RANGE = (20000, 20999)

    #: The time to optionally wait for the server to initialize itself and be
    #: ready to accept new connections
    INIT_TIMEOUT = 2.0

    def __init__(self, path='/usr/bin/gdbserver', port=None,
                 wait_until_running=True, *extra_args):
        """
        Initializes a new gdbserver instance

        :param path: location of the gdbserver binary
        :type path: str
        :param port: tcp port number to listen on for incoming connections
        :type port: int
        :param wait_until_running: wait until the gdbserver is running and
                                   accepting connections. It may take a little
                                   after the process is started and it is
                                   actually bound to the aloccated port
        :type wait_until_running: bool
        :param extra_args: optional extra arguments to be passed to gdbserver
        """
        self.path = path
        args = [self.path]
        args += self.REQUIRED_ARGS

        if port is None:
            self.port = network.find_free_port(*self.PORT_RANGE)
        else:
            self.port = port
        args.append(":%s" % self.port)

        prefix = 'avocado_gdbserver_%s_' % self.port
        _, self.stdout_path = tempfile.mkstemp(prefix=prefix + 'stdout_')
        self.stdout = open(self.stdout_path, 'w')
        _, self.stderr_path = tempfile.mkstemp(prefix=prefix + 'stderr_')
        self.stderr = open(self.stderr_path, 'w')

        try:
            self.process = subprocess.Popen(args,
                                            stdin=subprocess.PIPE,
                                            stdout=self.stdout,
                                            stderr=self.stderr,
                                            close_fds=True)
        except OSError as details:
            if details.errno == 2:
                exc = OSError("File '%s' not found" % args[0])
                exc.errno = 2
                raise exc
            else:
                raise

        if wait_until_running:
            self._wait_until_running()

    def _wait_until_running(self):
        init_time = time.time()
        connection_ok = False
        c = GDB()
        while time.time() - init_time < self.INIT_TIMEOUT:
            try:
                c.connect(self.port)
                connection_ok = True
                break
            except Exception:
                time.sleep(0.1)
        c.disconnect()
        c.exit()
        if not connection_ok:
            raise ServerInitTimeoutError

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
            self.stdout.close()
            self.stderr.close()


class GDBRemote(object):

    def __init__(self, host, port, no_ack_mode=True, extended_mode=True):
        """
        Initializes a new GDBRemote object.

        A GDBRemote acts like a client that speaks the GDB remote protocol,
        documented at:

        https://sourceware.org/gdb/current/onlinedocs/gdb/Remote-Protocol.html

        Caveat: we currently do not support communicating with devices, only
        with TCP sockets. This limitation is basically due to the lack of
        use cases that justify an implementation, but not due to any technical
        shortcoming.

        :param host: the IP address or host name
        :type host: str
        :param port: the port number where the the remote GDB is listening on
        :type port: int
        :param no_ack_mode: if the packet transmission confirmation mode should
                            be disabled
        :type no_ack_mode: bool
        :param extended_mode: if the remote extended mode should be enabled
        :type param extended_mode: bool
        """
        self.host = host
        self.port = port

        # Temporary holder for the class init attributes
        self._no_ack_mode = no_ack_mode
        self.no_ack_mode = False
        self._extended_mode = extended_mode
        self.extended_mode = False

        self._socket = None

    def cmd(self, command_data, expected_response=None):
        """
        Sends a command data to a remote gdb server

        Limitations: the current version does not deal with retransmissions.

        :param command_data: the remote command to send the the remote stub
        :type command_data: str
        :param expected_response: the (optional) response that is expected
                                  as a response for the command sent
        :type expected_response: str
        :raises: RetransmissionRequestedError, UnexpectedResponseError
        :returns: raw data read from from the remote server
        :rtype: str
        """
        if self._socket is None:
            raise NotConnectedError

        data = remote_encode(command_data)
        sent = self._socket.send(data)

        if not self.no_ack_mode:
            transmission_result = self._socket.recv(1)
            if transmission_result == REMOTE_TRANSMISSION_FAILURE:
                raise RetransmissionRequestedError

        result = self._socket.recv(REMOTE_MAX_PACKET_SIZE)
        response_payload = remote_decode(result)

        if expected_response is not None:
            if expected_response != response_payload:
                raise UnexpectedResponseError

        return response_payload

    def set_extended_mode(self):
        """
        Enable extended mode. In extended mode, the remote server is made
        persistent. The 'R' packet is used to restart the program being
        debugged. Original documentation at:

        https://sourceware.org/gdb/current/onlinedocs/gdb/Packets.html#extended-mode
        """
        self.cmd("!", "OK")
        self.extended_mode = True

    def start_no_ack_mode(self):
        """
        Request that the remote stub disable the normal +/- protocol
        acknowledgments. Original documentation at:

        https://sourceware.org/gdb/current/onlinedocs/gdb/General-Query-Packets.html#QStartNoAckMode
        """
        self.cmd("QStartNoAckMode", "OK")
        self.no_ack_mode = True

    def connect(self):
        """
        Connects to the remote target and initializes the chosen modes
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))

        if self._no_ack_mode:
            self.start_no_ack_mode()

        if self._extended_mode:
            self.set_extended_mode()
