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

"""
Utility for individual file access control implemented
via PID lock files.
"""

import os
import time

from .process import pid_exists


class AlreadyLocked(Exception):
    pass


class LockFailed(Exception):
    pass


class FileLock(object):

    """
    Creates an exclusive advisory lock for a file.
    All processes should use and honor the advisory
    locking scheme, but uncooperative processes are free to
    ignore the lock and access the file in any way they choose.
    """

    def __init__(self, filename, timeout=0):
        self.filename = '%s.lock' % filename
        self.pid = str(os.getpid())
        self.locked = False
        self.timeout = timeout

    def __enter__(self):
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_SYNC
        timelimit = time.time() + self.timeout
        while True:
            try:
                fd = os.open(self.filename, flags)
                os.write(fd, self.pid)
                os.close(fd)
                self.locked = True
                return self
            except:
                try:
                    # Read the file to realize what's happening.
                    with open(self.filename, 'r') as f:
                        try:
                            content = f.read()
                        except Exception as e:
                            raise LockFailed(e.message)

                    # If file is empty, I guess someone created it with 'touch'
                    # to manually lock the file.
                    if not content:
                        raise AlreadyLocked('File is locked by someone else.')

                    try:
                        existing_lock_pid = int(content)
                    except ValueError:
                        # If the file content is not an integer, then I don't know
                        # who created it and we better get out of here.
                        raise AlreadyLocked('File is locked by someone else.')

                    # If the PID in the lock file is not my PID, let's
                    # handle it.
                    if existing_lock_pid != self.pid:
                        # If there's no process with the PID in lockfile,
                        # let's try to remove the lockfile to acquire the
                        # lock in the next iteration.
                        if not pid_exists(existing_lock_pid):
                            try:
                                os.remove(self.filename)
                                continue
                            except:
                                raise LockFailed('Not able to lock.')

                except:
                    # If we cannot read the lock file, let's just
                    # go on. Maybe in next iteration (if we have time)
                    # we have a better luck.
                    pass

                # If we get to this point, the lock file is there, it belongs
                # to a running process and we are just waiting for the lock
                # to be released.
                if self.timeout <= 0:
                    raise AlreadyLocked('File is already locked.')
                elif time.time() > timelimit:
                    raise AlreadyLocked('Timeout waiting for the lock.')
                else:
                    time.sleep(0.1)

    def __exit__(self, *args):
        if self.locked:
            try:
                os.remove(self.filename)
                self.locked = False
            except:
                pass
