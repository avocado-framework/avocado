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
    def __init__(self, filename, timeout=0):
        self.filename = '%s.lock' % filename
        self.pid = str(os.getpid())
        self.locked = False
        self.timeout = timeout

    def acquire(self):
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        timelimit = time.time() + self.timeout
        while True:
            try:
                fd = os.open(self.filename, flags)
                os.write(fd, self.pid)
                os.close(fd)
                self.locked = True
                break
            except:
                # Read the file to realize what's happening.
                with open(self.filename, 'r') as f:
                    content = f.read()

                # If file is empty, I guess someone created it with 'touch'
                # to manually lock the file.
                if not content:
                    raise AlreadyLocked('File is locked by someone else.')

                try:
                    int(content)
                except ValueError:
                    # If the file content is not an integer, then I don't know
                    # who created it and we better get out of here.
                    raise AlreadyLocked('File is locked by someone else.')

                if content != self.pid:
                    # If the PID in the lock file is not my PID, let's
                    # handle it.
                    try:
                        # Do the process exist? If the kill produces no
                        # exception, it means the process exists and we will
                        # wait until the timeout for the lock to be released.
                        os.kill(int(content), 0)
                    except OSError as e:
                        if e.errno == errno.ESRCH:
                            # If there's no process with the PID in lockfile,
                            # let's try to remove the lockfile to acquire the
                            # lock in the next iteration.
                            try:
                                os.remove(self.filename)
                                continue
                            except:
                                raise LockFailed('Not able to lock.')

                # If we get to this point, the lock file is there, it belongs
                # to a running process and we are just waiting for the lock
                # to be released.
                if time.time() > timelimit:
                    raise AlreadyLocked('File is already locked and we '
                                        'have reached the timeout waiting')
                else:
                    time.sleep(0.1)

    def release(self):
        if self.locked:
            try:
                os.remove(self.filename)
                self.locked = False
            except:
                pass
