import os
import process


def make(path, make='make', extra_args='', ignore_status=False):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param extra: extra command line arguments to pass to make.
    """
    cwd = os.getcwd()
    os.chdir(path)
    cmd = make
    makeopts = os.environ.get('MAKEOPTS', '')
    if makeopts:
        cmd += ' %s' % makeopts
    if extra_args:
        cmd += ' %s' % extra_args
    make_process = process.system(cmd, ignore_status=ignore_status)
    os.chdir(cwd)
    return make_process
