"""
Library used to retrieve qemu paths from params or environment.
"""

import os

from avocado.utils import process

_QEMU_CANDIDATE_NAMES = ['qemu-kvm', 'qemu-system-x86_64', 'qemu']


class QEMUCmdNotFoundError(Exception):

    def __init__(self, program):
        self.program = program

    def __str__(self):
        return ('Could not find a suitable %s after looking in '
                'params, env variables and $PATH' % self.program)


def _validate_path(path, method):
    if not os.path.isfile(path):
        raise IOError('Path %s (provided through %s) does not exist' %
                      (path, method))
    return path


def get_qemu_binary(params=None):
    """
    Find a QEMU binary.

    First, look in the test params, then in the env variable $QEMU and
    then, if nothing found, look in the system $PATH.
    """
    if params is not None:
        params_qemu = params.get('qemu_bin')
        if params_qemu is not None:
            return _validate_path(params_qemu, 'test param qemu_bin')

    env_qemu = os.environ.get('QEMU')
    if env_qemu is not None:
        return _validate_path(env_qemu, 'env variable $QEMU')

    for c in _QEMU_CANDIDATE_NAMES:
        try:
            return process.find_command(c)
        except process.CmdNotFoundError:
            pass

    raise QEMUCmdNotFoundError('qemu')


def get_qemu_dst_binary(params=None):
    """
    Find an alternate QEMU binary to transfer state to.

    This is for use in migration tests.
    """
    if params is not None:
        params_qemu = params.get('qemu_dst_bin')
        if params_qemu is not None:
            return _validate_path(params_qemu, 'test param qemu_dst_bin')

    env_qemu = os.environ.get('QEMU_DST')
    if env_qemu is not None:
        return _validate_path(env_qemu, 'env variable $QEMU')

    for c in _QEMU_CANDIDATE_NAMES:
        try:
            return process.find_command(c)
        except process.CmdNotFoundError:
            pass

    raise QEMUCmdNotFoundError('qemu alternate destination')


def get_qemu_img_binary(params=None):
    if params is not None:
        params_qemu = params.get('qemu_img_bin')
        if params_qemu is not None:
            return _validate_path(params_qemu, 'test param qemu_img')

    env_qemu = os.environ.get('QEMU_IMG')
    if env_qemu is not None:
        return _validate_path(env_qemu, 'env variable $QEMU_IMG')

    try:
        return process.find_command('qemu-img')
    except process.CmdNotFoundError:
        pass

    raise QEMUCmdNotFoundError('qemu-img')


def get_qemu_io_binary(params=None):
    if params is not None:
        params_qemu = params.get('qemu_io_bin')
        if params_qemu is not None:
            return _validate_path(params_qemu, 'test param qemu_io_bin')

    env_qemu = os.environ.get('QEMU_IO')
    if env_qemu is not None:
        return _validate_path(env_qemu, 'env variable $QEMU_IO')

    try:
        return process.find_command('qemu-io')
    except process.CmdNotFoundError:
        pass

    raise QEMUCmdNotFoundError('qemu-io')
