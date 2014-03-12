import os
import process


def make(path, extra='', make='make', ignore_status=False):
    """
    Run make, adding MAKEOPTS to the list of options.

    :param extra: extra command line arguments to pass to make.
    """
    cwd = os.getcwd()
    os.chdir(path)
    cmd = '%s %s %s' % (make, os.environ.get('MAKEOPTS', ''), extra)
    make_process = process.system(cmd, ignore_status=ignore_status)
    os.chdir(cwd)
    return make_process
