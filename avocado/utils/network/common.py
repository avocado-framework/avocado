from .. import process


# Probably this will be replaced by aexpect
def _run_command(command, remote_session=None, sudo=False):
    if remote_session:
        if sudo:
            command = "sudo {}".format(command)
        return remote_session.cmd(command).stdout.decode('utf-8')
    return process.system_output(command, sudo=sudo).decode('utf-8')
