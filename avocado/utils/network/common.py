from .. import process


# Probably this will be replaced by aexpect
def run_command(command, host, sudo=False):
    # This is used to avoid circular imports
    if host.__class__.__name__ == 'LocalHost':
        return process.system_output(command, sudo=sudo).decode('utf-8')

    if sudo:
        command = "sudo {}".format(command)
    return host.remote_session.cmd(command).stdout.decode('utf-8')
