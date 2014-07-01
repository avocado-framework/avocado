import logging
import os
from avocado.core import data_dir
from avocado.utils import path
from avocado.utils import process

log = logging.getLogger("avocado.test")


def _get_backend_dir(params):
    """
    Get the appropriate backend directory. Example: backends/qemu.
    """
    return os.path.join(data_dir.get_data_dir(), 'backends',
                        params.get("vm_type"))


def get_qemu_binary(params):
    """
    Get the path to the qemu binary currently in use.
    """
    # Update LD_LIBRARY_PATH for built libraries (libspice-server)
    qemu_binary_path = path.get_path(_get_backend_dir(params),
                                     params.get("qemu_binary", "qemu"))

    if not os.path.isfile(qemu_binary_path):
        logging.debug('Could not find params qemu in %s, searching the '
                      'host PATH for one to use', qemu_binary_path)
        try:
            qemu_binary = process.find_command('qemu-kvm')
            logging.debug('Found %s', qemu_binary)
        except ValueError:
            qemu_binary = process.find_command('kvm')
            logging.debug('Found %s', qemu_binary)
    else:
        library_path = os.path.join(_get_backend_dir(params), 'install_root', 'lib')
        if os.path.isdir(library_path):
            library_path = os.path.abspath(library_path)
            qemu_binary = ("LD_LIBRARY_PATH=%s %s" %
                           (library_path, qemu_binary_path))
        else:
            qemu_binary = qemu_binary_path

    return qemu_binary


def get_qemu_dst_binary(params):
    """
    Get the path to the qemu dst binary currently in use.
    """
    qemu_dst_binary = params.get("qemu_dst_binary", None)
    if qemu_dst_binary is None:
        return qemu_dst_binary

    qemu_binary_path = path.get_path(_get_backend_dir(params), qemu_dst_binary)

    # Update LD_LIBRARY_PATH for built libraries (libspice-server)
    library_path = os.path.join(_get_backend_dir(params), 'install_root', 'lib')
    if os.path.isdir(library_path):
        library_path = os.path.abspath(library_path)
        qemu_dst_binary = ("LD_LIBRARY_PATH=%s %s" %
                           (library_path, qemu_binary_path))
    else:
        qemu_dst_binary = qemu_binary_path

    return qemu_dst_binary


def get_qemu_img_binary(params):
    """
    Get the path to the qemu-img binary currently in use.
    """
    qemu_img_binary_path = path.get_path(_get_backend_dir(params),
                                         params.get("qemu_img_binary", "qemu-img"))
    if not os.path.isfile(qemu_img_binary_path):
        logging.debug('Could not find params qemu-img in %s, searching the '
                      'host PATH for one to use', qemu_img_binary_path)
        qemu_img_binary = process.find_command('qemu-img')
        logging.debug('Found %s', qemu_img_binary)
    else:
        qemu_img_binary = qemu_img_binary_path

    return qemu_img_binary


def get_qemu_io_binary(params):
    """
    Get the path to the qemu-io binary currently in use.
    """
    qemu_io_binary_path = path.get_path(_get_backend_dir(params),
                                        params.get("qemu_io_binary", "qemu-io"))
    if not os.path.isfile(qemu_io_binary_path):
        logging.debug('Could not find params qemu-io in %s, searching the '
                      'host PATH for one to use', qemu_io_binary_path)
        qemu_io_binary = process.find_command('qemu-io')
        logging.debug('Found %s', qemu_io_binary)
    else:
        qemu_io_binary = qemu_io_binary_path

    return qemu_io_binary
