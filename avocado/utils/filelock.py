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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>


import errno
import os
import time


class AlreadyLocked(Exception):
    pass


class LockFailed(Exception):
    pass


class LockFile(object):
    """
    Creates a lock for a file.

    If the lock file already exists and it contains the current process
    pid in it, we wait until the timeout for the lock to be released,
    raising an AlreadyLocked exception when the timeout is reached.

    If the lock file already exists and it contains a pid of another
    running process, we raise an NotMyLock exception.

    If the lock file exists and it has no running processes pid in it,
    we try to clean the file and acquire the lock.
    """
    def __init__(self, filename):
        self.filename = '%s.lock' % filename
        self.pid = str(os.getpid())
        self.locked = False

    def acquire(self):
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        timeout = time.time() + 1
        while time.time() < timeout:
            try:
                fd = os.open(self.filename, flags)
            except:
                with open(self.filename, 'r') as f:
                    content = f.read()

                try:
                    int(content)
                except ValueError:
                    os.remove(self.filename)
                    continue

                if content != self.pid:
                    try:
                        os.kill(int(content), 0)
                    except OSError as e:
                        if e.errno == errno.ESRCH:
                            try:
                                os.remove(self.filename)
                            except:
                                raise LockFailed('Not able to lock.')
                        else:
                            raise AlreadyLocked('File is locked by some other '
                                                'process.')
                    except:
                        raise LockFailed('Not able to lock.')
            else:
                os.write(fd, self.pid)
                os.close(fd)
                self.locked = True
                return

            time.sleep(0.1)

        raise AlreadyLocked('File is already locked and we reached the '
                            'timeout waiting.')

    def release(self):
        if self.locked:
            try:
                os.remove(self.filename)
                self.locked = False
            except:
                pass
