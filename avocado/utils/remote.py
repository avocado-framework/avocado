"""
Functions and classes used for logging into guests and transferring files.
"""
import logging
import time
import aexpect
import utils_misc


class LoginError(Exception):
    """
    Error class for Login Error.
    """
    def __init__(self, msg, output):
        Exception.__init__(self, msg, output)
        self.msg = msg
        self.output = output

    def __str__(self):
        return "%s    (output: %r)" % (self.msg, self.output)


class LoginAuthenticationError(LoginError):
    """
    Error class for Login Authentication Error.
    """
    pass


class LoginTimeoutError(LoginError):
    """
    Error class for Login Timeout Error.
    """
    def __init__(self, output):
        LoginError.__init__(self, "Login timeout expired", output)


class LoginProcessTerminatedError(LoginError):
    """
    Error class for Login Process Terminated Error.
    """
    def __init__(self, status, output):
        LoginError.__init__(self, None, output)
        self.status = status

    def __str__(self):
        return ("Client process terminated    (status: %s,    output: %r)" %
                (self.status, self.output))


class LoginBadClientError(LoginError):
    """
    Error class for Login Bad Client Error.
    """
    def __init__(self, client):
        LoginError.__init__(self, None, None)
        self.client = client

    def __str__(self):
        return "Unknown remote shell client: %r" % self.client


def handle_prompts(session, username, password, prompt, timeout=10,
                   debug=False):
    """
    Connect to a remote host (guest) using SSH or Telnet or else.

    Wait for questions and provide answers.  If timeout expires while
    waiting for output from the child (e.g. a password prompt or
    a shell prompt) -- fail.

    :param session: An Expect or ShellSession instance to operate on
    :param username: The username to send in reply to a login prompt
    :param password: The password to send in reply to a password prompt
    :param prompt: The shell prompt that indicates a successful login
    :param timeout: The maximal time duration (in seconds) to wait for each
            step of the login procedure (i.e. the "Are you sure" prompt, the
            password prompt, the shell prompt, etc)
    :raise LoginTimeoutError: If timeout expires
    :raise LoginAuthenticationError: If authentication fails
    :raise LoginProcessTerminatedError: If the client terminates during login
    :raise LoginError: If some other error occurs
    :return: If connect succeed return the output text to script for further
             debug.
    """
    password_prompt_count = 0
    login_prompt_count = 0

    output = ""
    while True:
        try:
            match, text = session.read_until_last_line_matches(
                [r"[Aa]re you sure", r"[Pp]assword:\s*",
                 # Prompt of rescue mode for Red Hat.
                 r"\(or (press|type) Control-D to continue\):\s*$",
                 r"[Gg]ive.*[Ll]ogin:\s*$",  # Prompt of rescue mode for SUSE.
                 r"(?<![Ll]ast )[Ll]ogin:\s*$",  # Don't match "Last Login:"
                 r"[Cc]onnection.*closed", r"[Cc]onnection.*refused",
                 r"[Pp]lease wait", r"[Ww]arning", r"[Ee]nter.*username",
                 r"[Ee]nter.*password", r"[Cc]onnection timed out", prompt],
                timeout=timeout, internal_timeout=0.5)
            output += text
            if match == 0:  # "Are you sure you want to continue connecting"
                if debug:
                    logging.debug("Got 'Are you sure...', sending 'yes'")
                session.sendline("yes")
                continue
            elif match in [1, 2, 3, 10]:  # "password:"
                if password_prompt_count == 0:
                    if debug:
                        logging.debug("Got password prompt, sending '%s'",
                                      password)
                    session.sendline(password)
                    password_prompt_count += 1
                    continue
                else:
                    raise LoginAuthenticationError("Got password prompt twice",
                                                   text)
            elif match == 4 or match == 9:  # "login:"
                if login_prompt_count == 0 and password_prompt_count == 0:
                    if debug:
                        logging.debug("Got username prompt; sending '%s'",
                                      username)
                    session.sendline(username)
                    login_prompt_count += 1
                    continue
                else:
                    if login_prompt_count > 0:
                        msg = "Got username prompt twice"
                    else:
                        msg = "Got username prompt after password prompt"
                    raise LoginAuthenticationError(msg, text)
            elif match == 5:  # "Connection closed"
                raise LoginError("Client said 'connection closed'", text)
            elif match == 6:  # "Connection refused"
                raise LoginError("Client said 'connection refused'", text)
            elif match == 11:  # Connection timeout
                raise LoginError("Client said 'connection timeout'", text)
            elif match == 7:  # "Please wait"
                if debug:
                    logging.debug("Got 'Please wait'")
                timeout = 30
                continue
            elif match == 8:  # "Warning added RSA"
                if debug:
                    logging.debug("Got 'Warning added RSA to known host list")
                continue
            elif match == 12:  # prompt
                if debug:
                    logging.debug("Got shell prompt -- logged in")
                break
        except aexpect.ExpectTimeoutError, exception:
            raise LoginTimeoutError(exception.output)
        except aexpect.ExpectProcessTerminatedError, exception:
            raise LoginProcessTerminatedError(exception.status,
                                              exception.output)

    return output


def remote_login(client, host, port, username, password, prompt, linesep="\n",
                 log_filename=None, timeout=10, interface=None,
                 status_test_command="echo $?", verbose=False):
    """
    Log into a remote host (guest) using SSH/Telnet/Netcat.

    :param client: The client to use ('ssh', 'telnet' or 'nc')
    :param host: Hostname or IP address
    :param port: Port to connect to
    :param username: Username (if required)
    :param password: Password (if required)
    :param prompt: Shell prompt (regular expression)
    :param linesep: The line separator to use when sending lines
            (e.g. '\\n' or '\\r\\n')
    :param log_filename: If specified, log all output to this file
    :param timeout: The maximal time duration (in seconds) to wait for
            each step of the login procedure (i.e. the "Are you sure" prompt
            or the password prompt)
    :interface: The interface the neighbours attach to(only use when using ipv6
                linklocal address.)
    :param status_test_command: Command to be used for getting the last
            exit status of commands run inside the shell (used by
            cmd_status_output() and friends).

    :raise LoginError: If using ipv6 linklocal but not assign a interface that
                       the neighbour attache
    :raise LoginBadClientError: If an unknown client is requested
    :raise: Whatever handle_prompts() raises
    :return: A ShellSession object.
    """
    if host and host.lower().startswith("fe80"):
        if not interface:
            raise LoginError("When using ipv6 linklocal an interface must "
                             "be assigned", host)
        host = "%s%%%s" % (host, interface)

    verbose = verbose and "-vv" or ""
    if client == "ssh":
        cmd = ("ssh %s -o UserKnownHostsFile=/dev/null "
               "-o StrictHostKeyChecking=no "
               "-o PreferredAuthentications=password -p %s %s@%s" %
               (verbose, port, username, host))
    elif client == "telnet":
        cmd = "telnet -l %s %s %s" % (username, host, port)
    elif client == "nc":
        cmd = "nc %s %s %s" % (verbose, host, port)
    else:
        raise LoginBadClientError(client)

    if verbose:
        logging.debug("Login command: '%s'", cmd)
    session = aexpect.ShellSession(cmd, linesep=linesep, prompt=prompt,
                                   status_test_command=status_test_command)
    try:
        handle_prompts(session, username, password, prompt, timeout)
    except Exception:
        session.close()
        raise
    if log_filename:
        session.set_output_func(utils_misc.log_line)
        session.set_output_params((log_filename,))
        session.set_log_file(log_filename)
    return session


def wait_for_login(client, host, port, username, password, prompt,
                   linesep="\n", log_filename=None, timeout=240,
                   internal_timeout=10, interface=None):
    """
    Make multiple attempts to log into a guest until one succeeds or timeouts.

    :param timeout: Total time duration to wait for a successful login
    :param internal_timeout: The maximum time duration (in seconds) to wait for
                             each step of the login procedure (e.g. the
                             "Are you sure" prompt or the password prompt)
    :interface: The interface the neighbours attach to(only use when using ipv6
                linklocal address.)
    :see: remote_login()
    :raise: Whatever remote_login() raises
    :return: A ShellSession object.
    """
    logging.debug("Attempting to log into %s:%s using %s (timeout %ds)",
                  host, port, client, timeout)
    end_time = time.time() + timeout
    verbose = False
    while time.time() < end_time:
        try:
            return remote_login(client, host, port, username, password, prompt,
                                linesep, log_filename, internal_timeout,
                                interface, verbose=verbose)
        except LoginError, exception:
            logging.debug(exception)
            verbose = True
        time.sleep(2)
    # Timeout expired; try one more time but don't catch exceptions
    return remote_login(client, host, port, username, password, prompt,
                        linesep, log_filename, internal_timeout, interface)
