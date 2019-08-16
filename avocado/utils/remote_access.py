try:
    import pxssh
except ImportError:
    from pexpect import pxssh


def login(self, ip, username, password):
    '''
    SSH Login method for remote server
    '''
    pxh = pxssh.pxssh()
    # Work-around for old pxssh not having options= parameter
    pxh.SSH_OPTS = "%s  -o 'StrictHostKeyChecking=no'" % pxh.SSH_OPTS
    pxh.SSH_OPTS = "%s  -o 'UserKnownHostsFile /dev/null' " % pxh.SSH_OPTS
    pxh.force_password = True

    pxh.login(ip, username, password)
    pxh.sendline()
    pxh.prompt(timeout=60)
    pxh.sendline('exec bash --norc --noprofile')
    pxh.prompt(timeout=60)
    # Ubuntu likes to be "helpful" and alias grep to
    # include color, which isn't helpful at all. So let's
    # go back to absolutely no messing around with the shell
    pxh.set_unique_prompt()
    pxh.prompt(timeout=60)
    self.pxssh = pxh


def run_command(self, command, timeout=300):
    '''
    SSH Run command method for running commands on remote server
    '''
    self.log.info("Running the command on peer lpar: %s", command)
    if not hasattr(self, 'pxssh'):
        self.fail("SSH Console setup is not yet done")
    con = self.pxssh
    con.sendline(command)
    con.expect("\n")  # from us
    if command.endswith('&'):
        return ("", 0)
    con.expect(con.PROMPT, timeout=timeout)
    output = con.before.splitlines()
    con.sendline("echo $?")
    con.prompt(timeout)
    try:
        exitcode = int(''.join(con.before.splitlines()[1:]))
    except Exception as exc:
        exitcode = 0
        self.log.debug(exc)
    return (output, exitcode)
