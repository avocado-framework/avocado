import fcntl
import os
import time

from avocado.utils import path

_open_log_files = {}
_log_file_dir = "/tmp"


def lock_file(filename, mode=fcntl.LOCK_EX):
    lockfile = open(filename, "w")
    fcntl.lockf(lockfile, mode)
    return lockfile


def unlock_file(lockfile):
    fcntl.lockf(lockfile, fcntl.LOCK_UN)
    lockfile.close()


def read_file(filename):
    """
    Read the entire contents of file.

    :param filename: Path to the file.
    """
    with open(filename, 'r') as file_obj:
        contents = file_obj.read()
    return contents

    f = open(filename)
    try:
        return f.read()
    finally:
        f.close()


def read_one_line(filename):
    """
    Read the first line of filename.

    :param filename: Path to the file.
    """
    with open(filename, 'r') as file_obj:
        line = file_obj.readline().rstrip('\n')
    return line


def write_one_line(filename, line):
    """
    Write one line of text to filename.

    :param filename: Path to the file.
    :param line: Line to be written.
    """
    write_file(filename, line.rstrip('\n') + '\n')


def write_file(filename, data):
    """
    Write data to a file.

    :param filename: Path to the file.
    :param line: Line to be written.
    """
    with open(filename, 'w') as file_obj:
        file_obj.write(data)


def close_log_file(filename):
    global _open_log_files, _log_file_dir
    remove = []
    for k in _open_log_files:
        if os.path.basename(k) == filename:
            f = _open_log_files[k]
            f.close()
            remove.append(k)
    if remove:
        for key_to_remove in remove:
            _open_log_files.pop(key_to_remove)


def log_line(filename, line):
    """
    Write a line to a file.

    :param filename: Path of file to write to, either absolute or relative to
                     the dir set by set_log_file_dir().
    :param line: Line to write.
    """
    global _open_log_files, _log_file_dir

    path = path.get_path(_log_file_dir, filename)
    if path not in _open_log_files:
        # First, let's close the log files opened in old directories
        close_log_file(filename)
        # Then, let's open the new file
        try:
            os.makedirs(os.path.dirname(path))
        except OSError:
            pass
        _open_log_files[path] = open(path, "w")
    timestr = time.strftime("%Y-%m-%d %H:%M:%S")
    _open_log_files[path].write("%s: %s\n" % (timestr, line))
    _open_log_files[path].flush()
